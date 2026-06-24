import type { UploadRecord } from "../types";

interface InvoiceReviewCardProps {
  uploadRecord: UploadRecord | null;
}

export function InvoiceReviewCard({ uploadRecord }: InvoiceReviewCardProps) {
  const canonical = uploadRecord?.canonical_invoice;
  const invoice = canonical?.invoice ?? {};
  const seller = canonical?.seller ?? {};
  const buyer = canonical?.buyer ?? {};
  const totals = canonical?.totals ?? {};
  const lines = canonical?.lines ?? [];

  return (
    <section className="card stack" aria-labelledby="invoice-review-heading">
      <h2 id="invoice-review-heading">Invoice Review</h2>
      <div className="review-grid">
        <ReviewField label="Invoice number" value={invoice.invoice_number} />
        <ReviewField label="Date/time" value={[invoice.invoice_date, invoice.invoice_time].filter(Boolean).join(" ")} />
        <ReviewField label="Seller" value={seller.legal_name} />
        <ReviewField label="Buyer" value={buyer.legal_name} />
        <ReviewField label="Currency" value={invoice.invoice_currency_code} />
        <ReviewField label="Lines" value={lines.length ? String(lines.length) : undefined} />
      </div>
      <div className="totals-band">
        <ReviewField label="Net" value={totals.net_total} />
        <ReviewField label="Tax" value={totals.tax_total} />
        <ReviewField label="Gross" value={totals.gross_total} />
      </div>
      <div className="line-preview compact-lines">
        {lines.slice(0, 3).map((line, index) => (
          <article key={`${String(line.line_number ?? index)}`}>
            <strong>{String(line.description ?? "Line item")}</strong>
            <span>
              {String(line.quantity ?? "-")} {String(line.unit_code ?? "")} / {String(line.line_net_amount ?? "-")}
            </span>
          </article>
        ))}
        {!lines.length ? <p className="muted compact">Upload a workbook to populate the invoice review.</p> : null}
      </div>
    </section>
  );
}

function ReviewField({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="review-field">
      <span>{label}</span>
      <strong>{value === undefined || value === null || value === "" ? "Pending" : String(value)}</strong>
    </div>
  );
}
