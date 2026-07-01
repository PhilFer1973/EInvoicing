from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from httpx import ASGITransport, AsyncClient
import pytest

from app.integrations.storecove.client import (
    CONFIGURATION_GUIDANCE,
    PRODUCTION_REJECTED_MESSAGE,
    redact_secrets,
)
from app.integrations.storecove.mapper import map_canonical_to_storecove_request
from app.integrations.storecove.schemas import StorecoveConfig, UK_SANDBOX_WORDING
from app.main import app
from app.models.canonical import CanonicalInvoice
from app.services.evidence import UK_READINESS_WORDING
from tests.workbook_fixtures import uk_valid_workbook_bytes


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_uk_roadmap_pack_is_exposed(client: AsyncClient) -> None:
    response = await client.get("/api/country-packs")

    assert response.status_code == 200
    uk = next(pack for pack in response.json()["country_packs"] if pack["country_pack_id"] == "uk_info")
    assert uk["display_name"] == "United Kingdom / 2029 Peppol Roadmap"
    assert uk["support_level"] == "generator_readiness"
    assert uk["sandbox_test_available_when_configured"] is True
    assert uk["default_output_profile"] == "uk_peppol_readiness_ubl"
    assert "mandatory e-invoicing is planned for 2029" in " ".join(uk["scope"])
    assert "Peppol" in " ".join(uk["mandatory_format"])
    assert UK_READINESS_WORDING in uk["v1_boundary"]


async def test_valid_uk_sample_workbook_validates_and_builds_canonical_invoice(client: AsyncClient) -> None:
    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes())

    assert payload["status"] == "validated"
    assert payload["validation_report"]["summary"]["overall_status"] == "passed"
    assert payload["validation_report"]["summary"]["blocking_errors"] == 0
    assert payload["validation_report"]["summary"]["warnings"] == 0
    readiness_notices = [
        result
        for result in payload["validation_report"]["results"]
        if result["rule_id"].startswith("UK-READINESS-") and result["rule_id"] != "UK-READINESS-000"
    ]
    assert len(readiness_notices) == 5
    assert all(result["status"] == "passed" for result in readiness_notices)
    assert all(result["severity"] == "warning" for result in readiness_notices)
    canonical = payload["canonical_invoice"]
    assert canonical["seller"]["legal_name"] == "Demo UK Services Ltd"
    assert canonical["seller"]["tax_registration_number"] == "GB123456789"
    assert canonical["seller"]["peppol_id"] == "9932:GB123456789"
    assert canonical["buyer"]["legal_name"] == "Demo UK Buyer Ltd"
    assert canonical["buyer"]["tax_registration_number"] == "GB987654321"
    assert canonical["buyer"]["peppol_id"] == "9932:GB987654321"
    assert canonical["invoice"]["invoice_number"] == "INV-UK-2029-001"
    assert canonical["invoice"]["invoice_currency_code"] == "GBP"
    assert canonical["invoice"]["buyer_reference"] == "UK-BUYER-REF-001"
    assert canonical["tax_summary"] == [
        {
            "tax_category_code": "S",
            "tax_rate": "20",
            "taxable_amount": "1000.00",
            "tax_amount": "200.00",
        }
    ]
    assert canonical["totals"]["gross_total"] == 1200
    files = {file["filename"]: file for file in payload["evidence_bundle_preview"]["files"]}
    assert files["invoice.xml"]["status"] == "pending_generation"
    assert files["xml_validation_report.json"]["status"] == "pending_xml_validation"
    assert files["en16931_validation_report.json"]["status"] == "pending_official_validation"


async def test_checked_in_uk_sample_workbook_validates(client: AsyncClient) -> None:
    workbook_path = Path(__file__).resolve().parents[2] / "test_data" / "workbooks" / "UK-PEPPOL-SANDBOX-001.xlsx"

    payload = await _upload_uk_workbook(client, workbook_path.read_bytes())

    assert payload["status"] == "validated"
    assert payload["canonical_invoice"]["invoice"]["invoice_number"] == "INV-UK-2029-001"


async def test_uk_readiness_xml_is_generated_from_canonical_invoice(client: AsyncClient) -> None:
    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes())

    response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")

    assert response.status_code == 200, response.text
    evidence = response.json()
    files = {file["filename"]: file for file in evidence["files"]}
    assert files["invoice.xml"]["status"] == "stored"
    assert files["xml_validation_report.json"]["status"] == "stored"
    assert files["en16931_validation_report.json"]["status"] == "stored"
    assert files["peppol_schematron_validation_report.json"]["status"] == "stored"

    xml_response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-xml")
    assert xml_response.status_code == 200
    xml = xml_response.content.decode("utf-8")
    assert "INV-UK-2029-001" in xml
    assert "GBP" in xml
    assert "GB123456789" in xml
    assert "GB987654321" in xml
    assert "200.00" in xml
    assert "1200.00" in xml

    root = ET.fromstring(xml_response.content)
    ns = {
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }
    seller_endpoint = root.find("./cac:AccountingSupplierParty/cac:Party/cbc:EndpointID", ns)
    buyer_endpoint = root.find("./cac:AccountingCustomerParty/cac:Party/cbc:EndpointID", ns)
    assert seller_endpoint is not None
    assert seller_endpoint.attrib["schemeID"] == "9932"
    assert seller_endpoint.text == "GB123456789"
    assert buyer_endpoint is not None
    assert buyer_endpoint.attrib["schemeID"] == "9932"
    assert buyer_endpoint.text == "GB987654321"


async def test_uk_evidence_bundle_contains_readiness_xml_and_honest_metadata(client: AsyncClient) -> None:
    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes())
    generate_response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")
    assert generate_response.status_code == 200, generate_response.text

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")

    assert bundle_response.status_code == 200
    assert "INV-UK-2029-001_uk_evidence_bundle.zip" in bundle_response.headers["content-disposition"]
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert {
            "source_upload_snapshot.xlsx",
            "canonical_invoice.json",
            "validation_report.json",
            "xml_validation_report.json",
            "invoice.xml",
            "country_pack_manifest.json",
            "evidence_metadata.json",
            "hashes.txt",
            "README_uk_readiness_only.txt",
        } <= names
        metadata = json.loads(archive.read("evidence_metadata.json"))
        xml_report = json.loads(archive.read("xml_validation_report.json"))
        readme = archive.read("README_uk_readiness_only.txt").decode("utf-8")

        assert metadata["uk_readiness"]["wording"] == UK_READINESS_WORDING
        assert metadata["uk_readiness"]["final_uk_2029_compliance"] == "not_proven"
        assert len(metadata["readiness_notices"]) == 5
        assert {notice["label"] for notice in metadata["readiness_notices"]} == {"Readiness notice"}
        assert {notice["status"] for notice in metadata["readiness_notices"]} == {"passed"}
        assert metadata["official_xml_validator_status"]["en16931_validation_status"] == "not_configured"
        assert metadata["official_xml_validator_status"]["peppol_schematron_validation_status"] == "not_configured"
        assert xml_report["overall_status"] == "passed"
        assert UK_READINESS_WORDING in readme
        assert "live Peppol" not in metadata["uk_readiness"]["peppol_delivery"]


async def test_true_uk_blocking_errors_still_fail_validation(client: AsyncClient) -> None:
    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes(buyer_peppol_id=None))

    assert payload["status"] == "validation_failed"
    assert payload["validation_report"]["summary"]["overall_status"] == "failed"
    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    buyer_endpoint_error = next(
        result for result in payload["validation_report"]["results"] if result["rule_id"] == "UK-BUYER-002"
    )
    assert buyer_endpoint_error["status"] == "failed"
    assert buyer_endpoint_error["severity"] == "error"


async def test_storecove_sandbox_is_disabled_without_configuration(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_storecove_env(monkeypatch)

    config_response = await client.get("/api/uploads/storecove-sandbox/configuration")
    assert config_response.status_code == 200
    assert config_response.json()["configured"] is False
    assert config_response.json()["message"] == CONFIGURATION_GUIDANCE

    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes())
    submit_response = await client.post(f"/api/uploads/{payload['upload_id']}/storecove-sandbox")

    assert submit_response.status_code == 409
    assert CONFIGURATION_GUIDANCE in submit_response.text


async def test_storecove_mapper_creates_expected_request_object(client: AsyncClient) -> None:
    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes())
    canonical = CanonicalInvoice(**payload["canonical_invoice"])
    config = StorecoveConfig(
        sandbox_enabled=True,
        api_base_url="https://sandbox.storecove.example.test",
        api_key="test-secret",
        sender_legal_entity_id="sender-entity-id",
        receiver_legal_entity_id="receiver-entity-id",
    )

    request_payload = map_canonical_to_storecove_request(canonical, config)

    assert request_payload.sandbox_only is True
    assert request_payload.external_id == "INV-UK-2029-001"
    assert request_payload.sender.legal_entity_id == "sender-entity-id"
    assert request_payload.sender.tax_registration_number == "GB123456789"
    assert request_payload.receiver.legal_entity_id == "receiver-entity-id"
    assert request_payload.invoice["currency"] == "GBP"
    assert request_payload.totals["gross_total"] == "1200.00"
    assert request_payload.lines[0].description == "Consulting services"
    assert request_payload.disclaimer == UK_SANDBOX_WORDING


async def test_production_storecove_endpoint_is_rejected(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _set_storecove_env(monkeypatch, base_url="https://api.storecove.com")

    config_response = await client.get("/api/uploads/storecove-sandbox/configuration")

    assert config_response.status_code == 200
    assert config_response.json()["configured"] is False
    assert config_response.json()["mode"] == "configuration_error"
    assert config_response.json()["message"] == PRODUCTION_REJECTED_MESSAGE


async def test_mocked_storecove_sandbox_response_and_evidence_are_redacted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_storecove_env(monkeypatch)
    payload = await _upload_uk_workbook(client, uk_valid_workbook_bytes())

    submit_response = await client.post(f"/api/uploads/{payload['upload_id']}/storecove-sandbox")

    assert submit_response.status_code == 200, submit_response.text
    submitted = submit_response.json()
    assert submitted["status"] == "storecove_sandbox_mocked"
    assert submitted["storecove_mocked"] is True
    assert submitted["storecove_provider_reference"] == "MOCK-STORECOVE-INV-UK-2029-001"
    files = {file["filename"]: file for file in submitted["evidence_bundle_preview"]["files"]}
    for filename in (
        "storecove_request.json",
        "storecove_response.json",
        "storecove_status.json",
        "provider_reference.txt",
        "README_sandbox_only.txt",
    ):
        assert files[filename]["status"] == "stored"
        assert files[filename]["sha256"]

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")

    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert {
            "source_upload_snapshot.xlsx",
            "canonical_invoice.json",
            "validation_report.json",
            "storecove_request.json",
            "storecove_response.json",
            "storecove_status.json",
            "provider_reference.txt",
            "country_pack_manifest.json",
            "evidence.json",
            "README_sandbox_only.txt",
        } <= names
        request_payload = json.loads(archive.read("storecove_request.json"))
        response_payload = json.loads(archive.read("storecove_response.json"))
        status_payload = json.loads(archive.read("storecove_status.json"))
        evidence = json.loads(archive.read("evidence.json"))
        readme = archive.read("README_sandbox_only.txt").decode("utf-8")
        provider_reference = archive.read("provider_reference.txt").decode("utf-8")

        assert request_payload["external_id"] == "INV-UK-2029-001"
        assert "test-secret-api-key" not in json.dumps(request_payload)
        assert response_payload["mocked"] is True
        assert status_payload["peppol_network_delivery"] == "not_submitted"
        assert provider_reference == "MOCK-STORECOVE-INV-UK-2029-001"
        assert UK_SANDBOX_WORDING in readme
        assert evidence["storecove_sandbox"]["mocked"] is True
        assert evidence["storecove_sandbox"]["disclaimer"] == UK_SANDBOX_WORDING
        assert "final UK 2029 statutory compliance" in evidence["official_artefact_validation"]["note"]
        assert not _zip_text_files_contain(archive, "test-secret-api-key")


def test_redaction_helper_removes_secret_values() -> None:
    redacted = redact_secrets(
        {
            "api_key": "test-secret-api-key",
            "nested": {"authorization": "Bearer test-secret-api-key"},
            "url": "https://sandbox.example.test?key=test-secret-api-key",
        },
        "test-secret-api-key",
    )

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["authorization"] == "[REDACTED]"
    assert redacted["url"] == "https://sandbox.example.test?key=[REDACTED]"


async def _upload_uk_workbook(client: AsyncClient, workbook_bytes: bytes) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": "uk_info"},
        files={
            "file": (
                "UK-PEPPOL-SANDBOX-001.xlsx",
                workbook_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _clear_storecove_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "STORECOVE_SANDBOX_ENABLED",
        "STORECOVE_API_BASE_URL",
        "STORECOVE_API_KEY",
        "STORECOVE_SENDER_LEGAL_ENTITY_ID",
        "STORECOVE_RECEIVER_LEGAL_ENTITY_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def _set_storecove_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    base_url: str = "https://sandbox.storecove.example.test",
) -> None:
    monkeypatch.setenv("STORECOVE_SANDBOX_ENABLED", "true")
    monkeypatch.setenv("STORECOVE_API_BASE_URL", base_url)
    monkeypatch.setenv("STORECOVE_API_KEY", "test-secret-api-key")
    monkeypatch.setenv("STORECOVE_SENDER_LEGAL_ENTITY_ID", "sender-entity-id")
    monkeypatch.setenv("STORECOVE_RECEIVER_LEGAL_ENTITY_ID", "receiver-entity-id")


def _zip_text_files_contain(archive: ZipFile, needle: str) -> bool:
    for name in archive.namelist():
        if name.endswith((".json", ".txt")):
            if needle in archive.read(name).decode("utf-8"):
                return True
    return False
