from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
import pytest

from app.integrations.einvoicebe.client import CONFIGURATION_GUIDANCE
from app.integrations.einvoicebe.redaction import redact_einvoicebe_secrets
from app.integrations.einvoicebe.schemas import EInvoiceBEValidationIssue, EInvoiceBEValidationResponse
from app.main import app
from tests.workbook_fixtures import belgium_einvoicebe_validation_workbook_bytes, belgium_valid_workbook_bytes


pytestmark = pytest.mark.anyio

BELGIUM_EINVOICEBE_IDENTIFIER_MAPPING = [
    {
        "ubl_path": "AccountingSupplierParty/Party/EndpointID[@schemeID='0208']",
        "value": "0990251719",
        "concept": "Peppol endpoint ID value",
        "expected_format": "Ten-digit Belgian enterprise number without BE prefix; PEPPOL-COMMON-R043 mod-97 valid",
    },
    {
        "ubl_path": "AccountingSupplierParty/Party/PartyIdentification/ID[@schemeID='0208']",
        "value": "0990251719",
        "concept": "Seller legal/enterprise registration number",
        "expected_format": "Ten-digit Belgian enterprise number without BE prefix; PEPPOL-COMMON-R043 mod-97 valid",
    },
    {
        "ubl_path": "AccountingSupplierParty/Party/PartyTaxScheme/CompanyID",
        "value": "BE0990251719",
        "concept": "Seller VAT registration number",
        "expected_format": "Belgian VAT number with BE prefix",
    },
    {
        "ubl_path": "AccountingSupplierParty/Party/PartyLegalEntity/CompanyID[@schemeID='0208']",
        "value": "0990251719",
        "concept": "Seller legal/enterprise registration number",
        "expected_format": "Ten-digit Belgian enterprise number without BE prefix; PEPPOL-COMMON-R043 mod-97 valid",
    },
    {
        "ubl_path": "AccountingCustomerParty/Party/EndpointID[@schemeID='0208']",
        "value": "0987654394",
        "concept": "Buyer Peppol endpoint ID value",
        "expected_format": "Buyer enterprise number without BE prefix",
    },
    {
        "ubl_path": "AccountingCustomerParty/Party/PartyTaxScheme/CompanyID",
        "value": "BE0987654394",
        "concept": "Buyer VAT registration number",
        "expected_format": "Belgian VAT number with BE prefix",
    },
    {
        "ubl_path": "AccountingCustomerParty/Party/PartyLegalEntity/CompanyID[@schemeID='0208']",
        "value": "0987654394",
        "concept": "Buyer legal/enterprise registration number",
        "expected_format": "Buyer enterprise number without BE prefix",
    },
]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_einvoicebe_validation_is_disabled_by_default(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client)

    config_response = await client.get("/api/uploads/einvoicebe/configuration")
    validation_response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert config_response.status_code == 200
    assert config_response.json()["configured"] is False
    assert config_response.json()["message"] == CONFIGURATION_GUIDANCE
    assert validation_response.status_code == 200
    record = validation_response.json()
    assert record["generated_xml_path"].endswith("_belgium_peppol_invoice.xml")
    assert record["external_validation"]["status"] == "not_configured"
    assert record["external_validation"]["messages"] == ["External e-invoice.be sandbox validation not configured."]

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert "invoice.xml" in names
        assert "external_validation_status.json" in names
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["external_validation"]["status"] == "not_configured"
        assert evidence["xml_generation_for_validation"]["status"] == "generated"


async def test_einvoicebe_validation_missing_api_key_fails_safely(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_einvoicebe_env(monkeypatch)
    monkeypatch.setenv("EINVOICEBE_ENABLED", "true")
    payload = await _upload_belgium_workbook(client)

    config_response = await client.get("/api/uploads/einvoicebe/configuration")
    validation_response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert config_response.status_code == 200
    assert config_response.json()["mode"] == "missing_credentials"
    assert config_response.json()["missing_fields"] == ["EINVOICEBE_API_KEY"]
    assert validation_response.status_code == 200
    assert validation_response.json()["external_validation"]["status"] == "not_configured"


async def test_legacy_validate_endpoint_runs_belgium_validation_pipeline_when_not_configured(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client)

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate")
    record_response = await client.get(f"/api/uploads/{payload['upload_id']}")

    assert response.status_code == 200
    assert record_response.status_code == 200
    record = record_response.json()
    assert record["generated_xml_path"].endswith("_belgium_peppol_invoice.xml")
    assert record["external_validation"]["status"] == "not_configured"


async def test_belgium_pipeline_skips_xml_and_external_validation_when_internal_errors_block(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client, belgium_valid_workbook_bytes(invoice_number=None))

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert response.status_code == 200
    record = response.json()
    assert record["validation_report"]["summary"]["blocking_errors"] > 0
    assert record["generated_xml_path"] is None
    assert record["external_validation"]["status"] == "skipped"
    assert record["external_validation"]["messages"] == [
        "External e-invoice.be sandbox validation skipped because internal validation has blocking errors."
    ]


async def test_mocked_einvoicebe_validation_response_is_captured_in_evidence(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    monkeypatch.setattr(
        "app.api.uploads.submit_ubl_validation",
        _successful_einvoicebe_response,
    )
    payload = await _upload_belgium_workbook(client)

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert response.status_code == 200, response.text
    record = response.json()
    assert record["external_validation"]["provider"] == "e-invoice.be"
    assert record["external_validation"]["label"] == "External sandbox validation"
    assert record["external_validation"]["status"] == "passed"
    assert record["external_validation"]["is_valid"] is True
    assert record["external_validation"]["reference"] == "EINVBE-VALID-001"
    assert record["external_validation"]["endpoint"] == "https://api.e-invoice.be/api/validate/ubl"

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")

    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert {
            "source_upload_snapshot.xlsx",
            "canonical_invoice.json",
            "validation_report.json",
            "invoice.xml",
            "einvoicebe_validation_request.json",
            "einvoicebe_validation_response.json",
            "external_validation_status.json",
            "country_pack_manifest.json",
            "evidence_metadata.json",
        } <= names
        request_payload = json.loads(archive.read("einvoicebe_validation_request.json"))
        response_payload = json.loads(archive.read("einvoicebe_validation_response.json"))
        status_payload = json.loads(archive.read("external_validation_status.json"))
        evidence = json.loads(archive.read("evidence_metadata.json"))

        assert request_payload["endpoint"] == "https://api.e-invoice.be/api/validate/ubl"
        assert request_payload["method"] == "POST"
        assert request_payload["content_type"] == "multipart/form-data"
        assert request_payload["authorization"] == "[REDACTED]"
        assert request_payload["form_fields"][0]["name"] == "file"
        assert request_payload["form_fields"][0]["filename"].endswith("_belgium_peppol_invoice.xml")
        assert request_payload["sandbox_company_number"] == "099025170"
        assert request_payload["sandbox_peppol_id"] == "0208:099025170"
        assert response_payload["id"] == "EINVBE-VALID-001"
        assert response_payload["is_valid"] is True
        assert status_payload["status"] == "passed"
        assert status_payload["peppol_delivery"] == "not_delivered"
        assert evidence["external_validation"]["status"] == "passed"
        assert evidence["external_validation"]["peppol_delivery"] == "not_delivered"
        assert evidence["external_validation"]["recipient_acceptance"] == "not_requested"
        assert evidence["external_validation"]["smp_registration_claim"] == "not_claimed"
        assert evidence["xml_generation_for_validation"]["status"] == "generated"
        assert "External sandbox validation only" in evidence["external_validation"]["disclaimer"]
        assert not _zip_text_files_contain(archive, "test-einvoicebe-api-key")


async def test_mocked_einvoicebe_failed_validation_is_reported_clearly(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    monkeypatch.setattr(
        "app.api.uploads.submit_ubl_validation",
        _failed_einvoicebe_response,
    )
    payload = await _upload_belgium_workbook(client)

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert response.status_code == 200, response.text
    external_validation = response.json()["external_validation"]
    assert external_validation["status"] == "failed"
    assert external_validation["is_valid"] is False
    assert external_validation["issue_count"] == 2
    assert external_validation["messages"] == ["Mocked Peppol validation issue."]

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        response_payload = json.loads(archive.read("einvoicebe_validation_response.json"))
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert len(response_payload["issues"]) == 2
        assert response_payload["issues"][0]["message"] == "Mocked Peppol validation issue."
        assert response_payload["issues"][1]["message"] == "Mocked Peppol validation issue."
        assert evidence["external_validation"]["messages"] == ["Mocked Peppol validation issue."]


async def test_einvoicebe_transport_error_keeps_xml_and_marks_external_validation_failed(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)

    def _raise_transport_error(*, config, xml_bytes: bytes, filename: str) -> EInvoiceBEValidationResponse:
        raise RuntimeError("simulated provider transport failure")

    monkeypatch.setattr("app.api.uploads.submit_ubl_validation", _raise_transport_error)
    payload = await _upload_belgium_workbook(client)

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert response.status_code == 200, response.text
    record = response.json()
    assert record["generated_xml_path"].endswith("_belgium_peppol_invoice.xml")
    assert record["external_validation"]["status"] == "failed"
    assert record["external_validation"]["messages"] == [
        "External e-invoice.be sandbox validation failed before a provider response was captured."
    ]

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert "invoice.xml" in names
        assert "einvoicebe_validation_request.json" in names
        assert "external_validation_status.json" in names
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["xml_generation_for_validation"]["status"] == "generated"
        assert evidence["external_validation"]["status"] == "failed"
        assert not _zip_text_files_contain(archive, "test-einvoicebe-api-key")


async def test_einvoicebe_sample_workbook_separates_belgian_identifiers(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(client, belgium_einvoicebe_validation_workbook_bytes(), "BE-EINVOICEBE-VALIDATION-001.xlsx")
    canonical = payload["canonical_invoice"]

    assert canonical["seller"]["legal_name"] == "Test Company BV"
    assert canonical["seller"]["tax_registration_number"] == "BE0990251719"
    assert canonical["seller"]["company_number"] == "0990251719"
    assert canonical["seller"]["enterprise_number"] == "0990251719"
    assert canonical["seller"]["peppol_id"] == "0208:0990251719"

    generate_response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")
    assert generate_response.status_code == 200
    xml_response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-xml")
    xml = xml_response.text
    assert '<cbc:EndpointID schemeID="0208">0990251719</cbc:EndpointID>' in xml
    assert '<cbc:ID schemeID="0208">0990251719</cbc:ID>' in xml
    assert "<cbc:CompanyID>BE0990251719</cbc:CompanyID>" in xml
    assert '<cbc:CompanyID schemeID="0208">0990251719</cbc:CompanyID>' in xml
    assert "0208:0990251719" not in xml


async def test_belgium_ubl_identifier_mapping_table_is_enforced(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(
        client,
        belgium_einvoicebe_validation_workbook_bytes(),
        "BE-EINVOICEBE-VALIDATION-001.xlsx",
    )

    generate_response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")
    assert generate_response.status_code == 200
    xml_response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-xml")
    xml = xml_response.text

    expected_xml_snippets = {
        "AccountingSupplierParty/Party/EndpointID[@schemeID='0208']": '<cbc:EndpointID schemeID="0208">0990251719</cbc:EndpointID>',
        "AccountingSupplierParty/Party/PartyIdentification/ID[@schemeID='0208']": '<cbc:ID schemeID="0208">0990251719</cbc:ID>',
        "AccountingSupplierParty/Party/PartyTaxScheme/CompanyID": "<cbc:CompanyID>BE0990251719</cbc:CompanyID>",
        "AccountingSupplierParty/Party/PartyLegalEntity/CompanyID[@schemeID='0208']": '<cbc:CompanyID schemeID="0208">0990251719</cbc:CompanyID>',
        "AccountingCustomerParty/Party/EndpointID[@schemeID='0208']": '<cbc:EndpointID schemeID="0208">0987654394</cbc:EndpointID>',
        "AccountingCustomerParty/Party/PartyTaxScheme/CompanyID": "<cbc:CompanyID>BE0987654394</cbc:CompanyID>",
        "AccountingCustomerParty/Party/PartyLegalEntity/CompanyID[@schemeID='0208']": '<cbc:CompanyID schemeID="0208">0987654394</cbc:CompanyID>',
    }
    for mapping in BELGIUM_EINVOICEBE_IDENTIFIER_MAPPING:
        assert expected_xml_snippets[mapping["ubl_path"]] in xml

    for identifier in ["0990251719", "0987654394"]:
        assert _is_valid_belgian_0208_identifier(identifier)
    assert "0208:0990251719" not in xml


async def test_checked_in_einvoicebe_sample_workbook_validates(client: AsyncClient) -> None:
    workbook_path = Path(__file__).resolve().parents[2] / "test_data" / "workbooks" / "BE-EINVOICEBE-VALIDATION-001.xlsx"

    payload = await _upload_belgium_workbook(client, workbook_path.read_bytes(), "BE-EINVOICEBE-VALIDATION-001.xlsx")

    assert payload["status"] == "validated"
    assert payload["canonical_invoice"]["seller"]["legal_name"] == "Test Company BV"


async def test_belgium_evidence_metadata_says_einvoicebe_validation_not_run(client: AsyncClient) -> None:
    payload = await _upload_and_generate_belgium_xml(client)

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")

    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["external_validation"]["provider"] == "e-invoice.be"
        assert evidence["external_validation"]["status"] == "not_run"
        assert evidence["external_validation"]["message"] == "External e-invoice.be validation not run."


def test_einvoicebe_redaction_removes_api_key_values() -> None:
    redacted = redact_einvoicebe_secrets(
        {
            "api_key": "test-einvoicebe-api-key",
            "nested": {"authorization": "Bearer test-einvoicebe-api-key"},
            "raw_response": {"debug": "test-einvoicebe-api-key"},
        },
        "test-einvoicebe-api-key",
    )

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["authorization"] == "[REDACTED]"
    assert redacted["raw_response"]["debug"] == "[REDACTED]"


async def _upload_and_generate_belgium_xml(client: AsyncClient) -> dict:
    payload = await _upload_belgium_workbook(client)
    generate_response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")
    assert generate_response.status_code == 200, generate_response.text
    return payload


async def _upload_belgium_workbook(
    client: AsyncClient,
    workbook_bytes: bytes | None = None,
    filename: str = "BE-VALID-001.xlsx",
) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": "belgium_peppol"},
        files={
            "file": (
                filename,
                workbook_bytes if workbook_bytes is not None else belgium_valid_workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _successful_einvoicebe_response(*, config, xml_bytes: bytes, filename: str) -> EInvoiceBEValidationResponse:
    assert config.validation_url == "https://api.e-invoice.be/api/validate/ubl"
    assert b"INV-BE-2026-001" in xml_bytes
    assert b"<cbc:CompanyID>BE0990251719</cbc:CompanyID>" in xml_bytes
    assert b'<cbc:CompanyID schemeID="0208">0990251719</cbc:CompanyID>' in xml_bytes
    assert b'<cbc:EndpointID schemeID="0208">0990251719</cbc:EndpointID>' in xml_bytes
    return EInvoiceBEValidationResponse(
        id="EINVBE-VALID-001",
        file_name=filename,
        is_valid=True,
        issues=[],
        http_status_code=201,
        raw_response={"id": "EINVBE-VALID-001", "debug": "test-einvoicebe-api-key"},
    )


def _failed_einvoicebe_response(*, config, xml_bytes: bytes, filename: str) -> EInvoiceBEValidationResponse:
    return EInvoiceBEValidationResponse(
        id="EINVBE-INVALID-001",
        file_name=filename,
        is_valid=False,
        issues=[
            EInvoiceBEValidationIssue(
                message="Mocked Peppol validation issue.",
                type="error",
                schematron="mocked_schematron",
                rule_id="MOCK-UBL-001",
            ),
            EInvoiceBEValidationIssue(
                message="Mocked Peppol validation issue.",
                type="error",
                schematron="mocked_schematron",
                rule_id="MOCK-UBL-001",
            )
        ],
        http_status_code=201,
        raw_response={"id": "EINVBE-INVALID-001"},
    )


def _clear_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EINVOICEBE_ENABLED",
        "EINVOICEBE_API_BASE_URL",
        "EINVOICEBE_API_KEY",
        "EINVOICEBE_SANDBOX_COMPANY_NUMBER",
        "EINVOICEBE_SANDBOX_PEPPOL_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def _set_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EINVOICEBE_ENABLED", "true")
    monkeypatch.setenv("EINVOICEBE_API_BASE_URL", "https://api.e-invoice.be")
    monkeypatch.setenv("EINVOICEBE_API_KEY", "test-einvoicebe-api-key")
    monkeypatch.setenv("EINVOICEBE_SANDBOX_COMPANY_NUMBER", "099025170")
    monkeypatch.setenv("EINVOICEBE_SANDBOX_PEPPOL_ID", "0208:099025170")


def _is_valid_belgian_0208_identifier(value: str) -> bool:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) != 10:
        return False
    expected_check_digits = 97 - (int(digits[:8]) % 97)
    return int(digits[8:]) == expected_check_digits


def _zip_text_files_contain(archive: ZipFile, needle: str) -> bool:
    for name in archive.namelist():
        if name.endswith((".json", ".txt", ".xml")):
            if needle in archive.read(name).decode("utf-8"):
                return True
    return False
