from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.models.canonical import CanonicalInvoice
from app.models.upload import EvidenceBundlePreview, UploadRecord
from app.models.validation import ValidationReport
from app.services.country_packs import CountryPackNotFound, get_country_pack
from app.services.evidence import build_evidence_metadata
from app.services.saudi_pdf import SaudiVisualPdfError, generate_saudi_visual_invoice_pdf
from app.services.saudi_qr import generate_saudi_phase_one_qr
from app.services.saudi_xml import generate_saudi_zatca_invoice_xml
from app.services.upload_store import get_upload, save_upload
from app.services.ubl_xml import generate_belgium_ubl_invoice_xml
from app.services.workbook import parse_workbook_upload
from app.storage.file_store import relative_storage_path, save_binary, storage_path_from_relative


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("", response_model=UploadRecord)
async def create_upload(
    selected_country_pack: str = Form(...),
    file: UploadFile = File(...),
) -> UploadRecord:
    try:
        pack = get_country_pack(selected_country_pack)
    except CountryPackNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    record = parse_workbook_upload(content, file.filename or "upload.xlsx", pack)
    return save_upload(record)


@router.get("/{upload_id}", response_model=UploadRecord)
def read_upload(upload_id: str) -> UploadRecord:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record


@router.post("/{upload_id}/validate", response_model=ValidationReport)
def validate_upload(upload_id: str) -> ValidationReport:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record.validation_report


@router.get("/{upload_id}/validation-results", response_model=ValidationReport)
def read_validation_results(upload_id: str) -> ValidationReport:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record.validation_report


@router.get("/{upload_id}/canonical-invoice", response_model=CanonicalInvoice)
def read_canonical_invoice(upload_id: str) -> CanonicalInvoice:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.canonical_invoice:
        raise HTTPException(status_code=404, detail="Canonical invoice JSON is not available for this upload.")
    return record.canonical_invoice


@router.get("/{upload_id}/canonical-invoice/download")
def download_canonical_invoice(upload_id: str) -> FileResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.canonical_json_path:
        raise HTTPException(status_code=404, detail="Canonical invoice JSON is not available for this upload.")
    path = storage_path_from_relative(record.canonical_json_path)
    return FileResponse(path, media_type="application/json", filename=f"{upload_id}_canonical_invoice.json")


@router.get("/{upload_id}/evidence-bundle/download")
def download_evidence_bundle(upload_id: str) -> StreamingResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.evidence_bundle_preview:
        raise HTTPException(status_code=404, detail="Evidence bundle skeleton is not available for this upload.")
    if record.status == "generated" and _requires_acknowledgement(record) and not _acknowledgement_complete(record):
        raise HTTPException(
            status_code=409,
            detail="Acknowledge the V1 boundary warnings before exporting this evidence bundle.",
        )

    pack = get_country_pack(record.selected_country_pack)
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        _write_stored_file(archive, "source_upload_snapshot.xlsx", record.stored_workbook_path)
        _write_stored_file(archive, "canonical_invoice.json", record.canonical_json_path)
        _write_stored_file(archive, "validation_report.json", record.validation_report_path)
        _write_stored_file(archive, "invoice.xml", record.generated_xml_path)
        _write_evidence_file(archive, record, "qr_payload_base64.txt")
        _write_evidence_file(archive, record, "qr_payload_decoded.json")
        _write_evidence_file(archive, record, "qr.png")
        _write_evidence_file(archive, record, "saudi_visual_invoice.pdf")
        archive.writestr(
            "evidence.json",
            json.dumps(build_evidence_metadata(record, pack), indent=2, sort_keys=True),
        )
        archive.writestr("country_pack_manifest.json", json.dumps(pack.model_dump(mode="json"), indent=2, sort_keys=True))
        archive.writestr("hashes.txt", _hash_manifest(record))

    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{upload_id}_evidence_bundle_skeleton.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@router.post("/{upload_id}/acknowledge-boundaries", response_model=UploadRecord)
def acknowledge_boundary_warnings(upload_id: str) -> UploadRecord:
    record = _require_upload(upload_id)
    required_rule_ids = _required_acknowledgement_rule_ids(record)
    if not required_rule_ids:
        return record

    record.acknowledged_warning_rule_ids = required_rule_ids
    record.warning_acknowledged_at = datetime.now(timezone.utc).isoformat()
    return save_upload(record)


@router.post("/{upload_id}/generate", response_model=EvidenceBundlePreview)
def generate_output(upload_id: str) -> EvidenceBundlePreview:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if record.selected_country_pack not in {"belgium_peppol", "saudi_zatca"}:
        raise HTTPException(
            status_code=400,
            detail="Generation is not configured for the selected country pack.",
        )
    if not record.canonical_invoice:
        raise HTTPException(status_code=400, detail="Canonical invoice JSON is required before XML generation.")
    if record.validation_report.summary.blocking_errors > 0:
        raise HTTPException(status_code=409, detail="Blocking validation errors must be resolved before XML generation.")

    if record.selected_country_pack == "saudi_zatca":
        try:
            xml_content = generate_saudi_zatca_invoice_xml(record.canonical_invoice)
            qr = generate_saudi_phase_one_qr(record.canonical_invoice)
            pdf_content = generate_saudi_visual_invoice_pdf(record.canonical_invoice, qr.png_bytes)
        except SaudiVisualPdfError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Saudi output data is incomplete: {exc}") from exc

        generated_filename = f"{upload_id}_saudi_zatca_offline_invoice.xml"
        qr_payload_base64_filename = f"{upload_id}_saudi_zatca_phase1_qr_payload_base64.txt"
        qr_payload_decoded_filename = f"{upload_id}_saudi_zatca_phase1_qr_payload_decoded.json"
        qr_image_filename = f"{upload_id}_saudi_zatca_phase1_qr.png"
        pdf_filename = f"{upload_id}_saudi_zatca_visual_invoice.pdf"
        evidence_status = "outputs_generated_milestone_3c"
    else:
        xml_content = generate_belgium_ubl_invoice_xml(record.canonical_invoice)
        generated_filename = f"{upload_id}_belgium_peppol_invoice.xml"
        evidence_status = "xml_generated_milestone_2b"

    xml_path, xml_hash = save_binary("generated", generated_filename, xml_content)
    record.generated_xml_path = relative_storage_path(xml_path)
    record.generated_xml_sha256_hash = xml_hash
    _mark_generated_file(record, "invoice.xml", record.generated_xml_path, xml_hash)

    if record.selected_country_pack == "saudi_zatca":
        qr_payload_path, qr_payload_hash = save_binary(
            "generated", qr_payload_base64_filename, qr.payload_base64.encode("ascii")
        )
        qr_decoded_path, qr_decoded_hash = save_binary(
            "generated",
            qr_payload_decoded_filename,
            json.dumps(qr.decoded_payload, indent=2, ensure_ascii=False).encode("utf-8"),
        )
        qr_image_path, qr_image_hash = save_binary("generated", qr_image_filename, qr.png_bytes)
        pdf_path, pdf_hash = save_binary("generated", pdf_filename, pdf_content)
        _mark_generated_file(record, "qr_payload_base64.txt", relative_storage_path(qr_payload_path), qr_payload_hash)
        _mark_generated_file(record, "qr_payload_decoded.json", relative_storage_path(qr_decoded_path), qr_decoded_hash)
        _mark_generated_file(record, "qr.png", relative_storage_path(qr_image_path), qr_image_hash)
        _mark_generated_file(record, "saudi_visual_invoice.pdf", relative_storage_path(pdf_path), pdf_hash)

    record.status = "generated"
    record.generated_at = datetime.now(timezone.utc).isoformat()
    record.evidence_bundle_preview.status = evidence_status
    save_upload(record)
    return record.evidence_bundle_preview


@router.get("/{upload_id}/generated-xml")
def read_generated_xml(upload_id: str) -> FileResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.generated_xml_path:
        raise HTTPException(status_code=404, detail="Generated XML is not available for this upload.")
    path = storage_path_from_relative(record.generated_xml_path)
    return FileResponse(path, media_type="application/xml")


@router.get("/{upload_id}/generated-xml/download")
def download_generated_xml(upload_id: str) -> FileResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.generated_xml_path:
        raise HTTPException(status_code=404, detail="Generated XML is not available for this upload.")
    path = storage_path_from_relative(record.generated_xml_path)
    return FileResponse(path, media_type="application/xml", filename=_generated_xml_filename(record))


@router.get("/{upload_id}/generated-qr")
def read_generated_qr(upload_id: str) -> FileResponse:
    return _generated_evidence_file(upload_id, "qr.png", "image/png", "Saudi QR image")


@router.get("/{upload_id}/generated-qr/download")
def download_generated_qr(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "qr.png",
        "image/png",
        "Saudi QR image",
        filename=f"{record.upload_id}_saudi_zatca_phase1_qr.png",
    )


@router.get("/{upload_id}/generated-pdf")
def read_generated_pdf(upload_id: str) -> FileResponse:
    return _generated_evidence_file(upload_id, "saudi_visual_invoice.pdf", "application/pdf", "Saudi visual PDF")


@router.get("/{upload_id}/generated-pdf/download")
def download_generated_pdf(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "saudi_visual_invoice.pdf",
        "application/pdf",
        "Saudi visual PDF",
        filename=f"{record.upload_id}_saudi_zatca_visual_invoice.pdf",
    )


@router.get("/{upload_id}/generated-qr-payload/download")
def download_generated_qr_payload(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "qr_payload_base64.txt",
        "text/plain",
        "Saudi QR payload",
        filename=f"{record.upload_id}_saudi_zatca_phase1_qr_payload_base64.txt",
    )


@router.get("/{upload_id}/generated-qr-payload-decoded")
def read_generated_qr_payload_decoded(upload_id: str) -> FileResponse:
    return _generated_evidence_file(
        upload_id,
        "qr_payload_decoded.json",
        "application/json",
        "Decoded Saudi QR payload",
    )


@router.get("/{upload_id}/generated-qr-payload-decoded/download")
def download_generated_qr_payload_decoded(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "qr_payload_decoded.json",
        "application/json",
        "Decoded Saudi QR payload",
        filename=f"{record.upload_id}_saudi_zatca_phase1_qr_payload_decoded.json",
    )


def _write_stored_file(archive: ZipFile, archive_name: str, relative_path: str | None) -> None:
    if not relative_path:
        return
    path = storage_path_from_relative(relative_path)
    if path.exists():
        archive.write(path, archive_name)


def _write_evidence_file(archive: ZipFile, record: UploadRecord, filename: str) -> None:
    evidence_file = next((file for file in record.evidence_bundle_preview.files if file.filename == filename), None)
    _write_stored_file(archive, filename, evidence_file.storage_path if evidence_file else None)


def _hash_manifest(record: UploadRecord) -> str:
    lines = ["filename\tsha256\tstatus"]
    for file in record.evidence_bundle_preview.files:
        lines.append(f"{file.filename}\t{file.sha256 or 'not_available'}\t{file.status}")
    return "\n".join(lines) + "\n"


def _required_acknowledgement_rule_ids(record: UploadRecord) -> list[str]:
    return [
        result.rule_id
        for result in record.validation_report.results
        if result.severity == "warning_ack_required" and result.status == "failed"
    ]


def _requires_acknowledgement(record: UploadRecord) -> bool:
    return bool(_required_acknowledgement_rule_ids(record))


def _acknowledgement_complete(record: UploadRecord) -> bool:
    required_rule_ids = _required_acknowledgement_rule_ids(record)
    return all(rule_id in record.acknowledged_warning_rule_ids for rule_id in required_rule_ids)


def _mark_generated_file(record: UploadRecord, filename: str, storage_path: str, sha256: str) -> None:
    for file in record.evidence_bundle_preview.files:
        if file.filename == filename:
            file.status = "stored"
            file.sha256 = sha256
            file.storage_path = storage_path
            return


def _require_upload(upload_id: str) -> UploadRecord:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record


def _generated_evidence_file(
    upload_id: str,
    evidence_filename: str,
    media_type: str,
    display_name: str,
    filename: str | None = None,
) -> FileResponse:
    record = _require_upload(upload_id)
    evidence_file = next((file for file in record.evidence_bundle_preview.files if file.filename == evidence_filename), None)
    if not evidence_file or not evidence_file.storage_path:
        raise HTTPException(status_code=404, detail=f"{display_name} is not available for this upload.")
    path = storage_path_from_relative(evidence_file.storage_path)
    return FileResponse(path, media_type=media_type, filename=filename)


def _generated_xml_filename(record: UploadRecord) -> str:
    if record.selected_country_pack == "saudi_zatca":
        return f"{record.upload_id}_saudi_zatca_offline_invoice.xml"
    return f"{record.upload_id}_belgium_peppol_invoice.xml"
