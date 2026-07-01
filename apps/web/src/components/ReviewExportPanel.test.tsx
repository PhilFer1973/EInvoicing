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

  it("does not show a Saudi boundary acknowledgement label in the right panel", () => {
    render(<ReviewExportPanel pack={saudiPack} uploadRecord={validSaudiUpload} onUploadRecordChange={vi.fn()} />);

    expect(screen.queryByText(/Acknowledge:/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export ZIP" })).toBeInTheDocument();
  });

  it("shows country-specific Saudi validation details without Belgium XML layers", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(validSaudiUpload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<ReviewExportPanel pack={saudiPack} uploadRecord={validSaudiUpload} onUploadRecordChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Validation Details" })).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Internal validation" })).toBeInTheDocument();
    expect(screen.queryByText("SA-V1-BOUNDARY-001")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "XML well-formedness" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Peppol readiness checks" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "External sandbox validation" })).not.toBeInTheDocument();

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

  it("generates UK Peppol readiness XML through the normal Generate action", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ...validUkUpload.evidence_bundle_preview,
          status: "uk_peppol_readiness_xml_generated_milestone_8a",
          files: [
            { filename: "invoice.xml", status: "stored", sha256: "uk-xml-hash", storage_path: "generated/UP-UK-VALID_uk_peppol_readiness_invoice.xml" },
            { filename: "xml_validation_report.json", status: "stored", sha256: "xml-validation-hash", storage_path: "generated/UP-UK-VALID_xml_validation_report.json" }
          ]
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);
    const onUploadRecordChange = vi.fn();

    render(<ReviewExportPanel pack={ukPack} uploadRecord={validUkUpload} onUploadRecordChange={onUploadRecordChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/uploads/UP-UK-VALID/generate", { method: "POST" })
    );
    expect(await screen.findByRole("heading", { name: "Generated Outputs" })).toBeInTheDocument();
    expect(screen.getByText(/UK Peppol readiness XML only/)).toBeInTheDocument();
    expect(onUploadRecordChange).toHaveBeenCalledWith(expect.objectContaining({ generated_xml_path: "generated/UP-UK-VALID_uk_peppol_readiness_invoice.xml" }));

    vi.unstubAllGlobals();
  });

  it("shows UK readiness notices separately from failed validation errors", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify(validUkUpload), { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ReviewExportPanel pack={ukPack} uploadRecord={validUkUpload} onUploadRecordChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    expect(await screen.findByRole("heading", { name: "UK readiness boundaries" })).toBeInTheDocument();
    expect(screen.getByText("These notices explain the limits of the UK readiness XML. They are not blocking workbook errors.")).toBeInTheDocument();
    expect(screen.getByText("Readiness notice")).toBeInTheDocument();
    expect(screen.queryByText("failed")).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("uses one Validate button and shows e-invoice.be as not configured through the main validation pipeline", async () => {
    const updatedUpload: UploadRecord = {
      ...validBelgiumUpload,
      generated_xml_path: "server/storage/generated/UP-BE-VALID_belgium_peppol_invoice.xml",
      generated_xml_sha256_hash: "xml-hash",
      xml_validation_report_path: "server/storage/generated/UP-BE-VALID_xml_validation_report.json",
      xml_validation_report: validBelgiumXmlValidationReport,
      external_validation: {
        provider: "e-invoice.be",
        label: "External sandbox validation",
        status: "not_configured",
        is_valid: null,
        reference: null,
        validated_at: "2026-06-29T12:00:00+00:00",
        issue_count: 0,
        messages: ["External e-invoice.be sandbox validation not configured."],
        endpoint: "https://api.e-invoice.be/api/validate/ubl",
        peppol_delivery: "not_delivered",
        recipient_acceptance: "not_requested",
        smp_registration_claim: "not_claimed",
        disclaimer: "External sandbox validation only. This does not prove Peppol delivery or final statutory compliance."
      }
    };
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(updatedUpload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    function StatefulPanel() {
      const [record, setRecord] = useState(validBelgiumUpload);
      return <ReviewExportPanel pack={belgiumPack} uploadRecord={record} onUploadRecordChange={setRecord} />;
    }

    render(<StatefulPanel />);

    expect(screen.getAllByRole("button", { name: "Validate" })).toHaveLength(1);
    expect(screen.queryByText("Validate with e-invoice.be sandbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Validation Details" })).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Generated Outputs" })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/uploads/UP-BE-VALID/validate-pipeline",
      { method: "POST" }
    );
    expect(screen.getByRole("heading", { name: "Internal validation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "XML generation for validation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "XML well-formedness" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "UBL structure checks" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Peppol readiness checks" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "UBL XSD validation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "EN16931 validation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Peppol Schematron validation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "External sandbox validation" })).toBeInTheDocument();
    expect(screen.getByText("Belgium XML was generated from canonical invoice JSON for validation/output evidence.")).toBeInTheDocument();
    expect(screen.getByText("Generated XML is well-formed.")).toBeInTheDocument();
    expect(screen.getByText("Basic UBL invoice structure checks passed.")).toBeInTheDocument();
    expect(screen.getByText("Peppol readiness checks passed.")).toBeInTheDocument();
    expect(screen.getAllByText("Official validator artefact not configured.")).toHaveLength(3);
    expect(screen.getByText("generated")).toBeInTheDocument();
    expect(screen.getAllByText("External e-invoice.be sandbox validation not configured.").length).toBeGreaterThan(0);
    expect(screen.queryByText("Belgium XML generation for validation has not run.")).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows XML and external validation as skipped when internal blocking errors remain", async () => {
    const blockedUpload: UploadRecord = {
      ...validBelgiumUpload,
      generated_xml_path: null,
      validation_report: {
        ...validBelgiumUpload.validation_report,
        summary: {
          ...validBelgiumUpload.validation_report.summary,
          blocking_errors: 1,
          overall_status: "failed"
        },
        results: [
          {
            rule_id: "BE-INV-001",
            layer: "country_validation",
            severity: "error",
            status: "failed",
            message: "Invoice number is required.",
            field_path: "invoice.invoice_number",
            country_pack_id: "belgium_peppol",
            country_pack_version: "0.6.0",
            corrective_action: "Add an invoice number.",
            technical_detail: null
          }
        ]
      },
      external_validation: {
        provider: "e-invoice.be",
        label: "External sandbox validation",
        status: "skipped",
        is_valid: null,
        reference: null,
        validated_at: "2026-06-29T12:00:00+00:00",
        issue_count: 0,
        messages: ["External e-invoice.be sandbox validation skipped because internal validation has blocking errors."],
        endpoint: "https://api.e-invoice.be/api/validate/ubl",
        peppol_delivery: "not_delivered",
        recipient_acceptance: "not_requested",
        smp_registration_claim: "not_claimed",
        disclaimer: "External sandbox validation only. This does not prove Peppol delivery or final statutory compliance."
      }
    };
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(blockedUpload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    function StatefulPanel() {
      const [record, setRecord] = useState(validBelgiumUpload);
      return <ReviewExportPanel pack={belgiumPack} uploadRecord={record} onUploadRecordChange={setRecord} />;
    }

    render(<StatefulPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Validation Details" })).toBeInTheDocument());
    expect(screen.getByText("Skipped due to blocking validation errors")).toBeInTheDocument();
    expect(screen.getByText("External sandbox validation skipped")).toBeInTheDocument();
    expect(screen.getByText("External e-invoice.be sandbox validation skipped because internal validation has blocking errors.")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("shows external sandbox validation failure separately from internal validation failure", async () => {
    const updatedUpload: UploadRecord = {
      ...validBelgiumUpload,
      generated_xml_path: "server/storage/generated/UP-BE-VALID_belgium_peppol_invoice.xml",
      generated_xml_sha256_hash: "xml-hash",
      external_validation: {
        provider: "e-invoice.be",
        label: "External sandbox validation",
        status: "failed",
        is_valid: false,
        reference: "EINVBE-VAL-FAILED",
        validated_at: "2026-06-29T12:00:00+00:00",
        issue_count: 2,
        messages: [
          "Belgian enterprise number MUST be stated in the correct format.",
          "Belgian enterprise number MUST be stated in the correct format."
        ],
        endpoint: "https://api.e-invoice.be/api/validate/ubl",
        peppol_delivery: "not_delivered",
        recipient_acceptance: "not_requested",
        smp_registration_claim: "not_claimed",
        disclaimer: "External sandbox validation only. This does not prove Peppol delivery or final statutory compliance."
      },
      evidence_bundle_preview: {
        ...validBelgiumUpload.evidence_bundle_preview,
        status: "belgium_xml_generated_einvoicebe_validated_milestone_5b",
        files: [
          ...validBelgiumUpload.evidence_bundle_preview.files,
          { filename: "invoice.xml", status: "stored", sha256: "xml-hash", storage_path: "generated/invoice.xml" },
          { filename: "einvoicebe_validation_request.json", status: "stored", sha256: "request-hash", storage_path: "generated/request.json" },
          { filename: "einvoicebe_validation_response.json", status: "stored", sha256: "response-hash", storage_path: "generated/response.json" },
          { filename: "external_validation_status.json", status: "stored", sha256: "status-hash", storage_path: "generated/status.json" }
        ]
      }
    };
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(updatedUpload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    function StatefulPanel() {
      const [record, setRecord] = useState(validBelgiumUpload);
      return <ReviewExportPanel pack={belgiumPack} uploadRecord={record} onUploadRecordChange={setRecord} />;
    }

    render(<StatefulPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Validate" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Validation Details" })).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/uploads/UP-BE-VALID/validate-pipeline",
      { method: "POST" }
    );
    expect(screen.getByText("External sandbox validation failed")).toBeInTheDocument();
    expect(screen.getAllByText("Belgian enterprise number MUST be stated in the correct format.")).toHaveLength(1);
    expect(screen.queryByText("Internal validation failed")).not.toBeInTheDocument();
    expect(screen.getByText("External sandbox validation only. This does not prove Peppol delivery or final statutory compliance.")).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it("does not show a separate e-invoice.be sandbox send button in the Belgium action panel", () => {
    const validatedUpload: UploadRecord = {
      ...validBelgiumUpload,
      generated_xml_path: "server/storage/generated/UP-BE-VALID_belgium_peppol_invoice.xml",
      generated_xml_sha256_hash: "xml-hash",
      canonical_invoice: {
        ...validBelgiumUpload.canonical_invoice!,
        seller: {
          ...validBelgiumUpload.canonical_invoice!.seller,
          tax_registration_number: "BE0990251719",
          enterprise_number: "0990251719",
          legal_registration_number: "0990251719",
          peppol_id: "0208:099025170",
          einvoicebe_sender_peppol_id: "0208:099025170"
        }
      },
      external_validation: {
        provider: "e-invoice.be",
        label: "External sandbox validation",
        status: "passed",
        is_valid: true,
        reference: "EINVBE-VALID-001",
        validated_at: "2026-06-29T12:00:00+00:00",
        issue_count: 0,
        messages: [],
        endpoint: "https://api.e-invoice.be/api/validate/ubl",
        peppol_delivery: "not_delivered",
        recipient_acceptance: "not_requested",
        smp_registration_claim: "not_claimed",
        disclaimer: "External sandbox validation only. This does not prove Peppol delivery or final statutory compliance."
      },
      evidence_bundle_preview: {
        ...validBelgiumUpload.evidence_bundle_preview,
        files: [
          ...validBelgiumUpload.evidence_bundle_preview.files,
          { filename: "invoice.xml", status: "stored", sha256: "xml-hash", storage_path: "generated/invoice.xml" }
        ]
      }
    };

    render(<ReviewExportPanel pack={belgiumPack} uploadRecord={validatedUpload} onUploadRecordChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Validate" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Generate" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "Export ZIP" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send to e-invoice.be sandbox" })).not.toBeInTheDocument();
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
  pack_version: "0.3.0",
  support_level: "generator_readiness",
  sandbox_test_available_when_configured: true,
  v1_boundary: "UK Peppol readiness XML only. Generated using Peppol BIS / EN16931-style structure based on currently announced UK Peppol direction. This does not prove final UK 2029 statutory compliance.",
  v1_boundary_warning: "UK Peppol readiness XML only.",
  output_profiles: ["uk_peppol_readiness_ubl"],
  default_output_profile: "uk_peppol_readiness_ubl",
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
  v1_app_capability: ["Readiness XML only."],
  official_sources: [{ label: "Deferred scope", url: "docs/14_open_items_and_deferred_scope.md" }],
  regime_summary: "",
  legal_invoice_requirements: [],
  einvoice_requirements: [],
  source_status: [],
  boundary_highlights: ["UK Peppol readiness XML only."],
  last_reviewed: "2026-06-30"
};

const validUkUpload: UploadRecord = {
  upload_id: "UP-UK-VALID",
  original_filename: "UK-PEPPOL-SANDBOX-001.xlsx",
  selected_country_pack: "uk_info",
  selected_output_profile: "uk_peppol_readiness_ubl",
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
      selected_output_profile: "uk_peppol_readiness_ubl"
    },
    seller: { legal_name: "Demo UK Services Ltd", tax_registration_number: "GB123456789", peppol_id: "9932:GB123456789", peppol_scheme_id: "9932" },
    buyer: { legal_name: "Demo UK Buyer Ltd", tax_registration_number: "GB987654321", peppol_id: "9932:GB987654321", peppol_scheme_id: "9932" },
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
    results: [
      {
        rule_id: "UK-READINESS-001",
        layer: "country_preflight",
        severity: "warning",
        status: "passed",
        message: "Final UK 2029 technical standard is not yet published/configured in this app.",
        field_path: "country_pack.uk_standard_status",
        country_pack_id: "uk_info",
        country_pack_version: "0.3.0",
        corrective_action: "Treat this as a readiness boundary, not as a blocking workbook error.",
        technical_detail: null
      }
    ]
  },
  evidence_bundle_preview: {
    generation_id: "GEN-PREVIEW",
    country_pack_id: "uk_info",
    country_pack_version: "0.3.0",
    output_profile_id: "uk_peppol_readiness_ubl",
    status: "skeleton_only_milestone_1",
    files: [
      { filename: "canonical_invoice.json", status: "stored", sha256: "hash", storage_path: "canonical.json" },
      { filename: "invoice.xml", status: "pending_generation", sha256: null, storage_path: null },
      { filename: "validation_report.json", status: "stored", sha256: "hash", storage_path: "validation.json" },
      { filename: "xml_validation_report.json", status: "pending_xml_validation", sha256: null, storage_path: null }
    ],
    v1_boundary: "UK Peppol readiness XML only."
  }
};

const belgiumPack: CountryPack = {
  country_pack_id: "belgium_peppol",
  display_name: "Belgium / Peppol BIS Billing 3.0",
  country_code: "BE",
  pack_version: "0.4.0",
  support_level: "ubl_xml_generation",
  v1_boundary: "Belgium generated XML only. No Peppol transmission.",
  v1_boundary_warning: "Generated only.",
  output_profiles: ["peppol_bis_billing_3_0_ubl_invoice"],
  default_output_profile: "peppol_bis_billing_3_0_ubl_invoice",
  requires_pdf: false,
  requires_qr: false,
  requires_signature: false,
  requires_live_submission_for_validity: false,
  live_submission_supported: false,
  live_clearance_supported: false,
  production_signing_supported: false,
  official_artefact_validation: "not_configured",
  legal_regime_summary: "Belgium B2B structured e-invoicing requirement.",
  scope: ["Belgium domestic B2B services."],
  mandatory_format: ["EN 16931 / Peppol BIS Billing 3.0."],
  transmission_or_clearance_model: ["Peppol or agreed structured alternative."],
  qr_signature_requirements: ["No QR requirement."],
  retention_or_audit_notes: ["Retain evidence."],
  v1_app_capability: ["Generated XML only."],
  official_sources: [{ label: "Belgium e-invoicing", url: "https://finances.belgium.be" }],
  regime_summary: "",
  legal_invoice_requirements: [],
  einvoice_requirements: [],
  source_status: [],
  boundary_highlights: [],
  last_reviewed: "2026-06-29"
};

const validBelgiumUpload: UploadRecord = {
  upload_id: "UP-BE-VALID",
  original_filename: "BE-VALID-001.xlsx",
  selected_country_pack: "belgium_peppol",
  selected_output_profile: "peppol_bis_billing_3_0_ubl_invoice",
  workbook_sha256_hash: "hash",
  status: "validated",
  stored_workbook_path: "server/storage/uploads/BE-VALID-001.xlsx",
  canonical_json_path: "server/storage/canonical/UP-BE-VALID_canonical_invoice.json",
  validation_report_path: "server/storage/validation/UP-BE-VALID_validation_report.json",
  generated_xml_path: null,
  generated_xml_sha256_hash: null,
  generated_at: null,
  canonical_invoice: {
    invoice: {
      invoice_number: "INV-BE-2026-001",
      invoice_date: "2026-06-24",
      invoice_currency_code: "EUR",
      selected_country_pack: "belgium_peppol",
      selected_output_profile: "peppol_bis_billing_3_0_ubl_invoice"
    },
    seller: {
      legal_name: "Demo Belgium Services BV",
      tax_registration_number: "BE0990251719",
      enterprise_number: "0990251719",
      legal_registration_number: "0990251719",
      peppol_id: "0208:0990251719"
    },
    buyer: {
      legal_name: "Demo Belgium Buyer NV",
      tax_registration_number: "BE0987654394",
      enterprise_number: "0987654394",
      legal_registration_number: "0987654394",
      peppol_id: "0208:0987654394"
    },
    lines: [{ line_number: 1, description: "Consulting services" }],
    tax_summary: [{ tax_category_code: "S", tax_rate: "21", taxable_amount: "1000.00", tax_amount: "210.00" }],
    totals: { net_total: 1000, tax_total: 210, gross_total: 1210 },
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
    country_pack_id: "belgium_peppol",
    country_pack_version: "0.4.0",
    output_profile_id: "peppol_bis_billing_3_0_ubl_invoice",
    status: "skeleton_only_milestone_1",
    files: [
      { filename: "invoice.xml", status: "pending_generation", sha256: null, storage_path: null },
      { filename: "canonical_invoice.json", status: "stored", sha256: "hash", storage_path: "canonical.json" },
      { filename: "validation_report.json", status: "stored", sha256: "hash", storage_path: "validation.json" },
      { filename: "einvoicebe_validation_request.json", status: "pending_external_validation", sha256: null, storage_path: null },
      { filename: "einvoicebe_validation_response.json", status: "pending_external_validation", sha256: null, storage_path: null },
      { filename: "external_validation_status.json", status: "pending_external_validation", sha256: null, storage_path: null }
    ],
    v1_boundary: "Belgium generated XML only."
  }
};

const validBelgiumXmlValidationReport = {
  overall_status: "passed",
  executed_at: "2026-06-30T12:00:00+00:00",
  results: [
    {
      validator_name: "XML well-formedness",
      validator_type: "xml_well_formedness",
      status: "passed",
      errors: [],
      warnings: [],
      informational_messages: ["Generated XML is well-formed."],
      executed_at: "2026-06-30T12:00:00+00:00",
      artefact_version: "Python xml.etree.ElementTree",
      raw_output_path: null,
      metadata: {}
    },
    {
      validator_name: "Basic UBL invoice structure checks",
      validator_type: "ubl_structure",
      status: "passed",
      errors: [],
      warnings: [],
      informational_messages: ["Basic UBL invoice structure checks passed."],
      executed_at: "2026-06-30T12:00:00+00:00",
      artefact_version: "Milestone 6A local readiness checks",
      raw_output_path: null,
      metadata: {}
    },
    {
      validator_name: "Peppol readiness checks",
      validator_type: "peppol_readiness",
      status: "passed",
      errors: [],
      warnings: [],
      informational_messages: ["Peppol readiness checks passed."],
      executed_at: "2026-06-30T12:00:00+00:00",
      artefact_version: "Milestone 6A local readiness checks",
      raw_output_path: null,
      metadata: {}
    },
    {
      validator_name: "UBL XSD validation",
      validator_type: "ubl_xsd",
      status: "not_configured",
      errors: [],
      warnings: [],
      informational_messages: ["Official validator artefact not configured."],
      executed_at: "2026-06-30T12:00:00+00:00",
      artefact_version: null,
      artefact_path: null,
      validator_executed: false,
      raw_output_path: null,
      metadata: {}
    },
    {
      validator_name: "EN16931 validation",
      validator_type: "en16931",
      status: "not_configured",
      errors: [],
      warnings: [],
      informational_messages: ["Official validator artefact not configured."],
      executed_at: "2026-06-30T12:00:00+00:00",
      artefact_version: null,
      artefact_path: null,
      validator_executed: false,
      raw_output_path: null,
      metadata: {}
    },
    {
      validator_name: "Peppol Schematron validation",
      validator_type: "peppol_schematron",
      status: "not_configured",
      errors: [],
      warnings: [],
      informational_messages: ["Official validator artefact not configured."],
      executed_at: "2026-06-30T12:00:00+00:00",
      artefact_version: null,
      artefact_path: null,
      validator_executed: false,
      raw_output_path: null,
      metadata: {}
    }
  ]
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
