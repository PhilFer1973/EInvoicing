import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UploadWorkbookCard } from "./UploadWorkbookCard";

describe("UploadWorkbookCard", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a specific wrong-regime diagnostic for a selected-regime mismatch", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify(mismatchUploadResponse), {
            headers: { "Content-Type": "application/json" },
            status: 200
          })
        )
      )
    );
    const onUploadComplete = vi.fn();
    const { container, rerender } = render(<UploadWorkbookCard selectedPackId="saudi_zatca" onUploadComplete={onUploadComplete} />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: {
        files: [new File(["workbook"], "BE-VALID-001.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" })]
      }
    });

    await waitFor(() => {
      expect(screen.getByText("Wrong regime selected")).toBeInTheDocument();
    });
    expect(onUploadComplete).toHaveBeenCalledWith(expect.objectContaining({ status: "validation_failed" }));

    rerender(<UploadWorkbookCard selectedPackId="belgium_peppol" onUploadComplete={onUploadComplete} />);

    await waitFor(() => {
      expect(screen.getByText("No workbook uploaded")).toBeInTheDocument();
    });
    expect(screen.queryByText("Wrong regime selected")).not.toBeInTheDocument();
  });
});

const mismatchUploadResponse = {
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
  canonical_invoice: null,
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
    files: [],
    v1_boundary: "Saudi validation foundation only."
  }
};
