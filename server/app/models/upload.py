from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.canonical import CanonicalInvoice
from app.models.validation import ValidationReport


class EvidenceFile(BaseModel):
    filename: str
    status: str
    sha256: str | None = None
    storage_path: str | None = None


class EvidenceBundlePreview(BaseModel):
    generation_id: str
    country_pack_id: str
    country_pack_version: str
    output_profile_id: str | None = None
    status: str
    files: list[EvidenceFile] = Field(default_factory=list)
    v1_boundary: str


class UploadRecord(BaseModel):
    upload_id: str
    original_filename: str
    selected_country_pack: str
    selected_output_profile: str | None = None
    workbook_sha256_hash: str
    status: str
    stored_workbook_path: str | None = None
    canonical_json_path: str | None = None
    validation_report_path: str | None = None
    generated_xml_path: str | None = None
    generated_xml_sha256_hash: str | None = None
    generated_at: str | None = None
    acknowledged_warning_rule_ids: list[str] = Field(default_factory=list)
    warning_acknowledged_at: str | None = None
    canonical_invoice: CanonicalInvoice | None = None
    validation_report: ValidationReport
    evidence_bundle_preview: EvidenceBundlePreview
