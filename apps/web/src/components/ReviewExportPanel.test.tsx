import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
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

  it("enables offline Saudi XML generation after validation passes", () => {
    render(<ReviewExportPanel pack={saudiPack} uploadRecord={validSaudiUpload} onUploadRecordChange={vi.fn()} />);

    expect(screen.getByText("INV-SA-2026-001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate" })).toBeEnabled();
  });

  it("requires Saudi V1 boundary acknowledgement before evidence export", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...validSaudiUpload,
          acknowledged_warning_rule_ids: ["SA-BOUNDARY-001"],
          warning_acknowledged_at: "2026-06-26T17:00:00+00:00"
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    function StatefulPanel() {
      const [record, setRecord] = useState(validSaudiUpload);
      return <ReviewExportPanel pack={saudiPack} uploadRecord={record} onUploadRecordChange={setRecord} />;
    }

    render(<StatefulPanel />);
    expect(screen.getByRole("button", { name: "Export ZIP" })).toBeDisabled();

    fireEvent.click(screen.getByRole("checkbox"));

    await waitFor(() => expect(screen.getByRole("link", { name: "Export ZIP" })).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/uploads/UP-SA-VALID/acknowledge-boundaries",
      { method: "POST" }
    );
    vi.unstubAllGlobals();
  });

  it("shows the decoded QR fields after Saudi output generation", async () => {
    const generatedEvidence = {
      ...validSaudiUpload.evidence_bundle_preview,
      status: "outputs_generated_milestone_3c",
      files: [
        { filename: "invoice.xml", status: "stored", sha256: "xml-hash", storage_path: "generated/invoice.xml" },
        { filename: "qr.png", status: "stored", sha256: "qr-hash", storage_path: "generated/qr.png" },
        { filename: "qr_payload_base64.txt", status: "stored", sha256: "payload-hash", storage_path: "generated/qr.txt" },
        { filename: "qr_payload_decoded.json", status: "stored", sha256: "decoded-hash", storage_path: "generated/qr.json" },
        { filename: "saudi_visual_invoice.pdf", status: "stored", sha256: "pdf-hash", storage_path: "generated/invoice.pdf" }
      ]
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(generatedEvidence), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            encoding: "base64_tlv_utf8",
            phase: "phase_1_tags_1_to_5",
            phase_two_tags_included: false,
            tags: [
              { tag: 1, label: "Seller name", field: "seller_name", value: "Demo Saudi Services LLC" },
              { tag: 2, label: "Seller VAT/TIN", field: "seller_vat_tin", value: "300000000000003" },
              { tag: 3, label: "Invoice timestamp", field: "invoice_timestamp", value: "2026-06-24T10:30:00" },
              { tag: 4, label: "Invoice total including VAT", field: "invoice_total_including_vat", value: "11500.00" },
              { tag: 5, label: "VAT total", field: "vat_total", value: "1500.00" }
            ]
          }),
          { status: 200 }
        )
      );
    vi.stubGlobal("fetch", fetchMock);

    function StatefulPanel() {
      const [record, setRecord] = useState(validSaudiUpload);
      return <ReviewExportPanel pack={saudiPack} uploadRecord={record} onUploadRecordChange={setRecord} />;
    }

    render(<StatefulPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Decoded QR payload" })).toBeInTheDocument());
    const decodedPanel = screen.getByRole("region", { name: "Decoded QR payload" });
    expect(within(decodedPanel).getByText("Tag 1: Seller name")).toBeInTheDocument();
    expect(within(decodedPanel).getByText("Demo Saudi Services LLC")).toBeInTheDocument();
    expect(screen.getByText("Normal QR scanners may show an encoded TLV string. Use the decoded QR payload view to inspect the invoice fields.")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("keeps Generate disabled for the UK pack when Storecove is not configured", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          sandbox_enabled: false,
          configured: false,
          api_base_url: null,
          missing_fields: [
            "STORECOVE_API_BASE_URL",
            "STORECOVE_API_KEY",
            "STORECOVE_SENDER_LEGAL_ENTITY_ID",
            "STORECOVE_RECEIVER_LEGAL_ENTITY_ID"
          ],
          mode: "disabled",
          message: "Storecove sandbox is not configured. Add sandbox credentials to enable UK Peppol testing."
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ReviewExportPanel pack={ukPack} uploadRecord={validUkUpload} onUploadRecordChange={vi.fn()} />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/uploads/storecove-sandbox/configuration", undefined));
    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
    expect(screen.queryByText("Storecove sandbox is not configured. Add sandbox credentials to enable UK Peppol testing.")).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});

const saudiPack: CountryPack = {
  country_pack_id: "saudi_zatca",
  display_name: "Saudi Arabia / ZATCA",
  country_code: "SA",
  pack_version: "0.5.0",
  support_level: "offline_xml_generation",
  v1_boundary: "Saudi offline XML only.",
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

const validSaudiUpload: UploadRecord = {
  upload_id: "UP-SA-VALID",
  original_filename: "SA-VALID-001.xlsx",
  selected_country_pack: "saudi_zatca",
  selected_output_profile: "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
  workbook_sha256_hash: "hash",
  status: "validated",
  stored_workbook_path: "server/storage/uploads/SA-VALID-001.xlsx",
  canonical_json_path: "server/storage/canonical/UP-SA-VALID_canonical_invoice.json",
  validation_report_path: "server/storage/validation/UP-SA-VALID_validation_report.json",
  generated_xml_path: null,
  generated_xml_sha256_hash: null,
  canonical_invoice: {
    invoice: {
      invoice_number: "INV-SA-2026-001",
      invoice_date: "2026-06-24",
      invoice_time: "10:30:00",
      invoice_currency_code: "SAR",
      tax_currency_code: "SAR",
      selected_country_pack: "saudi_zatca",
      selected_output_profile: "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf"
    },
    seller: { legal_name: "Demo Saudi Services LLC", tax_registration_number: "300000000000003" },
    buyer: { legal_name: "Demo Saudi Buyer LLC", tax_registration_number: "300000000000004" },
    lines: [{ line_number: 1, description: "Consulting services" }],
    tax_summary: [{ tax_category_code: "S", tax_rate: "15", taxable_amount: "10000.00", tax_amount: "1500.00" }],
    totals: { net_total: 10000, tax_total: 1500, gross_total: 11500 },
    source: {},
    metadata: {}
  },
  validation_report: {
    summary: {
      overall_status: "passed_with_warnings",
      internal_validation: "passed_with_warnings",
      official_artefact_validation: "not_configured",
      blocking_errors: 0,
      warnings_ack_required: 6,
      warnings: 0,
      passed_checks: 8
    },
    results: []
  },
  evidence_bundle_preview: {
    generation_id: "GEN-PREVIEW",
    country_pack_id: "saudi_zatca",
    country_pack_version: "0.5.0",
    output_profile_id: "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
    status: "skeleton_only_milestone_1",
    files: [
      { filename: "invoice.xml", status: "pending_generation", sha256: null, storage_path: null },
      { filename: "canonical_invoice.json", status: "stored", sha256: "hash", storage_path: "canonical.json" },
      { filename: "validation_report.json", status: "stored", sha256: "hash", storage_path: "validation.json" }
    ],
    v1_boundary: "Saudi offline XML only."
  }
};

const ukPack: CountryPack = {
  country_pack_id: "uk_info",
  display_name: "United Kingdom / 2029 Peppol Roadmap",
  country_code: "GB",
  pack_version: "0.2.0",
  support_level: "info_only_roadmap",
  sandbox_test_available_when_configured: true,
  v1_boundary: "UK Peppol sandbox test only. This tests Peppol-style invoice readiness through a sandbox provider. It does not prove final UK 2029 statutory compliance.",
  v1_boundary_warning: "UK Peppol sandbox test only.",
  output_profiles: ["storecove_peppol_sandbox_readiness_test"],
  default_output_profile: "storecove_peppol_sandbox_readiness_test",
  requires_pdf: false,
  requires_qr: false,
  requires_signature: false,
  requires_live_submission_for_validity: false,
  live_submission_supported: false,
  live_clearance_supported: false,
  production_signing_supported: false,
  official_artefact_validation: "not_configured",
  legal_regime_summary: "UK mandatory e-invoicing is planned for 2029.",
  scope: ["UK roadmap."],
  mandatory_format: ["Peppol has been announced as the UK core interoperability network."],
  transmission_or_clearance_model: ["Decentralised Peppol-style model."],
  qr_signature_requirements: ["No QR configured."],
  retention_or_audit_notes: ["Sandbox-only evidence."],
  v1_app_capability: ["Sandbox readiness only when configured."],
  official_sources: [{ label: "Deferred scope", url: "docs/14_open_items_and_deferred_scope.md" }],
  regime_summary: "",
  legal_invoice_requirements: [],
  einvoice_requirements: [],
  source_status: [],
  boundary_highlights: ["UK Peppol sandbox test only."],
  last_reviewed: "2026-06-29"
};

const validUkUpload: UploadRecord = {
  upload_id: "UP-UK-VALID",
  original_filename: "UK-PEPPOL-SANDBOX-001.xlsx",
  selected_country_pack: "uk_info",
  selected_output_profile: "storecove_peppol_sandbox_readiness_test",
  workbook_sha256_hash: "hash",
  status: "validated",
  stored_workbook_path: "server/storage/uploads/UK-PEPPOL-SANDBOX-001.xlsx",
  canonical_json_path: "server/storage/canonical/UP-UK-VALID_canonical_invoice.json",
  validation_report_path: "server/storage/validation/UP-UK-VALID_validation_report.json",
  generated_xml_path: null,
  generated_xml_sha256_hash: null,
  canonical_invoice: {
    invoice: {
      invoice_number: "INV-UK-2029-001",
      invoice_date: "2026-06-26",
      invoice_currency_code: "GBP",
      selected_country_pack: "uk_info",
      selected_output_profile: "storecove_peppol_sandbox_readiness_test"
    },
    seller: { legal_name: "Demo UK Services Ltd", tax_registration_number: "GB123456789" },
    buyer: { legal_name: "Demo UK Buyer Ltd", tax_registration_number: "GB987654321" },
    lines: [{ line_number: 1, description: "Consulting services" }],
    tax_summary: [{ tax_category_code: "S", tax_rate: "20", taxable_amount: "1000.00", tax_amount: "200.00" }],
    totals: { net_total: 1000, tax_total: 200, gross_total: 1200 },
    source: {},
    metadata: {}
  },
  validation_report: {
    summary: {
      overall_status: "passed",
      internal_validation: "passed",
      official_artefact_validation: "not_configured",
      blocking_errors: 0,
      warnings_ack_required: 0,
      warnings: 0,
      passed_checks: 8
    },
    results: []
  },
  evidence_bundle_preview: {
    generation_id: "GEN-PREVIEW",
    country_pack_id: "uk_info",
    country_pack_version: "0.2.0",
    output_profile_id: "storecove_peppol_sandbox_readiness_test",
    status: "skeleton_only_milestone_1",
    files: [
      { filename: "canonical_invoice.json", status: "stored", sha256: "hash", storage_path: "canonical.json" },
      { filename: "validation_report.json", status: "stored", sha256: "hash", storage_path: "validation.json" },
      { filename: "storecove_request.json", status: "pending_sandbox_test", sha256: null, storage_path: null }
    ],
    v1_boundary: "UK Peppol sandbox test only."
  }
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
