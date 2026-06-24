from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.adapters.registry import get_adapter
from app.models.upload import EvidenceBundlePreview, UploadRecord
from app.models.validation import ValidationReport
from app.services.country_packs import CountryPackNotFound, get_country_pack
from app.services.upload_store import get_upload, save_upload
from app.services.workbook import parse_workbook_upload


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

