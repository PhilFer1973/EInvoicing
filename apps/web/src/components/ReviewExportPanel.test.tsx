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
