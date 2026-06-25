import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReviewExportPanel } from "./ReviewExportPanel";
import type { CountryPack, UploadRecord } from "../types";

describe("ReviewExportPanel", () => {
  it("does not show invoice data or enable generation/export for a selected-regime mismatch", () => {
    render(<ReviewExportPanel pack={saudiPack} uploadRecord={regimeMismatchUpload} onUploadRecordChange={vi.fn()} />);

    expect(screen.getByText("No valid invoice loaded")).toBeInTheDocument();
    expect(screen.queryByText("INV-BE-2026-001")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validate" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Export ZIP" })).toBeDisabled();
  });
});

const saudiPack: CountryPack = {
  country_pack_id: "saudi_zatca",
  display_name: "Saudi Arabia / ZATCA",
  country_code: "SA",
  pack_version: "0.4.0",
  support_level: "validation_foundation",
  v1_boundary: "Saudi validation foundation only.",
  v1_boundary_warning: "Not submitted to ZATCA/FATOORA.",
  output_profiles: ["zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf"],
  default_output_profile: "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
  requires_pdf: true,
  requires_qr: true,
  requires_signature: true,
  requires_live_submission_for_validity: true,
  live_submission_supported: false,
  live_clearance_supported: false,
  production_signing_supported: false,
  official_artefact_validation: "not_configured",
  legal_regime_summary: "Saudi ZATCA/FATOORA regime.",
  scope: ["Saudi standard B2B scenario."],
  mandatory_format: ["XML or PDF/A-3."],
  transmission_or_clearance_model: ["Clearance/reporting model."],
  qr_signature_requirements: ["QR and signature requirements."],
  retention_or_audit_notes: ["Retain evidence."],
  v1_app_capability: ["Validation foundation only."],
  official_sources: [{ label: "ZATCA", url: "https://zatca.gov.sa" }],
  regime_summary: "",
  legal_invoice_requirements: [],
  einvoice_requirements: [],
  source_status: [],
  boundary_highlights: [],
  last_reviewed: "2026-06-25"
};

const regimeMismatchUpload: UploadRecord = {
  upload_id: "UP-MISMATCH",
  original_filename: "BE-VALID-001.xlsx",
  selected_country_pack: "saudi_zatca",
  selected_output_profile: "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
  workbook_sha256_hash: "hash",
  status: "validation_failed",
  stored_workbook_path: "server/storage/uploads/BE-VALID-001.xlsx",
  canonical_json_path: "server/storage/canonical/UP-MISMATCH_canonical_invoice.json",
  validation_report_path: "server/storage/validation/UP-MISMATCH_validation_report.json",
  generated_xml_path: null,
  generated_xml_sha256_hash: null,
  canonical_invoice: {
    invoice: {
      invoice_number: "INV-BE-2026-001",
      invoice_date: "2026-06-24",
      invoice_currency_code: "EUR",
      selected_country_pack: "belgium_peppol",
      selected_output_profile: "peppol_bis_billing_3_0_ubl_invoice"
    },
    seller: { legal_name: "Demo Belgium Services BV" },
    buyer: { legal_name: "Demo Belgium Buyer NV" },
    lines: [{ line_number: 1, description: "Consulting services" }],
    tax_summary: [],
    totals: { net_total: 1000, tax_total: 210, gross_total: 1210 },
    source: {},
    metadata: {}
  },
  validation_report: {
    summary: {
      overall_status: "failed",
      internal_validation: "failed",
      official_artefact_validation: "not_configured",
      blocking_errors: 1,
      warnings_ack_required: 0,
      warnings: 0,
      passed_checks: 5
    },
    results: [
      {
        rule_id: "WB-REGIME-001",
        layer: "workbook_structure",
        severity: "error",
        status: "failed",
        message: "Wrong regime selected",
        field_path: "invoice_header.selected_country_pack",
        country_pack_id: "saudi_zatca",
        country_pack_version: "0.4.0",
        corrective_action: "This workbook is for Belgium. Switch to Belgium or upload a Saudi workbook.",
        technical_detail: null
      }
    ]
  },
  evidence_bundle_preview: {
    generation_id: "GEN-PREVIEW",
    country_pack_id: "saudi_zatca",
    country_pack_version: "0.4.0",
    output_profile_id: "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
    status: "skeleton_only_milestone_1",
    files: [
      { filename: "canonical_invoice.json", status: "stored", sha256: "hash", storage_path: "canonical.json" },
      { filename: "validation_report.json", status: "stored", sha256: "hash", storage_path: "validation.json" }
    ],
    v1_boundary: "Saudi validation foundation only."
  }
};
