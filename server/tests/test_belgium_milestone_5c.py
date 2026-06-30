from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
import pytest

from app.integrations.einvoicebe.schemas import (
    EInvoiceBESandboxSendResponse,
    EInvoiceBEValidationResponse,
)
from app.main import app
from tests.workbook_fixtures import belgium_einvoicebe_send_workbook_bytes, belgium_valid_workbook_bytes


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_einvoicebe_sandbox_send_disabled_when_not_configured(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client)
    validation_response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    send_response = await client.post(f"/api/uploads/{payload['upload_id']}/einvoicebe-sandbox-send")

    assert validation_response.status_code == 200
    assert validation_response.json()["external_validation"]["status"] == "not_configured"
    assert send_response.status_code == 409
    assert "External e-invoice.be sandbox validation must pass" in send_response.text

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["external_sandbox_send"]["status"] == "not_run"
        assert evidence["external_sandbox_send"]["attempted"] is False
        assert evidence["external_sandbox_send"]["message"] == "External e-invoice.be sandbox send not run."


async def test_einvoicebe_sandbox_send_disabled_if_internal_validation_has_not_passed(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client, belgium_valid_workbook_bytes(invoice_number=None))
    await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    send_response = await client.post(f"/api/uploads/{payload['upload_id']}/einvoicebe-sandbox-send")

    assert send_response.status_code == 409
    assert "Internal validation must pass" in send_response.text


async def test_einvoicebe_sandbox_send_disabled_if_external_validation_has_not_passed(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    payload = await _upload_belgium_workbook(client)
    generate_response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")

    send_response = await client.post(f"/api/uploads/{payload['upload_id']}/einvoicebe-sandbox-send")

    assert generate_response.status_code == 200
    assert send_response.status_code == 409
    assert "External e-invoice.be sandbox validation must pass" in send_response.text


async def test_mocked_einvoicebe_sandbox_send_response_is_captured_in_evidence(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch, peppol_id="0208:0990251719", company_number="0990251719")
    monkeypatch.setattr("app.api.uploads.submit_ubl_validation", _successful_einvoicebe_validation)
    monkeypatch.setattr("app.api.uploads.submit_ubl_sandbox_send", _successful_einvoicebe_send)
    payload = await _upload_belgium_workbook(
        client,
        belgium_einvoicebe_send_workbook_bytes(
            seller_peppol_id="0208:0990251719",
            seller_einvoicebe_sender_peppol_id="0208:0990251719",
        ),
        "BE-EINVOICEBE-SEND-001.xlsx",
    )
    validation_response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    send_response = await client.post(f"/api/uploads/{payload['upload_id']}/einvoicebe-sandbox-send")

    assert validation_response.status_code == 200
    assert send_response.status_code == 200, send_response.text
    record = send_response.json()
    assert record["external_sandbox_send"]["status"] == "submitted"
    assert record["external_sandbox_send"]["provider_reference"] == "DOC-SEND-001"
    assert record["external_sandbox_send"]["peppol_delivery"] == "not_claimed"
    assert record["external_sandbox_send"]["recipient_acceptance"] == "not_claimed"

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert {
            "einvoicebe_send_request.json",
            "einvoicebe_send_response.json",
            "external_sandbox_send_status.json",
            "einvoicebe_send_provider_reference.txt",
            "evidence_metadata.json",
        } <= names
        request_payload = json.loads(archive.read("einvoicebe_send_request.json"))
        response_payload = json.loads(archive.read("einvoicebe_send_response.json"))
        status_payload = json.loads(archive.read("external_sandbox_send_status.json"))
        evidence = json.loads(archive.read("evidence_metadata.json"))

        assert request_payload["create_endpoint"] == "https://api.e-invoice.be/api/documents/ubl"
        assert request_payload["send_endpoint"] == "https://api.e-invoice.be/api/documents/DOC-SEND-001/send"
        assert request_payload["authorization"] == "[REDACTED]"
        assert request_payload["form_fields"][0]["name"] == "file"
        assert "sender_peppol_scheme" not in request_payload["query_parameters"]
        assert "sender_peppol_id" not in request_payload["query_parameters"]
        assert request_payload["query_parameters"]["receiver_peppol_scheme"] == "0208"
        assert request_payload["query_parameters"]["receiver_peppol_id"] == "0987654394"
        assert response_payload["provider_reference"] == "DOC-SEND-001"
        assert response_payload["status"] == "submitted"
        assert status_payload["status"] == "submitted"
        assert status_payload["sender_identity_check"]["xml_seller_endpoint_scheme"] == "0208"
        assert status_payload["sender_identity_check"]["xml_seller_endpoint_id"] == "0990251719"
        assert status_payload["sender_identity_check"]["xml_seller_party_legal_company_id"] == "0990251719"
        assert status_payload["sender_identity_check"]["xml_seller_tax_scheme_company_id"] == "BE0990251719"
        assert status_payload["sender_identity_check"]["send_request_sender_source"] == "omitted_provider_tenant_inferred"
        assert status_payload["sender_identity_check"]["send_request_sender_scheme"] is None
        assert status_payload["sender_identity_check"]["send_request_sender_id"] is None
        assert status_payload["sender_identity_check"]["xml_sender_matches_tenant"] is True
        assert status_payload["sender_identity_check"]["send_request_sender_matches_tenant"] is None
        assert evidence["external_sandbox_send"]["status"] == "submitted"
        assert evidence["sandbox_sender_identity_check"]["xml_sender_matches_tenant"] is True
        assert evidence["sandbox_sender_identity_check"]["send_request_sender_source"] == "omitted_provider_tenant_inferred"
        assert evidence["external_sandbox_send"]["peppol_delivery"] == "not_claimed"
        assert evidence["external_sandbox_send"]["recipient_acceptance"] == "not_claimed"
        assert "Sandbox send only" in evidence["external_sandbox_send"]["disclaimer"]
        assert archive.read("einvoicebe_send_provider_reference.txt").decode("utf-8") == "DOC-SEND-001"
        assert not _zip_text_files_contain(archive, "test-einvoicebe-api-key")


async def test_mocked_einvoicebe_sandbox_send_failure_is_reported_clearly(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    monkeypatch.setattr("app.api.uploads.submit_ubl_validation", _successful_einvoicebe_validation)
    monkeypatch.setattr("app.api.uploads.submit_ubl_sandbox_send", _failed_einvoicebe_send)
    payload = await _upload_belgium_workbook(
        client,
        belgium_einvoicebe_send_workbook_bytes(),
        "BE-EINVOICEBE-SEND-001.xlsx",
    )
    await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    send_response = await client.post(f"/api/uploads/{payload['upload_id']}/einvoicebe-sandbox-send")

    assert send_response.status_code == 200, send_response.text
    record = send_response.json()
    assert record["external_sandbox_send"]["status"] == "failed"
    assert record["external_sandbox_send"]["messages"] == [
        "Sandbox provider rejected the send because the tenant does not own the sender Peppol ID in the generated Belgium XML. This is the known e-invoice.be sandbox identity limitation.",
        "Document is not allowed to be sent - tenant does not own the sender Peppol ID",
    ]
    assert record["status"] == "einvoicebe_sandbox_send_failed"

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["external_validation"]["status"] == "passed"
        assert evidence["external_sandbox_send"]["status"] == "failed"
        assert evidence["external_sandbox_send"]["attempted"] is True
        assert evidence["external_sandbox_send"]["provider_error_message"] == "Document is not allowed to be sent - tenant does not own the sender Peppol ID"
        assert evidence["external_sandbox_send"]["messages"] == [
            "Sandbox provider rejected the send because the tenant does not own the sender Peppol ID in the generated Belgium XML. This is the known e-invoice.be sandbox identity limitation.",
            "Document is not allowed to be sent - tenant does not own the sender Peppol ID",
        ]
        assert evidence["sandbox_sender_identity_check"]["xml_sender_matches_tenant"] is False
        assert evidence["sandbox_sender_identity_check"]["send_request_sender_matches_tenant"] is None
        assert "sandbox tenant Peppol ID mismatch" in evidence["external_sandbox_send"]["known_limitation"]
        assert "sandbox tenant Peppol ID mismatch" in evidence["known_limitations"][0]


async def test_einvoicebe_validation_is_not_locally_blocked_for_send_fixture(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    validation_mock = _ValidationCallRecorder()
    monkeypatch.setattr("app.api.uploads.submit_ubl_validation", validation_mock)
    payload = await _upload_belgium_workbook(
        client,
        belgium_einvoicebe_send_workbook_bytes(),
        "BE-EINVOICEBE-SEND-001.xlsx",
    )

    validation_response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert validation_response.status_code == 200
    record = validation_response.json()
    assert record["external_validation"]["status"] == "passed"
    assert validation_mock.called is True
    assert b'<cbc:EndpointID schemeID="0208">0990251719</cbc:EndpointID>' in validation_mock.xml_bytes


async def test_einvoicebe_sandbox_send_attempts_provider_when_xml_sender_differs_from_tenant(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_einvoicebe_env(monkeypatch)
    monkeypatch.setattr("app.api.uploads.submit_ubl_validation", _successful_einvoicebe_validation)
    send_mock = _SendFailureRecorder()
    monkeypatch.setattr("app.api.uploads.submit_ubl_sandbox_send", send_mock)
    payload = await _upload_belgium_workbook(
        client,
        belgium_einvoicebe_send_workbook_bytes(),
        "BE-EINVOICEBE-SEND-001.xlsx",
    )
    validation_response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    send_response = await client.post(f"/api/uploads/{payload['upload_id']}/einvoicebe-sandbox-send")

    assert validation_response.status_code == 200
    assert validation_response.json()["external_validation"]["status"] == "passed"
    assert send_response.status_code == 200
    assert send_mock.called is True
    record = send_response.json()
    assert record["external_sandbox_send"]["status"] == "failed"
    assert record["external_sandbox_send"]["sender_identity_check"]["tenant_owned_sender_peppol_id"] == "0208:099025170"
    assert record["external_sandbox_send"]["sender_identity_check"]["xml_seller_endpoint_id"] == "0990251719"
    assert record["external_sandbox_send"]["sender_identity_check"]["xml_sender_matches_tenant"] is False


async def test_checked_in_einvoicebe_send_workbook_uses_valid_endpoint_and_tenant_send_metadata(client: AsyncClient) -> None:
    workbook_path = (
        Path(__file__).resolve().parents[2]
        / "test_data"
        / "workbooks"
        / "BE-EINVOICEBE-SEND-001.xlsx"
    )

    payload = await _upload_belgium_workbook(client, workbook_path.read_bytes(), "BE-EINVOICEBE-SEND-001.xlsx")
    canonical = payload["canonical_invoice"]

    assert canonical["seller"]["legal_name"] == "Test Company BV"
    assert canonical["seller"]["tax_registration_number"] == "BE0990251719"
    assert canonical["seller"]["company_number"] == "0990251719"
    assert canonical["seller"]["enterprise_number"] == "0990251719"
    assert canonical["seller"]["peppol_id"] == "0208:0990251719"
    assert canonical["seller"]["einvoicebe_sender_peppol_id"] == "0208:099025170"
    assert isinstance(canonical["seller"]["peppol_id"], str)
    assert isinstance(canonical["seller"]["company_number"], str)

    generate_response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")
    assert generate_response.status_code == 200
    xml_response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-xml")
    xml = xml_response.text
    assert '<cbc:EndpointID schemeID="0208">0990251719</cbc:EndpointID>' in xml
    assert '<cbc:EndpointID schemeID="0208">099025170</cbc:EndpointID>' not in xml
    assert "<cbc:CompanyID>BE0990251719</cbc:CompanyID>" in xml
    assert '<cbc:CompanyID schemeID="0208">0990251719</cbc:CompanyID>' in xml


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


def _successful_einvoicebe_validation(*, config, xml_bytes: bytes, filename: str) -> EInvoiceBEValidationResponse:
    return EInvoiceBEValidationResponse(
        id="EINVBE-VALID-001",
        file_name=filename,
        is_valid=True,
        issues=[],
        http_status_code=201,
        raw_response={"id": "EINVBE-VALID-001"},
    )


def _successful_einvoicebe_send(
    *,
    config,
    xml_bytes: bytes,
    filename: str,
    sender_peppol_id: str | None = None,
    receiver_peppol_id: str | None = None,
) -> EInvoiceBESandboxSendResponse:
    assert config.document_ubl_url == "https://api.e-invoice.be/api/documents/ubl"
    assert config.document_send_url("DOC-SEND-001") == "https://api.e-invoice.be/api/documents/DOC-SEND-001/send"
    assert sender_peppol_id is None
    assert receiver_peppol_id == "0208:0987654394"
    assert b"INV-BE-2026-001" in xml_bytes
    expected_endpoint = config.sandbox_peppol_id.split(":", 1)[1].encode("utf-8")
    assert b'<cbc:EndpointID schemeID="0208">' + expected_endpoint + b"</cbc:EndpointID>" in xml_bytes
    assert b'<cbc:CompanyID schemeID="0208">0990251719</cbc:CompanyID>' in xml_bytes
    return EInvoiceBESandboxSendResponse(
        document_id="DOC-SEND-001",
        provider_reference="DOC-SEND-001",
        status="submitted",
        message="Sandbox send submitted to e-invoice.be.",
        create_http_status_code=201,
        send_http_status_code=200,
        provider_document_state="TRANSIT",
        create_response={"id": "DOC-SEND-001", "state": "DRAFT", "debug": "test-einvoicebe-api-key"},
        send_response={"id": "DOC-SEND-001", "state": "TRANSIT", "debug": "test-einvoicebe-api-key"},
    )


def _failed_einvoicebe_send(
    *,
    config,
    xml_bytes: bytes,
    filename: str,
    sender_peppol_id: str | None = None,
    receiver_peppol_id: str | None = None,
) -> EInvoiceBESandboxSendResponse:
    return EInvoiceBESandboxSendResponse(
        document_id="DOC-SEND-FAILED",
        provider_reference="DOC-SEND-FAILED",
        status="failed",
        message="Document is not allowed to be sent - tenant does not own the sender Peppol ID",
        create_http_status_code=201,
        send_http_status_code=400,
        provider_document_state="DRAFT",
        create_response={"id": "DOC-SEND-FAILED", "state": "DRAFT"},
        send_response={"detail": "Document is not allowed to be sent - tenant does not own the sender Peppol ID"},
    )


class _SendFailureRecorder:
    called = False

    def __call__(self, **kwargs) -> EInvoiceBESandboxSendResponse:
        self.called = True
        return _failed_einvoicebe_send(**kwargs)


class _ValidationCallRecorder:
    called = False
    xml_bytes: bytes = b""

    def __call__(self, **kwargs) -> EInvoiceBEValidationResponse:
        self.called = True
        self.xml_bytes = kwargs["xml_bytes"]
        return _successful_einvoicebe_validation(**kwargs)


def _clear_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EINVOICEBE_ENABLED",
        "EINVOICEBE_API_BASE_URL",
        "EINVOICEBE_API_KEY",
        "EINVOICEBE_SANDBOX_COMPANY_NUMBER",
        "EINVOICEBE_SANDBOX_PEPPOL_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def _set_einvoicebe_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    company_number: str = "099025170",
    peppol_id: str = "0208:099025170",
) -> None:
    monkeypatch.setenv("EINVOICEBE_ENABLED", "true")
    monkeypatch.setenv("EINVOICEBE_API_BASE_URL", "https://api.e-invoice.be")
    monkeypatch.setenv("EINVOICEBE_API_KEY", "test-einvoicebe-api-key")
    monkeypatch.setenv("EINVOICEBE_SANDBOX_COMPANY_NUMBER", company_number)
    monkeypatch.setenv("EINVOICEBE_SANDBOX_PEPPOL_ID", peppol_id)


def _zip_text_files_contain(archive: ZipFile, needle: str) -> bool:
    for name in archive.namelist():
        if name.endswith((".json", ".txt", ".xml")):
            if needle in archive.read(name).decode("utf-8"):
                return True
    return False
