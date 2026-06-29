from __future__ import annotations

from io import BytesIO
import json
import unicodedata
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
from pypdf import PdfReader
import pytest

from app.main import app
from app.services.saudi_qr import decode_tlv_payload, encode_tlv
from tests.workbook_fixtures import saudi_valid_workbook_bytes


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


def test_tlv_encoder_uses_utf8_byte_length() -> None:
    encoded = encode_tlv([(1, "شركة")])

    assert encoded[0] == 1
    assert encoded[1] == len("شركة".encode("utf-8"))
    assert encoded[2:] == "شركة".encode("utf-8")


async def test_saudi_qr_payload_contains_phase_one_tags_only(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client)
    await _generate_saudi_outputs(client, payload["upload_id"])

    response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-qr-payload/download")

    assert response.status_code == 200
    fields = decode_tlv_payload(response.text)
    assert [tag for tag, _ in fields] == [1, 2, 3, 4, 5]
    assert dict(fields) == {
        1: "Demo Saudi Services LLC",
        2: "300000000000003",
        3: "2026-06-24T10:30:00",
        4: "11500.00",
        5: "1500.00",
    }
    assert not ({6, 7, 8, 9} & {tag for tag, _ in fields})


async def test_saudi_generation_makes_qr_png_and_visual_pdf_available(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client)
    evidence = await _generate_saudi_outputs(client, payload["upload_id"])
    files = {file["filename"]: file for file in evidence["files"]}

    assert evidence["status"] == "outputs_generated_milestone_3c"
    for filename in (
        "invoice.xml",
        "qr_payload_base64.txt",
        "qr_payload_decoded.json",
        "qr.png",
        "saudi_visual_invoice.pdf",
    ):
        assert files[filename]["status"] == "stored"
        assert files[filename]["sha256"]
        assert files[filename]["storage_path"]

    qr_response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-qr")
    pdf_response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-pdf")

    assert qr_response.status_code == 200
    assert qr_response.headers["content-type"] == "image/png"
    assert qr_response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF-")


async def test_saudi_visual_pdf_contains_invoice_data_qr_and_boundary_footer(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client)
    await _generate_saudi_outputs(client, payload["upload_id"])

    response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-pdf")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Tax Invoice" in text
    assert "INV-SA-2026-001" in text
    assert "300000000000003" in text
    assert "300000000000004" in text
    assert "1,500.00" in text
    assert "11,500.00" in text
    assert "خدمات استشارية" in _normalise_pdf_arabic(text)
    assert "Consulting services" in text
    assert "Generated in offline demo mode." in text
    assert b"/Subtype /Image" in response.content


async def test_saudi_visual_pdf_falls_back_to_english_line_description(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(line_description_ar=""))
    await _generate_saudi_outputs(client, payload["upload_id"])

    response = await client.get(f"/api/uploads/{payload['upload_id']}/generated-pdf")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Consulting services" in text
    assert "خدمات استشارية" not in _normalise_pdf_arabic(text)


async def test_saudi_evidence_bundle_contains_all_milestone_3c_outputs(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client)
    await _generate_saudi_outputs(client, payload["upload_id"])
    acknowledgement = await client.post(f"/api/uploads/{payload['upload_id']}/acknowledge-boundaries")
    assert acknowledgement.status_code == 200

    response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")

    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {
            "source_upload_snapshot.xlsx",
            "canonical_invoice.json",
            "validation_report.json",
            "country_pack_manifest.json",
            "invoice.xml",
            "qr_payload_base64.txt",
            "qr_payload_decoded.json",
            "qr.png",
            "saudi_visual_invoice.pdf",
            "hashes.txt",
        } <= names
        assert archive.read("qr.png").startswith(b"\x89PNG\r\n\x1a\n")
        assert decode_tlv_payload(archive.read("qr_payload_base64.txt").decode("ascii"))[-1] == (5, "1500.00")
        decoded_payload = json.loads(archive.read("qr_payload_decoded.json"))
        assert decoded_payload["phase_two_tags_included"] is False
        assert decoded_payload["tags"] == [
            {"tag": 1, "label": "Seller name", "field": "seller_name", "value": "Demo Saudi Services LLC"},
            {"tag": 2, "label": "Seller VAT/TIN", "field": "seller_vat_tin", "value": "300000000000003"},
            {"tag": 3, "label": "Invoice timestamp", "field": "invoice_timestamp", "value": "2026-06-24T10:30:00"},
            {"tag": 4, "label": "Invoice total including VAT", "field": "invoice_total_including_vat", "value": "11500.00"},
            {"tag": 5, "label": "VAT total", "field": "vat_total", "value": "1500.00"},
        ]
        assert archive.read("saudi_visual_invoice.pdf").startswith(b"%PDF-")
        evidence = json.loads(archive.read("evidence.json"))
        assert evidence["generated_at"]
        assert evidence["validation"]["internal_validation"] == "passed"
        assert evidence["warning_acknowledgement"]["acknowledged"] is True
        assert evidence["official_artefact_validation"]["status"] == "not_configured"
        assert "no ZATCA SDK validation" in evidence["official_artefact_validation"]["note"]
        assert {output["filename"] for output in evidence["generated_outputs"]} >= {
            "invoice.xml",
            "qr_payload_base64.txt",
            "qr_payload_decoded.json",
            "qr.png",
            "saudi_visual_invoice.pdf",
        }


async def test_saudi_generated_bundle_requires_boundary_acknowledgement(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client)
    await _generate_saudi_outputs(client, payload["upload_id"])

    blocked = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert blocked.status_code == 409
    assert "Acknowledge the V1 boundary warnings" in blocked.text

    acknowledged = await client.post(f"/api/uploads/{payload['upload_id']}/acknowledge-boundaries")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_warning_rule_ids"]
    assert acknowledged.json()["warning_acknowledged_at"]


async def test_saudi_generation_remains_blocked_by_validation_errors(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(invoice_time=""))

    response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")

    assert response.status_code == 409
    assert "Blocking validation errors" in response.text


async def _upload_saudi_workbook(client: AsyncClient, workbook_bytes: bytes | None = None) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": "saudi_zatca"},
        files={
            "file": (
                "SA-VALID-001.xlsx",
                workbook_bytes or saudi_valid_workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


async def _generate_saudi_outputs(client: AsyncClient, upload_id: str) -> dict:
    response = await client.post(f"/api/uploads/{upload_id}/generate")
    assert response.status_code == 200, response.text
    return response.json()


def _normalise_pdf_arabic(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace("\u06cc", "\u064a").replace("\u06a9", "\u0643")
