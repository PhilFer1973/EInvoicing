from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app
from tests.workbook_fixtures import belgium_valid_workbook_bytes, saudi_valid_workbook_bytes


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_valid_saudi_sample_workbook_passes_with_boundary_warnings(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes())

    assert payload["status"] == "validated"
    assert payload["validation_report"]["summary"]["blocking_errors"] == 0
    assert payload["validation_report"]["summary"]["overall_status"] == "passed_with_warnings"
    assert payload["validation_report"]["summary"]["warnings_ack_required"] == 6
    assert _has_failed_rule(payload, "SA-V1-BOUNDARY-001")
    assert _has_failed_rule(payload, "SA-V1-BOUNDARY-006")


async def test_selecting_saudi_and_uploading_belgium_workbook_is_regime_mismatch(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, belgium_valid_workbook_bytes())

    assert payload["status"] == "validation_failed"
    assert payload["validation_report"]["summary"]["blocking_errors"] == 1
    assert _has_failed_rule(payload, "WB-REGIME-001")
    mismatch = next(result for result in _results(payload) if result["rule_id"] == "WB-REGIME-001")
    assert mismatch["message"] == "Wrong regime selected"
    assert mismatch["corrective_action"] == "This workbook is for Belgium. Switch to Belgium or upload a Saudi workbook."


async def test_missing_invoice_time_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(invoice_time=""))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-INV-001")


async def test_missing_invoice_date_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(invoice_date=""))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "GEN-DATE-001")


async def test_missing_seller_vat_tin_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(seller_vat=""))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-SELLER-001")


async def test_invalid_seller_vat_tin_format_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(seller_vat="100000000000001"))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-SELLER-002")


async def test_missing_buyer_vat_tin_for_b2b_standard_invoice_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(buyer_vat=""))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-BUYER-001")


async def test_saudi_vat_total_mismatch_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(tax_total=1501.00))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-ARITH-002")


async def test_unsupported_simplified_invoice_profile_is_blocking_for_v1(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(
        client,
        saudi_valid_workbook_bytes(
            invoice_type="simplified_invoice",
            selected_output_profile="zatca_simplified_invoice_reporting",
        ),
    )

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-INV-TYPE-001")


async def test_missing_line_description_is_blocking(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes(line_description=""))

    assert payload["validation_report"]["summary"]["blocking_errors"] >= 1
    assert _has_failed_rule(payload, "SA-LINE-001")


async def test_saudi_canonical_invoice_contains_expected_sections(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes())
    canonical = payload["canonical_invoice"]

    assert canonical["seller"]["legal_name"] == "Demo Saudi Services LLC"
    assert canonical["buyer"]["legal_name"] == "Demo Saudi Buyer LLC"
    assert canonical["invoice"]["invoice_number"] == "INV-SA-2026-001"
    assert canonical["invoice"]["invoice_time"] == "10:30:00"
    assert canonical["lines"][0]["description"] == "Consulting services"
    assert canonical["tax_summary"] == [
        {
            "tax_category_code": "S",
            "tax_rate": "15",
            "taxable_amount": "10000.00",
            "tax_amount": "1500.00",
        }
    ]
    assert canonical["totals"]["net_total"] == 10000
    assert canonical["totals"]["tax_total"] == 1500
    assert canonical["totals"]["gross_total"] == 11500
    assert canonical["metadata"]["rounding_policy"] == {
        "mode": "half_up",
        "amount_decimals": 2,
        "vat_summary_validation": "document_level_by_vat_category_and_rate",
    }

    response = await client.get(f"/api/uploads/{payload['upload_id']}/canonical-invoice")
    assert response.status_code == 200
    assert response.json()["invoice"]["invoice_number"] == "INV-SA-2026-001"


async def test_saudi_evidence_bundle_skeleton_contains_core_artefacts(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes())
    files = {file["filename"]: file for file in payload["evidence_bundle_preview"]["files"]}

    assert files["source_upload_snapshot.xlsx"]["status"] == "stored"
    assert files["canonical_invoice.json"]["status"] == "stored"
    assert files["validation_report.json"]["status"] == "stored"
    assert files["country_pack_manifest.json"]["status"] == "preview_available"
    assert files["invoice.xml"]["status"] == "not_implemented_milestone_3a"
    assert files["invoice_arabic_bilingual_visual.pdf"]["status"] == "not_implemented_milestone_3a"
    assert files["qr.png"]["status"] == "not_implemented_milestone_3a"

    response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert "source_upload_snapshot.xlsx" in names
        assert "canonical_invoice.json" in names
        assert "validation_report.json" in names
        assert "country_pack_manifest.json" in names
        assert "invoice.xml" not in names
        assert "qr.png" not in names
        assert "invoice_arabic_bilingual_visual.pdf" not in names


async def test_saudi_generation_endpoint_does_not_generate_xml_qr_or_pdf_in_milestone_3a(client: AsyncClient) -> None:
    payload = await _upload_saudi_workbook(client, saudi_valid_workbook_bytes())

    response = await client.post(f"/api/uploads/{payload['upload_id']}/generate")

    assert response.status_code == 400
    assert "Saudi XML, QR and PDF generation are not implemented in Milestone 3A" in response.text


async def _upload_saudi_workbook(client: AsyncClient, workbook_bytes: bytes) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": "saudi_zatca"},
        files={
            "file": (
                "SA-VALID-001.xlsx",
                workbook_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _results(payload: dict) -> list[dict]:
    return payload["validation_report"]["results"]


def _has_failed_rule(payload: dict, rule_id: str) -> bool:
    return any(result["rule_id"] == rule_id and result["status"] == "failed" for result in _results(payload))
