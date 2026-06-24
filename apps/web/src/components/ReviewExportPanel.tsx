import { Archive, Sparkles } from "lucide-react";

import type { CountryPack, UploadRecord } from "../types";

interface ReviewExportPanelProps {
  pack: CountryPack | null;
  uploadRecord: UploadRecord | null;
}

export function ReviewExportPanel({ pack, uploadRecord }: ReviewExportPanelProps) {
  const canonical = uploadRecord?.canonical_invoice;
  const invoice = canonical?.invoice ?? {};
  const seller = canonical?.seller ?? {};
  const buyer = canonical?.buyer ?? {};
  const totals = canonical?.totals ?? {};
  const lines = canonical?.lines ?? [];
  const isInfoOnly = pack?.support_level === "info_only";

  return (
    <section className="card stack review-export-card" aria-labelledby="review-export-heading">
      <div className="panel-title-row">
        <span className="panel-number">03</span>
        <h2 id="review-export-heading">Invoice Review / Export</h2>
      </div>
      <div className="review-grid">
        <ReviewField label="Invoice number" value={invoice.invoice_number} />
        <ReviewField label="Invoice date" value={invoice.invoice_date} />
        <ReviewField label="Currency" value={invoice.invoice_currency_code} />
        <ReviewField className="review-field-full" label="Seller" value={seller.legal_name} />
        <ReviewField className="review-field-full" label="Buyer" value={buyer.legal_name} />
        <ReviewField label="Net" value={totals.net_total} />
        <ReviewField label="Tax" value={totals.tax_total} />
        <ReviewField label="Gross" value={totals.gross_total} />
      </div>
      <div className="invoice-lines-listbox" role="listbox" aria-label="Invoice lines">
        <div className="listbox-heading">
          <span>Invoice lines</span>
          <strong>{lines.length || 0}</strong>
        </div>
        {lines.length ? (
          lines.map((line, index) => (
            <div className="invoice-line-option" key={`${String(line.line_number ?? index)}`} role="option" aria-selected="false">
              <span>{String(line.line_number ?? index + 1).padStart(2, "0")}</span>
              <strong>{String(line.description ?? line.item_name ?? "Line item")}</strong>
              <small>
                {String(line.quantity ?? "-")} {String(line.unit_code ?? "")} / {String(line.line_net_amount ?? "-")}
              </small>
            </div>
          ))
        ) : (
          <p className="muted compact">Upload a workbook to populate invoice lines.</p>
        )}
      </div>
      <div className="export-bottom-actions">
        <div className="output-choice-pill">
          <Archive aria-hidden="true" size={16} />
          <span>Generate ZIP bundle</span>
        </div>
        <button className="button-primary generate-button" disabled={isInfoOnly} type="button">
          <Sparkles aria-hidden="true" size={17} />
          Generate
        </button>
      </div>
    </section>
  );
}

function ReviewField({ className = "", label, value }: { className?: string; label: string; value: unknown }) {
  return (
    <div className={`review-field ${className}`.trim()}>
      <span>{label}</span>
      <strong>{value === undefined || value === null || value === "" ? "Pending" : String(value)}</strong>
    </div>
  );
}
