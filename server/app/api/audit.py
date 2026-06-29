from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.upload_store import list_uploads


router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditEntry(BaseModel):
    generated_at: str
    invoice_number: str | None
    country_pack: str
    output_profile: str | None
    status: str
    warnings: int
    pack_version: str
    download_zip: str | None = None


@router.get("", response_model=list[AuditEntry])
def list_audit_entries() -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for upload in list_uploads():
        canonical = upload.canonical_invoice
        entries.append(
            AuditEntry(
                generated_at=upload.generated_at or "Not generated",
                invoice_number=canonical.invoice.get("invoice_number") if canonical else None,
                country_pack=upload.selected_country_pack,
                output_profile=upload.selected_output_profile,
                status=upload.status,
                warnings=upload.validation_report.summary.warnings + upload.validation_report.summary.warnings_ack_required,
                pack_version=upload.evidence_bundle_preview.country_pack_version,
                download_zip=(
                    f"/api/uploads/{upload.upload_id}/evidence-bundle/download"
                    if upload.status in {"generated", "storecove_sandbox_mocked"}
                    else None
                ),
            )
        )
    return entries
