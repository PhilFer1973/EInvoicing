from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.adapters.registry import get_adapter
from app.models.canonical import CanonicalInvoice
from app.models.upload import EvidenceBundlePreview, UploadRecord
from app.models.validation import ValidationReport
from app.services.country_packs import CountryPackNotFound, get_country_pack
from app.services.upload_store import get_upload, save_upload
from app.services.workbook import parse_workbook_upload
from app.storage.file_store import storage_path_from_relative


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

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        _write_stored_file(archive, "source_upload_snapshot.xlsx", record.stored_workbook_path)
        _write_stored_file(archive, "canonical_invoice.json", record.canonical_json_path)
        _write_stored_file(archive, "validation_report.json", record.validation_report_path)
        archive.writestr(
            "evidence.json",
            json.dumps(record.evidence_bundle_preview.model_dump(mode="json"), indent=2, sort_keys=True),
        )
        pack = get_country_pack(record.selected_country_pack)
        archive.writestr("country_pack_manifest.json", json.dumps(pack.model_dump(mode="json"), indent=2, sort_keys=True))
        archive.writestr("hashes.txt", _hash_manifest(record))

    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{upload_id}_evidence_bundle_skeleton.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@router.post("/{upload_id}/generate", response_model=EvidenceBundlePreview)
def generate_placeholder(upload_id: str) -> EvidenceBundlePreview:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    adapter = get_adapter(record.selected_country_pack)
    evidence = adapter.build_output_placeholder(record.canonical_invoice)
    evidence.generation_id = record.evidence_bundle_preview.generation_id
    evidence.status = "not_implemented_milestone_1"
    return evidence


def _write_stored_file(archive: ZipFile, archive_name: str, relative_path: str | None) -> None:
    if not relative_path:
        return
    path = storage_path_from_relative(relative_path)
    if path.exists():
        archive.write(path, archive_name)


def _hash_manifest(record: UploadRecord) -> str:
    lines = ["filename\tsha256\tstatus"]
    for file in record.evidence_bundle_preview.files:
        lines.append(f"{file.filename}\t{file.sha256 or 'not_available'}\t{file.status}")
    return "\n".join(lines) + "\n"
