import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { CountryPack } from "./types";

const packs: CountryPack[] = [
  {
    country_pack_id: "belgium_peppol",
    display_name: "Belgium / Peppol BIS Billing 3.0",
    country_code: "BE",
    pack_version: "0.6.0",
    support_level: "generator_basic",
    v1_boundary: "Not transmitted through Peppol. No access point or Mercurius submission.",
    v1_boundary_warning: "Not transmitted through Peppol.",
    output_profiles: ["peppol_bis_billing_3_0_ubl_invoice"],
    default_output_profile: "peppol_bis_billing_3_0_ubl_invoice",
    requires_pdf: false,
    requires_qr: false,
    requires_signature: false,
    requires_live_submission_for_validity: false,
    live_submission_supported: false,
    official_artefact_validation: "not_configured",
    legal_regime_summary: "Belgium B2B structured e-invoicing applies from 1 January 2026.",
    scope: ["Belgian B2B structured e-invoicing."],
    mandatory_format: ["EN 16931 and Peppol BIS Billing 3.0."],
    transmission_or_clearance_model: ["Peppol/access point delivery."],
    qr_signature_requirements: ["No QR requirement."],
    retention_or_audit_notes: ["Audit evidence required."],
    v1_app_capability: ["Milestone 1 scaffold."],
    official_sources: [{ label: "Belgium spec", url: "docs/06_belgium_peppol_pack_spec.md" }],
    regime_summary: "Belgium scaffold.",
    legal_invoice_requirements: ["Supplier and buyer VAT identifiers."],
    einvoice_requirements: ["Peppol-style UBL later."],
    source_status: ["Sources recorded."],
    boundary_highlights: ["Not transmitted through Peppol."],
    last_reviewed: "2026-06-24"
  },
  {
    country_pack_id: "saudi_zatca",
    display_name: "Saudi Arabia / ZATCA",
    country_code: "SA",
    pack_version: "0.3.0",
    support_level: "generator_basic",
    v1_boundary: "Not submitted to FATOORA. No ZATCA clearance stamp.",
    v1_boundary_warning: "This file has not been submitted to ZATCA/FATOORA and is not a cleared Saudi tax invoice.",
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
    scope: ["Phase One generation and Phase Two integration."],
    mandatory_format: ["XML or PDF/A-3 with embedded XML."],
    transmission_or_clearance_model: ["Standard B2B tax invoices follow clearance."],
    qr_signature_requirements: ["QR and production security features."],
    retention_or_audit_notes: ["Evidence retained."],
    v1_app_capability: ["Milestone 1 scaffold."],
    official_sources: [{ label: "ZATCA", url: "https://zatca.gov.sa/en/E-Invoicing/Pages/default.aspx" }],
    regime_summary: "Saudi scaffold.",
    legal_invoice_requirements: ["Invoice time required."],
    einvoice_requirements: ["PDF and QR later."],
    source_status: ["Sources recorded."],
    boundary_highlights: ["Not submitted to FATOORA.", "No ZATCA clearance stamp.", "Not a cleared Saudi tax invoice."],
    last_reviewed: "2026-06-24"
  },
  {
    country_pack_id: "uk_info",
    display_name: "United Kingdom / Information Only",
    country_code: "GB",
    pack_version: "0.1.0",
    support_level: "info_only",
    v1_boundary: "Information-only placeholder.",
    v1_boundary_warning: "Information only.",
    output_profiles: [],
    default_output_profile: null,
    requires_pdf: false,
    requires_qr: false,
    requires_signature: false,
    requires_live_submission_for_validity: false,
    live_submission_supported: false,
    official_artefact_validation: "not_configured",
    legal_regime_summary: "UK info-only pack.",
    scope: ["No UK V1 generation."],
    mandatory_format: ["No UK format configured."],
    transmission_or_clearance_model: ["No UK workflow configured."],
    qr_signature_requirements: ["No QR configured."],
    retention_or_audit_notes: ["Pack selection only."],
    v1_app_capability: ["Information panel only."],
    official_sources: [{ label: "Deferred scope", url: "docs/14_open_items_and_deferred_scope.md" }],
    regime_summary: "UK info scaffold.",
    legal_invoice_requirements: ["No generation."],
    einvoice_requirements: ["Generation disabled."],
    source_status: ["No artefacts configured."],
    boundary_highlights: ["Information only."],
    last_reviewed: "2026-06-24"
  }
];

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string | URL | Request) => {
        const target = String(url);
        if (target.endsWith("/api/country-packs")) {
          return Promise.resolve(
            new Response(JSON.stringify({ country_packs: packs }), {
              headers: { "Content-Type": "application/json" },
              status: 200
            })
          );
        }
        if (target.endsWith("/api/audit")) {
          return Promise.resolve(
            new Response(JSON.stringify([]), {
              headers: { "Content-Type": "application/json" },
              status: 200
            })
          );
        }
        return Promise.resolve(new Response("{}", { status: 404 }));
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the required top navigation and country selector", async () => {
    const { container } = render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText("Belgium / Peppol BIS Billing 3.0").length).toBeGreaterThan(0);
    });

    expect(screen.getByText("Global E-Invoice Generation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "E-Invoicing" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Audit Trail" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Export Template/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Settings/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Help/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Saudi Arabia / ZATCA" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "United Kingdom / Information Only" })).toBeInTheDocument();
    expect(container.querySelector("aside")).not.toBeInTheDocument();
    expect(container.querySelector(".chart")).not.toBeInTheDocument();
  });
});
