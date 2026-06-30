import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuditTrailScreen } from "./AuditTrailScreen";

const auditEntry = {
  upload_id: "UP-AUDIT001",
  uploaded_at: "2026-06-30T10:00:00+00:00",
  generated_at: "2026-06-30T10:05:00+00:00",
  original_filename: "BE-VALID-001.xlsx",
  invoice_number: "INV-BE-2026-001",
  country_pack: "belgium_peppol",
  country_regime: "Belgium / Peppol BIS Billing 3.0",
  output_profile: "peppol_bis_billing_3_0_ubl_invoice",
  seller: "Demo Belgium Services BV",
  buyer: "Demo Belgium Buyer NV",
  currency: "EUR",
  gross_amount: "1210.00",
  validation_status: "passed",
  xml_generation_status: "generated",
  external_validation_status: "passed",
  sandbox_send_status: "failed",
  evidence_bundle_available: true,
  evidence_bundle_download_url: "/api/uploads/UP-AUDIT001/evidence-bundle/download",
  warnings: 0,
  pack_version: "0.6.0"
};

const auditDetail = {
  entry: auditEntry,
  source_upload_filename: "BE-VALID-001.xlsx",
  country_pack_version: "0.6.0",
  selected_output_profile: "peppol_bis_billing_3_0_ubl_invoice",
  invoice_summary: {
    invoice_number: "INV-BE-2026-001",
    seller: "Demo Belgium Services BV",
    buyer: "Demo Belgium Buyer NV",
    currency: "EUR",
    gross: "1210.00",
    line_count: 1
  },
  validation_summary: { overall_status: "passed", blocking_errors: 0 },
  generated_outputs_summary: [{ filename: "invoice.xml", status: "stored" }],
  xml_validation_summary: { overall_status: "passed" },
  official_validator_status: {
    status: "not_configured",
    en16931_validation_status: "not_configured",
    peppol_schematron_validation_status: "not_configured"
  },
  external_validation: { status: "passed", label: "External sandbox validation" },
  sandbox_send: { status: "failed", label: "External sandbox send", recipient_acceptance: "not_claimed" },
  saudi_outputs: { status: "not_applicable" },
  timestamps: { uploaded_at: "2026-06-30T10:00:00+00:00" },
  hashes: { workbook_sha256: "abc123" },
  evidence_metadata: { selected_country_pack: "belgium_peppol" },
  evidence_files: [
    {
      filename: "evidence_metadata.json",
      status: "available",
      sha256: null,
      content_type: "application/json",
      preview_available: true,
      download_url: "/api/audit/UP-AUDIT001/evidence-files/evidence_metadata.json/download",
      preview_url: "/api/audit/UP-AUDIT001/evidence-files/evidence_metadata.json/preview"
    },
    {
      filename: "source_upload_snapshot.xlsx",
      status: "stored",
      sha256: "def456",
      content_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      preview_available: false,
      download_url: "/api/audit/UP-AUDIT001/evidence-files/source_upload_snapshot.xlsx/download",
      preview_url: null
    }
  ],
  evidence_bundle_download_url: "/api/uploads/UP-AUDIT001/evidence-bundle/download"
};

describe("AuditTrailScreen", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string | URL | Request) => {
        const target = String(url);
        if (target.endsWith("/api/audit")) {
          return Promise.resolve(
            new Response(JSON.stringify([auditEntry]), {
              headers: { "Content-Type": "application/json" },
              status: 200
            })
          );
        }
        if (target.endsWith("/api/audit/UP-AUDIT001")) {
          return Promise.resolve(
            new Response(JSON.stringify(auditDetail), {
              headers: { "Content-Type": "application/json" },
              status: 200
            })
          );
        }
        if (target.endsWith("/api/audit/UP-AUDIT001/evidence-files/evidence_metadata.json/preview")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                filename: "evidence_metadata.json",
                content_type: "application/json",
                preview_available: true,
                kind: "json",
                content: {
                  selected_country_pack: "belgium_peppol",
                  official_xml_validator_status: { en16931_validation_status: "not_configured" }
                },
                message: null
              }),
              {
                headers: { "Content-Type": "application/json" },
                status: 200
              }
            )
          );
        }
        return Promise.resolve(new Response("{}", { status: 404 }));
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders audit list, selected detail and evidence bundle action", async () => {
    render(<AuditTrailScreen />);

    expect(await screen.findByText("INV-BE-2026-001")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Demo Belgium Services BV")).toBeInTheDocument();
    });
    expect(screen.getByText("Demo Belgium Buyer NV")).toBeInTheDocument();
    expect(screen.getAllByText("1,210.00 EUR").length).toBeGreaterThan(0);
    expect(screen.getByTitle("Download evidence bundle")).toHaveAttribute(
      "href",
      "http://localhost:8000/api/uploads/UP-AUDIT001/evidence-bundle/download"
    );
    expect(screen.getByText("evidence_metadata.json")).toBeInTheDocument();
    expect(screen.getByText("source_upload_snapshot.xlsx")).toBeInTheDocument();
  });

  it("previews JSON evidence files", async () => {
    render(<AuditTrailScreen />);

    await screen.findByText("evidence_metadata.json");
    fireEvent.click(screen.getAllByTitle("Preview file")[0]);

    await waitFor(() => {
      expect(screen.getByText(/official_xml_validator_status/)).toBeInTheDocument();
    });
  });
});
