from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app
from app.models.canonical import CanonicalInvoice
from app.services.ubl_xml import generate_belgium_ubl_invoice_xml
from app.validation.xml_validator import validate_belgium_invoice_xml, validate_xml_well_formedness
from tests.workbook_fixtures import belgium_valid_workbook_bytes


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_valid_belgium_pipeline_runs_xml_validation_and_adds_evidence(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client)

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert response.status_code == 200
    record = response.json()
    xml_report = record["xml_validation_report"]
    assert xml_report["overall_status"] == "passed"
    statuses = {result["validator_type"]: result["status"] for result in xml_report["results"]}
    assert statuses["xml_well_formedness"] == "passed"
    assert statuses["ubl_structure"] == "passed"
    assert statuses["peppol_readiness"] == "passed"
    assert statuses["ubl_xsd"] == "not_configured"
    assert statuses["en16931"] == "not_configured"
    assert statuses["peppol_schematron"] == "not_configured"

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    assert (
        bundle_response.headers["content-disposition"]
        == 'attachment; filename="INV-BE-2026-001_belgium_evidence_bundle.zip"'
    )
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert "xml_validation_report.json" in names
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["xml_validation"]["overall_status"] == "passed"
        assert evidence["official_xml_validator_status"]["status"] == "not_configured"
        assert "Official validator not configured in this milestone" in evidence["official_xml_validator_status"]["note"]


def test_malformed_xml_fails_well_formedness_cleanly() -> None:
    result = validate_xml_well_formedness(b"<?xml version='1.0'?><Invoice><Broken></Invoice>")

    assert result.status == "failed"
    assert result.errors[0].code == "XML-WELLFORMED-001"
    assert result.errors[0].line is not None
    assert result.errors[0].column is not None


async def test_generated_belgium_xml_passes_basic_ubl_structure_checks(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(client)
    xml = _xml_for_payload(payload)

    report = validate_belgium_invoice_xml(xml)

    structure = _result(report, "ubl_structure")
    assert structure["status"] == "passed"
    assert structure["errors"] == []


async def test_missing_key_ubl_element_creates_failed_structure_check(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(client)
    xml = _xml_for_payload(payload)
    xml = xml.replace(
        b"  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>\n",
        b"",
    )

    report = validate_belgium_invoice_xml(xml)

    structure = _result(report, "ubl_structure")
    assert structure["status"] == "failed"
    assert any(error["code"] == "UBL-CUSTOMIZATION-001" for error in structure["errors"])


async def test_peppol_readiness_passes_for_valid_belgium_sample(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(client)
    report = validate_belgium_invoice_xml(_xml_for_payload(payload))

    readiness = _result(report, "peppol_readiness")
    assert readiness["status"] == "passed"
    assert readiness["errors"] == []


async def test_missing_buyer_reference_or_purchase_order_creates_readiness_failure(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(client)
    xml = _xml_for_payload(payload)
    xml = xml.replace(b"  <cbc:BuyerReference>BE-BUYER-REF-001</cbc:BuyerReference>\n", b"")

    report = validate_belgium_invoice_xml(xml)

    readiness = _result(report, "peppol_readiness")
    assert readiness["status"] == "failed"
    assert any(error["code"] == "PEPPOL-REFERENCE-001" for error in readiness["errors"])


async def _upload_belgium_workbook(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": "belgium_peppol"},
        files={
            "file": (
                "BE-VALID-001.xlsx",
                belgium_valid_workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _xml_for_payload(payload: dict) -> bytes:
    canonical = CanonicalInvoice.model_validate(payload["canonical_invoice"])
    return generate_belgium_ubl_invoice_xml(canonical)


def _result(report, validator_type: str) -> dict:
    payload = report.model_dump(mode="json")
    return next(result for result in payload["results"] if result["validator_type"] == validator_type)


def _clear_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EINVOICEBE_ENABLED",
        "EINVOICEBE_API_BASE_URL",
        "EINVOICEBE_API_KEY",
        "EINVOICEBE_SANDBOX_COMPANY_NUMBER",
        "EINVOICEBE_SANDBOX_PEPPOL_ID",
    ):
        monkeypatch.delenv(name, raising=False)
