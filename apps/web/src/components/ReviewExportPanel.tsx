import { Archive, ListChecks, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

import {
  canonicalInvoiceDownloadUrl,
  canonicalInvoiceUrl,
  evidenceBundleDownloadUrl,
  fetchGeneratedXml,
  generateOutput,
  generatedXmlDownloadUrl,
  generatedXmlUrl,
  validateUpload
} from "../services/api";
import type { CountryPack, UploadRecord, ValidationReport } from "../types";

interface ReviewExportPanelProps {
  pack: CountryPack | null;
  uploadRecord: UploadRecord | null;
  onUploadRecordChange?: (record: UploadRecord) => void;
}

type DetailView = "validation" | "canonical" | "lines" | "xml" | null;

export function ReviewExportPanel({ pack, uploadRecord, onUploadRecordChange }: ReviewExportPanelProps) {
  const hasRegimeMismatch = Boolean(
    uploadRecord?.validation_report.results.some((result) => result.rule_id === "WB-REGIME-001" && result.status === "failed")
  );
  const canonical = hasRegimeMismatch ? null : uploadRecord?.canonical_invoice;
  const invoice = canonical?.invoice ?? {};
  const seller = canonical?.seller ?? {};
  const buyer = canonical?.buyer ?? {};
  const totals = canonical?.totals ?? {};
  const lines = canonical?.lines ?? [];
  const [detailView, setDetailView] = useState<DetailView>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(uploadRecord?.validation_report ?? null);
  const [isValidating, setIsValidating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedXml, setGeneratedXml] = useState("");
  const [generationError, setGenerationError] = useState("");
  const canExportZip = Boolean(uploadRecord?.evidence_bundle_preview.files.length) && !hasRegimeMismatch;
  const canGenerate =
    pack?.country_pack_id === "belgium_peppol" &&
    Boolean(uploadRecord?.canonical_invoice) &&
    (validationReport?.summary.blocking_errors ?? 1) === 0;
  const generateTitle =
    pack?.country_pack_id === "saudi_zatca"
      ? "Saudi XML, QR and PDF generation are not implemented in Milestone 3A."
      : canGenerate
        ? "Generate Belgium Peppol-style UBL XML."
        : "Resolve blocking validation errors before generation.";

  useEffect(() => {
    setValidationReport(uploadRecord?.validation_report ?? null);
    setDetailView(null);
    setGeneratedXml("");
    setGenerationError("");
  }, [uploadRecord?.upload_id]);

  async function handleValidate() {
    if (!uploadRecord) return;
    setIsValidating(true);
    try {
      const report = await validateUpload(uploadRecord.upload_id);
      setValidationReport(report);
      onUploadRecordChange?.({ ...uploadRecord, validation_report: report });
      setDetailView("validation");
    } catch {
      setDetailView("validation");
    } finally {
      setIsValidating(false);
    }
  }

  async function handleGenerate() {
    if (!uploadRecord || !canGenerate) return;
    setIsGenerating(true);
    setGenerationError("");
    try {
      const evidence = await generateOutput(uploadRecord.upload_id);
      const xmlFile = evidence.files.find((file) => file.filename === "invoice.xml");
      onUploadRecordChange?.({
        ...uploadRecord,
        status: "generated",
        evidence_bundle_preview: evidence,
        generated_xml_path: xmlFile?.storage_path ?? uploadRecord.generated_xml_path,
        generated_xml_sha256_hash: xmlFile?.sha256 ?? uploadRecord.generated_xml_sha256_hash
      });
      setGeneratedXml(await fetchGeneratedXml(uploadRecord.upload_id));
      setDetailView("xml");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "XML generation failed");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <section className="card stack review-export-card" aria-labelledby="review-export-heading">
      <div className="panel-title-row">
        <span className="panel-number">03</span>
        <h2 id="review-export-heading">Invoice Review / Export</h2>
      </div>

      {hasRegimeMismatch ? (
        <div className="no-valid-invoice-state">
          <strong>No valid invoice loaded</strong>
          <span>Open validation details to review the workbook mismatch.</span>
        </div>
      ) : (
        <div className="review-grid invoice-summary-grid">
          <ReviewField className="invoice-number-field" label="Invoice number" value={invoice.invoice_number} />
          <ReviewField className="invoice-date-field" label="Invoice date" value={invoice.invoice_date} />
          <ReviewField className="currency-field" label="Currency" value={invoice.invoice_currency_code} />
          <ReviewField className="review-field-full" label="Seller" value={seller.legal_name} />
          <ReviewField className="review-field-full" label="Buyer" value={buyer.legal_name} />
          <ReviewField className="total-field" label="Net" value={totals.net_total} variant="money" />
          <ReviewField className="total-field" label="Tax" value={totals.tax_total} variant="money" />
          <ReviewField className="total-field" label="Gross" value={totals.gross_total} variant="money" />
        </div>
      )}

      <div className="right-panel-spacer" aria-hidden="true" />

      <div className="action-panel">
        <button className="button-secondary action-button" disabled={!uploadRecord || isValidating} onClick={() => void handleValidate()} type="button">
          <ListChecks aria-hidden="true" size={17} />
          {isValidating ? "Validating" : "Validate"}
        </button>
        <button
          className="button-secondary action-button"
          disabled={!canGenerate || isGenerating}
          onClick={() => void handleGenerate()}
          title={generateTitle}
          type="button"
        >
          <Sparkles aria-hidden="true" size={17} />
          {isGenerating ? "Generating" : "Generate"}
        </button>
        {generationError ? <p className="action-error">{generationError}</p> : null}
        {uploadRecord && canExportZip ? (
          <a className="button-primary action-button export-zip-button" href={evidenceBundleDownloadUrl(uploadRecord.upload_id)}>
            <Archive aria-hidden="true" size={17} />
            Export ZIP
          </a>
        ) : (
          <button className="button-primary action-button export-zip-button" disabled type="button">
            <Archive aria-hidden="true" size={17} />
            Export ZIP
          </button>
        )}
      </div>

      {detailView ? (
        <DetailModal
          detailView={detailView}
          lines={lines}
          onClose={() => setDetailView(null)}
          uploadRecord={uploadRecord}
          validationReport={validationReport}
          xml={generatedXml}
        />
      ) : null}
    </section>
  );
}

function DetailModal({
  detailView,
  lines,
  onClose,
  uploadRecord,
  validationReport,
  xml
}: {
  detailView: Exclude<DetailView, null>;
  lines: Array<Record<string, unknown>>;
  onClose: () => void;
  uploadRecord: UploadRecord | null;
  validationReport: ValidationReport | null;
  xml: string;
}) {
  const title =
    detailView === "validation"
      ? "Validation Details"
      : detailView === "canonical"
        ? "Canonical JSON"
        : detailView === "xml"
          ? "Generated XML"
          : "Invoice Lines";

  return (
    <div className="modal-backdrop" onMouseDown={onClose} role="presentation">
      <section aria-labelledby="detail-modal-heading" aria-modal="true" className="detail-modal" onMouseDown={(event) => event.stopPropagation()} role="dialog">
        <div className="modal-title-row">
          <h3 id="detail-modal-heading">{title}</h3>
          <button aria-label="Close details" className="icon-button" onClick={onClose} type="button">
            <X aria-hidden="true" size={18} />
          </button>
        </div>
        {detailView === "validation" ? <ValidationDetails report={validationReport} uploadRecord={uploadRecord} /> : null}
        {detailView === "canonical" ? <CanonicalDetails uploadRecord={uploadRecord} /> : null}
        {detailView === "lines" ? <InvoiceLineDetails lines={lines} /> : null}
        {detailView === "xml" ? <XmlDetails uploadRecord={uploadRecord} xml={xml} /> : null}
      </section>
    </div>
  );
}

function XmlDetails({ uploadRecord, xml }: { uploadRecord: UploadRecord | null; xml: string }) {
  if (!uploadRecord) {
    return <p className="muted compact">Generated XML is available after successful Belgium generation.</p>;
  }
  if (!uploadRecord?.generated_xml_path && !xml) {
    return <p className="muted compact">Generated XML is available after successful Belgium generation.</p>;
  }

  return (
    <div className="modal-stack">
      <div className="modal-link-row">
        <a href={generatedXmlUrl(uploadRecord.upload_id)} target="_blank" rel="noreferrer">Open XML</a>
        <a href={generatedXmlDownloadUrl(uploadRecord.upload_id)}>Download XML</a>
      </div>
      <pre className="json-preview">{xml || "Generated XML is stored and available from the links above."}</pre>
    </div>
  );
}

function ValidationDetails({ report, uploadRecord }: { report: ValidationReport | null; uploadRecord: UploadRecord | null }) {
  if (!report) {
    return <p className="muted compact">Upload and validate a workbook to view validation details.</p>;
  }

  return (
    <div className="modal-stack">
      <div className="validation-summary-row">
        <span><strong>{report.summary.blocking_errors}</strong>Block</span>
        <span><strong>{report.summary.warnings_ack_required}</strong>Ack</span>
        <span><strong>{report.summary.warnings}</strong>Warning</span>
        <span><strong>{report.summary.passed_checks}</strong>Passed</span>
      </div>
      {uploadRecord?.canonical_invoice ? (
        <div className="modal-link-row">
          <a href={canonicalInvoiceUrl(uploadRecord.upload_id)} target="_blank" rel="noreferrer">Open canonical JSON</a>
          <a href={canonicalInvoiceDownloadUrl(uploadRecord.upload_id)}>Download canonical JSON</a>
        </div>
      ) : null}
      <div className="validation-result-list">
        {report.results.map((result, index) => (
          <article className={`validation-result-item ${result.severity}`} key={`${result.rule_id}-${index}`}>
            <strong>{result.rule_id}</strong>
            <span>{result.status.replaceAll("_", " ")}</span>
            <p>{result.message}</p>
            {result.corrective_action ? <small>{result.corrective_action}</small> : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function CanonicalDetails({ uploadRecord }: { uploadRecord: UploadRecord | null }) {
  if (!uploadRecord?.canonical_invoice) {
    return <p className="muted compact">Canonical JSON is available after a workbook upload is parsed.</p>;
  }

  return (
    <div className="modal-stack">
      <div className="modal-link-row">
        <a href={canonicalInvoiceUrl(uploadRecord.upload_id)} target="_blank" rel="noreferrer">Open JSON</a>
        <a href={canonicalInvoiceDownloadUrl(uploadRecord.upload_id)}>Download JSON</a>
      </div>
      <pre className="json-preview">{JSON.stringify(uploadRecord.canonical_invoice, null, 2)}</pre>
    </div>
  );
}

function InvoiceLineDetails({ lines }: { lines: Array<Record<string, unknown>> }) {
  if (!lines.length) {
    return <p className="muted compact">Upload a workbook to view invoice lines.</p>;
  }

  return (
    <div className="invoice-line-detail-list">
      {lines.map((line, index) => (
        <article key={`${String(line.line_number ?? index)}`}>
          <span>{String(line.line_number ?? index + 1).padStart(2, "0")}</span>
          <strong>{String(line.description ?? line.item_name ?? "Line item")}</strong>
          <small>
            Qty {String(line.quantity ?? "-")} {String(line.unit_code ?? "")} / Net {formatMoney(line.line_net_amount)} / VAT {formatMoney(line.tax_amount)}
          </small>
        </article>
      ))}
    </div>
  );
}

function ReviewField({
  className = "",
  label,
  value,
  variant
}: {
  className?: string;
  label: string;
  value: unknown;
  variant?: "money";
}) {
  return (
    <div className={`review-field ${className}`.trim()}>
      <span>{label}</span>
      <strong>{variant === "money" ? formatMoney(value) : formatValue(value)}</strong>
    </div>
  );
}

function formatValue(value: unknown): string {
  return value === undefined || value === null || value === "" ? "Pending" : String(value);
}

function formatMoney(value: unknown): string {
  if (value === undefined || value === null || value === "") {
    return "Pending";
  }
  const amount = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(amount)) {
    return String(value);
  }
  return new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(amount);
}
