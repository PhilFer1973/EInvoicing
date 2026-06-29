export type View = "workbench" | "audit";

export interface CountryPack {
  country_pack_id: string;
  display_name: string;
  country_code: string;
  pack_version: string;
  support_level: string;
  v1_boundary: string;
  v1_boundary_warning: string;
  output_profiles: string[];
  default_output_profile: string | null;
  requires_pdf: boolean;
  requires_qr: boolean;
  requires_signature: boolean;
  requires_live_submission_for_validity: boolean;
  live_submission_supported: boolean;
  live_clearance_supported?: boolean;
  production_signing_supported?: boolean;
  official_artefact_validation: "not_configured" | "configuration_error" | "passed" | "failed";
  legal_regime_summary: string;
  scope: string[];
  mandatory_format: string[];
  transmission_or_clearance_model: string[];
  qr_signature_requirements: string[];
  retention_or_audit_notes: string[];
  v1_app_capability: string[];
  official_sources: Array<{
    label: string;
    url: string;
  }>;
  regime_summary: string;
  legal_invoice_requirements: string[];
  einvoice_requirements: string[];
  source_status: string[];
  boundary_highlights: string[];
  last_reviewed: string;
}

export interface CountryPackList {
  country_packs: CountryPack[];
}

export interface ValidationResult {
  rule_id: string;
  layer: string;
  severity: "error" | "warning_ack_required" | "warning" | "info";
  status: "passed" | "failed" | "not_configured" | "acknowledged";
  message: string;
  field_path: string | null;
  country_pack_id: string | null;
  country_pack_version: string | null;
  corrective_action: string | null;
  technical_detail: string | null;
}

export interface ValidationSummary {
  overall_status: "not_uploaded" | "failed" | "passed" | "passed_with_warnings" | "not_implemented_milestone_1";
  internal_validation: "not_run" | "failed" | "passed" | "passed_with_warnings";
  official_artefact_validation: "not_configured" | "configuration_error" | "passed" | "failed";
  blocking_errors: number;
  warnings_ack_required: number;
  warnings: number;
  passed_checks: number;
}

export interface ValidationReport {
  summary: ValidationSummary;
  results: ValidationResult[];
}

export interface TaxSummaryLine {
  tax_category_code: string;
  tax_rate: string;
  taxable_amount: string;
  tax_amount: string;
}

export interface CanonicalInvoice {
  invoice: Record<string, unknown>;
  seller: Record<string, unknown>;
  buyer: Record<string, unknown>;
  lines: Array<Record<string, unknown>>;
  tax_summary: TaxSummaryLine[];
  totals: Record<string, unknown>;
  source: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface EvidenceFile {
  filename: string;
  status: string;
  sha256: string | null;
  storage_path: string | null;
}

export interface EvidenceBundlePreview {
  generation_id: string;
  country_pack_id: string;
  country_pack_version: string;
  output_profile_id: string | null;
  status: string;
  files: EvidenceFile[];
  v1_boundary: string;
}

export interface DecodedQrPayload {
  encoding: string;
  phase: string;
  phase_two_tags_included: boolean;
  tags: Array<{
    tag: number;
    label: string;
    field: string;
    value: string;
  }>;
}

export interface UploadRecord {
  upload_id: string;
  original_filename: string;
  selected_country_pack: string;
  selected_output_profile: string | null;
  workbook_sha256_hash: string;
  status: string;
  stored_workbook_path: string | null;
  canonical_json_path: string | null;
  validation_report_path: string | null;
  generated_xml_path: string | null;
  generated_xml_sha256_hash: string | null;
  generated_at?: string | null;
  acknowledged_warning_rule_ids?: string[];
  warning_acknowledged_at?: string | null;
  canonical_invoice: CanonicalInvoice | null;
  validation_report: ValidationReport;
  evidence_bundle_preview: EvidenceBundlePreview;
}

export interface AuditEntry {
  generated_at: string;
  invoice_number: string | null;
  country_pack: string;
  output_profile: string | null;
  status: string;
  warnings: number;
  pack_version: string;
  download_zip: string | null;
}
