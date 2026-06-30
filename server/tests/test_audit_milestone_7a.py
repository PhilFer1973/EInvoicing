from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
import pytest

from app.integrations.einvoicebe.schemas import EInvoiceBESandboxSendResponse, EInvoiceBEValidationResponse
from app.main import app
from app.services.upload_store import clear_uploads_for_tests
from tests.workbook_fixtures import (
    belgium_einvoicebe_send_workbook_bytes,
    belgium_valid_workbook_bytes,
    saudi_valid_workbook_bytes,
    uk_valid_workbook_bytes,
)


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def clean_audit_store() -> None:
    clear_uploads_for_tests()
    yield
    clear_uploads_for_tests()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_audit_list_and_detail_show_belgium_generation(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_einvoicebe_env(monkeypatch)
    upload = await _upload(client, "belgium_peppol", "BE-VALID-001.xlsx", belgium_valid_workbook_bytes())
    generate_response = await client.post(f"/api/uploads/{upload['upload_id']}/generate")

    list_response = await client.get("/api/audit")
    detail_response = await client.get(f"/api/audit/{upload['upload_id']}")

    assert generate_response.status_code == 200
    assert list_response.status_code == 200
    entries = list_response.json()
    assert entries[0]["invoice_number"] == "INV-BE-2026-001"
    assert entries[0]["country_regime"] == "Belgium / Peppol BIS Billing 3.0"
    assert entries[0]["validation_status"] == "passed"
    assert entries[0]["xml_generation_status"] == "generated"
    assert entries[0]["external_validation_status"] == "not_run"
    assert entries[0]["evidence_bundle_available"] is True

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["source_upload_filename"] == "BE-VALID-001.xlsx"
    assert detail["invoice_summary"]["seller"] == "Demo Belgium Services BV"
    assert detail["invoice_summary"]["buyer"] == "Demo Belgium Buyer NV"
    assert detail["validation_summary"]["overall_status"] == "passed"
    assert detail["xml_validation_summary"]["overall_status"] == "passed"
    assert detail["official_validator_status"]["en16931_validation_status"] == "not_configured"
    assert detail["evidence_bundle_download_url"].endswith("/evidence-bundle/download")
    assert "xml_validation_report.json" in {file["filename"] for file in detail["evidence_files"]}


async def test_audit_evidence_json_preview_and_zip_download(client: AsyncClient) -> None:
    upload = await _upload(client, "belgium_peppol", "BE-VALID-001.xlsx", belgium_valid_workbook_bytes())
    await client.post(f"/api/uploads/{upload['upload_id']}/generate")

    preview_response = await client.get(f"/api/audit/{upload['upload_id']}/evidence-files/evidence_metadata.json/preview")
    download_response = await client.get(f"/api/uploads/{upload['upload_id']}/evidence-bundle/download")

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["kind"] == "json"
    assert preview["content"]["selected_country_pack"] == "belgium_peppol"
    assert preview["content"]["official_xml_validator_status"]["en16931_validation_status"] == "not_configured"

    assert download_response.status_code == 200
    with ZipFile(BytesIO(download_response.content)) as archive:
        assert "evidence_metadata.json" in archive.namelist()


async def test_audit_missing_evidence_file_returns_clear_404(client: AsyncClient) -> None:
    upload = await _upload(client, "belgium_peppol", "BE-VALID-001.xlsx", belgium_valid_workbook_bytes())

    response = await client.get(f"/api/audit/{upload['upload_id']}/evidence-files/not-real.json/preview")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence file is not available for this audit item."


async def test_audit_detail_shows_external_validation_and_sandbox_send_status(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    monkeypatch.setattr("app.api.uploads.submit_ubl_validation", _successful_einvoicebe_response)
    monkeypatch.setattr("app.api.uploads.submit_ubl_sandbox_send", _failed_einvoicebe_send_response)
    upload = await _upload(
        client,
        "belgium_peppol",
        "BE-EINVOICEBE-SEND-001.xlsx",
        belgium_einvoicebe_send_workbook_bytes(),
    )
    validation_response = await client.post(f"/api/uploads/{upload['upload_id']}/validate-pipeline")
    send_response = await client.post(f"/api/uploads/{upload['upload_id']}/einvoicebe-sandbox-send")
    detail_response = await client.get(f"/api/audit/{upload['upload_id']}")

    assert validation_response.status_code == 200
    assert send_response.status_code == 200
    detail = detail_response.json()
    assert detail["external_validation"]["status"] == "passed"
    assert detail["sandbox_send"]["status"] == "failed"
    assert detail["sandbox_send"]["recipient_acceptance"] == "not_claimed"
    evidence_filenames = {file["filename"] for file in detail["evidence_files"]}
    assert "einvoicebe_validation_response.json" in evidence_filenames
    assert "einvoicebe_send_response.json" in evidence_filenames

    send_preview = await client.get(f"/api/audit/{upload['upload_id']}/evidence-files/einvoicebe_send_response.json/preview")
    assert send_preview.status_code == 200
    assert send_preview.json()["content"]["status"] == "failed"


async def test_audit_detail_handles_saudi_outputs(client: AsyncClient) -> None:
    upload = await _upload(client, "saudi_zatca", "SA-VALID-001.xlsx", saudi_valid_workbook_bytes())
    await client.post(f"/api/uploads/{upload['upload_id']}/acknowledge-boundaries")
    generate_response = await client.post(f"/api/uploads/{upload['upload_id']}/generate")
    detail_response = await client.get(f"/api/audit/{upload['upload_id']}")

    assert generate_response.status_code == 200
    detail = detail_response.json()
    assert detail["entry"]["country_regime"] == "Saudi Arabia / ZATCA"
    assert detail["entry"]["xml_generation_status"] == "generated"
    assert detail["saudi_outputs"]["qr"] == "stored"
    assert detail["saudi_outputs"]["visual_pdf"] == "stored"


async def test_audit_detail_handles_uk_roadmap_upload(client: AsyncClient) -> None:
    upload = await _upload(client, "uk_info", "UK-PEPPOL-SANDBOX-001.xlsx", uk_valid_workbook_bytes())
    detail_response = await client.get(f"/api/audit/{upload['upload_id']}")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["entry"]["country_regime"] == "United Kingdom / 2029 Peppol Roadmap"
    assert detail["entry"]["xml_generation_status"] == "not_applicable"
    assert detail["evidence_metadata"]["storecove_sandbox"]["disclaimer"].startswith("UK Peppol sandbox test only")


async def _upload(client: AsyncClient, country_pack: str, filename: str, content: bytes) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": country_pack},
        files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _set_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EINVOICEBE_ENABLED", "true")
    monkeypatch.setenv("EINVOICEBE_API_BASE_URL", "https://api.e-invoice.be")
    monkeypatch.setenv("EINVOICEBE_API_KEY", "test-einvoicebe-api-key")
    monkeypatch.setenv("EINVOICEBE_SANDBOX_COMPANY_NUMBER", "099025170")
    monkeypatch.setenv("EINVOICEBE_SANDBOX_PEPPOL_ID", "0208:099025170")


def _clear_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "EINVOICEBE_ENABLED",
        "EINVOICEBE_API_BASE_URL",
        "EINVOICEBE_API_KEY",
        "EINVOICEBE_SANDBOX_COMPANY_NUMBER",
        "EINVOICEBE_SANDBOX_PEPPOL_ID",
    ]:
        monkeypatch.delenv(key, raising=False)


def _successful_einvoicebe_response(**kwargs) -> EInvoiceBEValidationResponse:
    return EInvoiceBEValidationResponse(
        id="EINVBE-VALID-AUDIT-001",
        file_name=kwargs.get("filename"),
        is_valid=True,
        issues=[],
        ubl_document=None,
        raw_response={"id": "EINVBE-VALID-AUDIT-001", "is_valid": True},
    )


def _failed_einvoicebe_send_response(**kwargs) -> EInvoiceBESandboxSendResponse:
    return EInvoiceBESandboxSendResponse(
        document_id="DOC-AUDIT-001",
        provider_reference="DOC-AUDIT-001",
        status="failed",
        message="Sandbox provider rejected the send for audit test.",
        create_http_status_code=201,
        send_http_status_code=422,
        provider_document_state="rejected",
        create_response={"id": "DOC-AUDIT-001"},
        send_response={"error": "Sandbox provider rejected the send for audit test."},
    )
