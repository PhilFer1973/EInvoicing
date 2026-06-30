from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.models.upload import EvidenceFile, UploadRecord
from app.services.country_packs import get_country_pack
from app.services.evidence import build_evidence_metadata
from app.services.upload_store import get_upload, list_uploads
from app.storage.file_store import storage_path_from_relative


router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditEntry(BaseModel):
    upload_id: str
    uploaded_at: str | None
    generated_at: str | None
    original_filename: str
    invoice_number: str | None
    country_pack: str
    country_regime: str
    output_profile: str | None
    seller: str | None
    buyer: str | None
    currency: str | None
    gross_amount: str | None
    validation_status: str
    xml_generation_status: str
    external_validation_status: str
    sandbox_send_status: str
    evidence_bundle_available: bool
    evidence_bundle_download_url: str | None = None
    warnings: int
    pack_version: str


class AuditEvidenceFile(BaseModel):
    filename: str
    status: str
    sha256: str | None = None
    content_type: str
    preview_available: bool
    download_url: str | None = None
    preview_url: str | None = None


class AuditDetail(BaseModel):
    entry: AuditEntry
    source_upload_filename: str
    country_pack_version: str
    selected_output_profile: str | None
    invoice_summary: dict[str, Any]
    validation_summary: dict[str, Any]
    generated_outputs_summary: list[dict[str, Any]]
    xml_validation_summary: dict[str, Any]
    official_validator_status: dict[str, Any]
    external_validation: dict[str, Any]
    sandbox_send: dict[str, Any]
    saudi_outputs: dict[str, Any]
    timestamps: dict[str, Any]
    hashes: dict[str, Any]
    evidence_metadata: dict[str, Any]
    evidence_files: list[AuditEvidenceFile] = Field(default_factory=list)
    evidence_bundle_download_url: str | None = None


class EvidenceFilePreview(BaseModel):
    filename: str
    content_type: str
    preview_available: bool
    kind: str
    content: Any | None = None
    message: str | None = None


@router.get("", response_model=list[AuditEntry])
def list_audit_entries() -> list[AuditEntry]:
    return [_entry_from_record(upload) for upload in list_uploads()]


@router.get("/{upload_id}", response_model=AuditDetail)
def read_audit_detail(upload_id: str) -> AuditDetail:
    record = _require_upload(upload_id)
    metadata = _safe_evidence_metadata(record)
    entry = _entry_from_record(record)
    return AuditDetail(
        entry=entry,
        source_upload_filename=record.original_filename,
        country_pack_version=record.evidence_bundle_preview.country_pack_version,
        selected_output_profile=record.selected_output_profile,
        invoice_summary=_invoice_summary(record),
        validation_summary=record.validation_report.summary.model_dump(mode="json"),
        generated_outputs_summary=_generated_outputs_summary(record),
        xml_validation_summary=_xml_validation_summary(record),
        official_validator_status=metadata.get("official_xml_validator_status", {"status": "not_applicable"}),
        external_validation=_external_validation_summary(record, metadata),
        sandbox_send=_sandbox_send_summary(record, metadata),
        saudi_outputs=_saudi_outputs_summary(record),
        timestamps={
            "uploaded_at": record.uploaded_at,
            "generated_at": record.generated_at,
            "warning_acknowledged_at": record.warning_acknowledged_at,
        },
        hashes={
            "workbook_sha256": record.workbook_sha256_hash,
            "generated_xml_sha256": record.generated_xml_sha256_hash,
        },
        evidence_metadata=metadata,
        evidence_files=_audit_evidence_files(record),
        evidence_bundle_download_url=_evidence_bundle_url(record),
    )


@router.get("/{upload_id}/evidence-files/{filename}/preview", response_model=EvidenceFilePreview)
def preview_audit_evidence_file(upload_id: str, filename: str) -> EvidenceFilePreview:
    record = _require_upload(upload_id)
    content, content_type = _read_evidence_file(record, filename)
    if content_type == "application/json":
        try:
            parsed = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status_code=422, detail="JSON evidence file could not be parsed for preview.")
        return EvidenceFilePreview(
            filename=filename,
            content_type=content_type,
            preview_available=True,
            kind="json",
            content=parsed,
        )
    if _is_textual_content_type(content_type):
        return EvidenceFilePreview(
            filename=filename,
            content_type=content_type,
            preview_available=True,
            kind="text",
            content=content.decode("utf-8", errors="replace"),
        )
    return EvidenceFilePreview(
        filename=filename,
        content_type=content_type,
        preview_available=False,
        kind="binary",
        message="Binary evidence file preview is not available. Use download.",
    )


@router.get("/{upload_id}/evidence-files/{filename}/download")
def download_audit_evidence_file(upload_id: str, filename: str) -> Response:
    record = _require_upload(upload_id)
    content, content_type = _read_evidence_file(record, filename)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _require_upload(upload_id: str) -> UploadRecord:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit item not found.")
    return record


def _entry_from_record(record: UploadRecord) -> AuditEntry:
    invoice = record.canonical_invoice.invoice if record.canonical_invoice else {}
    seller = record.canonical_invoice.seller if record.canonical_invoice else {}
    buyer = record.canonical_invoice.buyer if record.canonical_invoice else {}
    pack = _country_pack_display(record)
    return AuditEntry(
        upload_id=record.upload_id,
        uploaded_at=record.uploaded_at,
        generated_at=record.generated_at,
        original_filename=record.original_filename,
        invoice_number=_string_or_none(invoice.get("invoice_number")),
        country_pack=record.selected_country_pack,
        country_regime=pack,
        output_profile=record.selected_output_profile,
        seller=_string_or_none(seller.get("legal_name")),
        buyer=_string_or_none(buyer.get("legal_name")),
        currency=_string_or_none(invoice.get("invoice_currency_code")),
        gross_amount=_string_or_none((record.canonical_invoice.totals if record.canonical_invoice else {}).get("gross_total")),
        validation_status=record.validation_report.summary.overall_status,
        xml_generation_status=_xml_generation_status(record),
        external_validation_status=_external_validation_status(record),
        sandbox_send_status=_sandbox_send_status(record),
        evidence_bundle_available=bool(record.evidence_bundle_preview),
        evidence_bundle_download_url=_evidence_bundle_url(record),
        warnings=record.validation_report.summary.warnings + record.validation_report.summary.warnings_ack_required,
        pack_version=record.evidence_bundle_preview.country_pack_version,
    )


def _country_pack_display(record: UploadRecord) -> str:
    try:
        return get_country_pack(record.selected_country_pack).display_name
    except Exception:
        return record.selected_country_pack


def _invoice_summary(record: UploadRecord) -> dict[str, Any]:
    if not record.canonical_invoice:
        return {"status": "not_available"}
    invoice = record.canonical_invoice.invoice
    totals = record.canonical_invoice.totals
    return {
        "invoice_number": invoice.get("invoice_number"),
        "invoice_date": invoice.get("invoice_date"),
        "invoice_time": invoice.get("invoice_time"),
        "currency": invoice.get("invoice_currency_code"),
        "seller": record.canonical_invoice.seller.get("legal_name"),
        "buyer": record.canonical_invoice.buyer.get("legal_name"),
        "net": totals.get("net_total"),
        "tax": totals.get("tax_total"),
        "gross": totals.get("gross_total"),
        "line_count": len(record.canonical_invoice.lines),
    }


def _generated_outputs_summary(record: UploadRecord) -> list[dict[str, Any]]:
    core_files = {
        "source_upload_snapshot.xlsx",
        "canonical_invoice.json",
        "validation_report.json",
        "country_pack_manifest.json",
        "hashes.txt",
        "evidence.json",
        "evidence_metadata.json",
    }
    return [
        {
            "filename": evidence_file.filename,
            "status": evidence_file.status,
            "sha256": evidence_file.sha256,
        }
        for evidence_file in _merged_evidence_file_records(record)
        if evidence_file.filename not in core_files and evidence_file.status == "stored"
    ]


def _xml_validation_summary(record: UploadRecord) -> dict[str, Any]:
    if not record.xml_validation_report:
        return {"overall_status": "not_run" if record.selected_country_pack == "belgium_peppol" else "not_applicable"}
    return {
        "overall_status": record.xml_validation_report.overall_status,
        "executed_at": record.xml_validation_report.executed_at,
        "results": [
            {
                "validator_name": result.validator_name,
                "validator_type": result.validator_type,
                "status": result.status,
                "errors": len(result.errors),
                "warnings": len(result.warnings),
                "validator_executed": result.validator_executed,
            }
            for result in record.xml_validation_report.results
        ],
    }


def _external_validation_summary(record: UploadRecord, metadata: dict[str, Any]) -> dict[str, Any]:
    if record.external_validation:
        return record.external_validation.model_dump(mode="json")
    return metadata.get("external_validation", {"status": "not_applicable"})


def _sandbox_send_summary(record: UploadRecord, metadata: dict[str, Any]) -> dict[str, Any]:
    if record.external_sandbox_send:
        return record.external_sandbox_send.model_dump(mode="json")
    return metadata.get("external_sandbox_send", {"status": "not_applicable"})


def _saudi_outputs_summary(record: UploadRecord) -> dict[str, Any]:
    if record.selected_country_pack != "saudi_zatca":
        return {"status": "not_applicable"}
    files = {file.filename: file.status for file in record.evidence_bundle_preview.files}
    return {
        "xml": files.get("invoice.xml", "not_available"),
        "qr": files.get("qr.png", "not_available"),
        "decoded_qr": files.get("qr_payload_decoded.json", "not_available"),
        "visual_pdf": files.get("saudi_visual_invoice.pdf", "not_available"),
        "boundary_acknowledged": bool(record.warning_acknowledged_at),
    }


def _safe_evidence_metadata(record: UploadRecord) -> dict[str, Any]:
    try:
        return build_evidence_metadata(record, get_country_pack(record.selected_country_pack))
    except Exception as exc:
        return {
            "status": "metadata_unavailable",
            "message": "Evidence metadata could not be assembled for this audit item.",
            "technical_detail": str(exc),
        }


def _audit_evidence_files(record: UploadRecord) -> list[AuditEvidenceFile]:
    files: list[AuditEvidenceFile] = []
    for evidence_file in _merged_evidence_file_records(record):
        content_type = _content_type_for_filename(evidence_file.filename)
        available = bool(evidence_file.storage_path) or evidence_file.filename in _dynamic_evidence_filenames()
        files.append(
            AuditEvidenceFile(
                filename=evidence_file.filename,
                status="available" if evidence_file.filename in _dynamic_evidence_filenames() else evidence_file.status,
                sha256=evidence_file.sha256,
                content_type=content_type,
                preview_available=available and (content_type == "application/json" or _is_textual_content_type(content_type)),
                download_url=f"/api/audit/{record.upload_id}/evidence-files/{evidence_file.filename}/download" if available else None,
                preview_url=f"/api/audit/{record.upload_id}/evidence-files/{evidence_file.filename}/preview" if available else None,
            )
        )
    return files


def _merged_evidence_file_records(record: UploadRecord) -> list[EvidenceFile]:
    by_filename = {file.filename: file.model_copy() for file in record.evidence_bundle_preview.files}
    for filename in _dynamic_evidence_filenames():
        by_filename.setdefault(filename, EvidenceFile(filename=filename, status="available"))
    return sorted(by_filename.values(), key=lambda file: file.filename)


def _read_evidence_file(record: UploadRecord, filename: str) -> tuple[bytes, str]:
    if filename in {"evidence.json", "evidence_metadata.json"}:
        content = json.dumps(_safe_evidence_metadata(record), indent=2, sort_keys=True).encode("utf-8")
        return content, "application/json"
    if filename == "country_pack_manifest.json":
        content = json.dumps(get_country_pack(record.selected_country_pack).model_dump(mode="json"), indent=2, sort_keys=True).encode(
            "utf-8"
        )
        return content, "application/json"
    if filename == "hashes.txt":
        return _hash_manifest(record).encode("utf-8"), "text/plain"

    storage_path = _storage_path_for_filename(record, filename)
    if not storage_path:
        raise HTTPException(status_code=404, detail="Evidence file is not available for this audit item.")
    path = storage_path_from_relative(storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored evidence file is missing.")
    return path.read_bytes(), _content_type_for_filename(filename)


def _storage_path_for_filename(record: UploadRecord, filename: str) -> str | None:
    direct_paths = {
        "source_upload_snapshot.xlsx": record.stored_workbook_path,
        "canonical_invoice.json": record.canonical_json_path,
        "validation_report.json": record.validation_report_path,
        "invoice.xml": record.generated_xml_path,
        "xml_validation_report.json": record.xml_validation_report_path,
    }
    if filename in direct_paths:
        return direct_paths[filename]
    evidence_file = next((file for file in record.evidence_bundle_preview.files if file.filename == filename), None)
    return evidence_file.storage_path if evidence_file else None


def _hash_manifest(record: UploadRecord) -> str:
    lines = ["filename\tsha256\tstatus"]
    for file in _merged_evidence_file_records(record):
        lines.append(f"{file.filename}\t{file.sha256 or 'not_available'}\t{file.status}")
    return "\n".join(lines) + "\n"


def _dynamic_evidence_filenames() -> set[str]:
    return {"evidence.json", "evidence_metadata.json", "country_pack_manifest.json", "hashes.txt"}


def _content_type_for_filename(filename: str) -> str:
    if filename.endswith(".json"):
        return "application/json"
    if filename.endswith(".xml"):
        return "application/xml"
    if filename.endswith(".svrl"):
        return "application/xml"
    if filename.endswith(".txt"):
        return "text/plain"
    if filename.endswith(".pdf"):
        return "application/pdf"
    if filename.endswith(".png"):
        return "image/png"
    if filename.endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream"


def _is_textual_content_type(content_type: str) -> bool:
    return content_type.startswith("text/") or content_type in {"application/xml"}


def _xml_generation_status(record: UploadRecord) -> str:
    if record.selected_country_pack not in {"belgium_peppol", "saudi_zatca"}:
        return "not_applicable"
    return "generated" if record.generated_xml_path else "not_generated"


def _external_validation_status(record: UploadRecord) -> str:
    if record.external_validation:
        return record.external_validation.status
    return "not_run" if record.selected_country_pack == "belgium_peppol" else "not_applicable"


def _sandbox_send_status(record: UploadRecord) -> str:
    if record.external_sandbox_send:
        return record.external_sandbox_send.status
    if record.selected_country_pack == "belgium_peppol":
        return "not_run"
    if record.selected_country_pack == "uk_info":
        return record.storecove_submission_status or "not_run"
    return "not_applicable"


def _evidence_bundle_url(record: UploadRecord) -> str | None:
    if not record.evidence_bundle_preview:
        return None
    return f"/api/uploads/{record.upload_id}/evidence-bundle/download"


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
