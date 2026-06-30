export type View = "workbench" | "audit";

export interface CountryPack {
  country_pack_id: string;
  display_name: string;
  country_code: string;
  pack_version: string;
  support_level: string;
  sandbox_test_available_when_configured?: boolean;
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

export interface ExternalValidationRecord {
  provider: string;
  label: string;
  status: string;
  is_valid: boolean | null;
  reference: string | null;
  validated_at: string;
  issue_count: number;
  messages: string[];
  endpoint: string;
  peppol_delivery?: string;
  recipient_acceptance?: string;
  smp_registration_claim?: string;
  disclaimer: string;
}

export interface ExternalSandboxSendRecord {
  provider: string;
  label: string;
  status: string;
  submitted_at: string;
  provider_reference: string | null;
  document_id: string | null;
  provider_document_state: string | null;
  endpoint: string;
  messages: string[];
  sender_identity_check?: {
    tenant_owned_sender_peppol_id?: string;
    tenant_sender_scheme?: string | null;
    tenant_sender_id?: string | null;
    xml_seller_endpoint_scheme?: string | null;
    xml_seller_endpoint_id?: string | null;
    xml_seller_party_legal_company_id?: string | null;
    xml_seller_tax_scheme_company_id?: string | null;
    send_request_sender_source?: string | null;
    send_request_sender_scheme?: string | null;
    send_request_sender_id?: string | null;
    xml_sender_matches_tenant?: boolean;
    send_request_sender_matches_tenant?: boolean | null;
  } | null;
  peppol_delivery?: string;
  recipient_acceptance?: string;
  smp_registration_claim?: string;
  disclaimer: string;
}

export interface XMLValidationMessage {
  code: string;
  message: string;
  location?: string | null;
  line?: number | null;
  column?: number | null;
  detail?: string | null;
}

export interface XMLValidatorResult {
  validator_name: string;
  validator_type: string;
  status: "passed" | "failed" | "warning" | "skipped" | "not_configured" | string;
  errors: XMLValidationMessage[];
  warnings: XMLValidationMessage[];
  informational_messages: string[];
  executed_at: string;
  artefact_version?: string | null;
  artefact_path?: string | null;
  validator_executed?: boolean;
  raw_output_path?: string | null;
  metadata?: Record<string, unknown>;
}

export interface XMLValidationReport {
  overall_status: "passed" | "failed" | "warning" | string;
  executed_at: string;
  results: XMLValidatorResult[];
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
  xml_validation_report_path?: string | null;
  xml_validation_report?: XMLValidationReport | null;
  generated_at?: string | null;
  storecove_provider_reference?: string | null;
  storecove_submission_status?: string | null;
  storecove_mocked?: boolean;
  external_validation?: ExternalValidationRecord | null;
  external_sandbox_send?: ExternalSandboxSendRecord | null;
  acknowledged_warning_rule_ids?: string[];
  warning_acknowledged_at?: string | null;
  canonical_invoice: CanonicalInvoice | null;
  validation_report: ValidationReport;
  evidence_bundle_preview: EvidenceBundlePreview;
}

export interface StorecoveConfigurationStatus {
  sandbox_enabled: boolean;
  configured: boolean;
  api_base_url: string | null;
  missing_fields: string[];
  mode: "disabled" | "missing_credentials" | "configuration_error" | "mocked_sandbox" | string;
  message: string;
}

export interface EInvoiceBEConfigurationStatus {
  enabled: boolean;
  configured: boolean;
  api_base_url: string;
  sandbox_company_number: string;
  sandbox_peppol_id: string;
  missing_fields: string[];
  mode: "disabled" | "missing_credentials" | "sandbox_validation" | string;
  message: string;
}

export interface AuditEntry {
  upload_id: string;
  uploaded_at: string | null;
  generated_at: string | null;
  original_filename: string;
  invoice_number: string | null;
  country_pack: string;
  country_regime: string;
  output_profile: string | null;
  seller: string | null;
  buyer: string | null;
  currency: string | null;
  gross_amount: string | null;
  validation_status: string;
  xml_generation_status: string;
  external_validation_status: string;
  sandbox_send_status: string;
  evidence_bundle_available: boolean;
  evidence_bundle_download_url: string | null;
  warnings: number;
  pack_version: string;
}

export interface AuditEvidenceFile {
  filename: string;
  status: string;
  sha256: string | null;
  content_type: string;
  preview_available: boolean;
  download_url: string | null;
  preview_url: string | null;
}

export interface AuditDetail {
  entry: AuditEntry;
  source_upload_filename: string;
  country_pack_version: string;
  selected_output_profile: string | null;
  invoice_summary: Record<string, unknown>;
  validation_summary: Record<string, unknown>;
  generated_outputs_summary: Array<Record<string, unknown>>;
  xml_validation_summary: Record<string, unknown>;
  official_validator_status: Record<string, unknown>;
  external_validation: Record<string, unknown>;
  sandbox_send: Record<string, unknown>;
  saudi_outputs: Record<string, unknown>;
  timestamps: Record<string, unknown>;
  hashes: Record<string, unknown>;
  evidence_metadata: Record<string, unknown>;
  evidence_files: AuditEvidenceFile[];
  evidence_bundle_download_url: string | null;
}

export interface EvidenceFilePreview {
  filename: string;
  content_type: string;
  preview_available: boolean;
  kind: "json" | "text" | "binary" | string;
  content: unknown;
  message: string | null;
}
