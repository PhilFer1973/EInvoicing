import { Archive, Code2, Download, ExternalLink, FileText, ListChecks, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

import {
  acknowledgeBoundaryWarnings,
  canonicalInvoiceDownloadUrl,
  canonicalInvoiceUrl,
  evidenceBundleDownloadUrl,
  fetchStorecoveSandboxConfiguration,
  fetchGeneratedQrPayloadDecoded,
  generateOutput,
  generatedPdfDownloadUrl,
  generatedPdfUrl,
  generatedQrPayloadDecodedDownloadUrl,
  generatedQrDownloadUrl,
  generatedQrUrl,
  generatedXmlDownloadUrl,
  generatedXmlUrl,
  sendToStorecoveSandbox,
  validateUpload
} from "../services/api";
import type { CountryPack, DecodedQrPayload, StorecoveConfigurationStatus, UploadRecord, ValidationReport } from "../types";

interface ReviewExportPanelProps {
  pack: CountryPack | null;
  uploadRecord: UploadRecord | null;
  onUploadRecordChange?: (record: UploadRecord) => void;
}

type DetailView = "validation" | "canonical" | "lines" | "outputs" | null;

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
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [storecoveConfig, setStorecoveConfig] = useState<StorecoveConfigurationStatus | null>(null);
  const isSaudiPack = pack?.country_pack_id === "saudi_zatca";
  const isUkPack = pack?.country_pack_id === "uk_info";
  const acknowledgementRequired = isSaudiPack && (validationReport?.summary.warnings_ack_required ?? 0) > 0;
  const acknowledgementComplete = Boolean(uploadRecord?.acknowledged_warning_rule_ids?.length);
  const generationSupported = pack?.country_pack_id === "belgium_peppol" || isSaudiPack;
  const storecoveActionSupported = isUkPack && Boolean(pack?.sandbox_test_available_when_configured);
  const canExportZip =
    Boolean(uploadRecord?.evidence_bundle_preview.files.length) &&
    !hasRegimeMismatch &&
    (!acknowledgementRequired || acknowledgementComplete);
  const canGenerate =
    generationSupported &&
    Boolean(uploadRecord?.canonical_invoice) &&
    !hasRegimeMismatch &&
    (validationReport?.summary.blocking_errors ?? 1) === 0;
  const canSendStorecoveSandbox =
    storecoveActionSupported &&
    Boolean(uploadRecord?.canonical_invoice) &&
    !hasRegimeMismatch &&
    (validationReport?.summary.blocking_errors ?? 1) === 0 &&
    Boolean(storecoveConfig?.configured);
  const generateTitle =
    isUkPack
      ? storecoveConfig?.message ?? "Storecove sandbox is not configured. Add sandbox credentials to enable UK Peppol testing."
      : canGenerate
      ? isSaudiPack
        ? "Generate offline/demo Saudi XML, QR tags 1-5 and visual PDF. No FATOORA submission, clearance, Phase Two cryptography or production signature."
        : "Generate Belgium Peppol-style UBL XML."
      : generationSupported
        ? "Resolve blocking validation errors before generation."
        : "Generation is not configured for this country pack.";
  const actionLabel = "Generate";
  const isActionEnabled = isUkPack ? canSendStorecoveSandbox : canGenerate;

  useEffect(() => {
    setValidationReport(uploadRecord?.validation_report ?? null);
    setDetailView(null);
    setGenerationError("");
    setIsExporting(false);
  }, [uploadRecord?.upload_id]);

  useEffect(() => {
    if (!isExporting) return;
    const timer = window.setTimeout(() => setIsExporting(false), 900);
    return () => window.clearTimeout(timer);
  }, [isExporting]);

  useEffect(() => {
    let active = true;
    if (!isUkPack) {
      setStorecoveConfig(null);
      return () => {
        active = false;
      };
    }

    void fetchStorecoveSandboxConfiguration()
      .then((config) => {
        if (active) setStorecoveConfig(config);
      })
      .catch(() => {
        if (active) {
          setStorecoveConfig({
            sandbox_enabled: false,
            configured: false,
            api_base_url: null,
            missing_fields: [],
            mode: "disabled",
            message: "Storecove sandbox is not configured. Add sandbox credentials to enable UK Peppol testing."
          });
        }
      });

    return () => {
      active = false;
    };
  }, [isUkPack]);

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
      setDetailView("outputs");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "XML generation failed");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleStorecoveSandbox() {
    if (!uploadRecord || !canSendStorecoveSandbox) return;
    setIsGenerating(true);
    setGenerationError("");
    try {
      const record = await sendToStorecoveSandbox(uploadRecord.upload_id);
      onUploadRecordChange?.(record);
      setDetailView("outputs");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "Storecove sandbox test failed");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleAcknowledge() {
    if (!uploadRecord || acknowledgementComplete) return;
    setIsAcknowledging(true);
    setGenerationError("");
    try {
      const record = await acknowledgeBoundaryWarnings(uploadRecord.upload_id);
      onUploadRecordChange?.(record);
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "Could not acknowledge the Saudi V1 boundary");
    } finally {
      setIsAcknowledging(false);
    }
  }

  function handleExport() {
    setIsExporting(true);
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
        <button
          aria-busy={isValidating}
          className={`button-primary action-button action-command-button ${isValidating ? "is-processing" : ""}`}
          disabled={!uploadRecord || isValidating}
          onClick={() => void handleValidate()}
          type="button"
        >
          <ListChecks aria-hidden="true" size={17} />
          {isValidating ? "Validating" : "Validate"}
        </button>
        <button
          aria-busy={isGenerating}
          className={`button-primary action-button action-command-button ${isGenerating ? "is-processing" : ""}`}
          disabled={!isActionEnabled || isGenerating}
          onClick={() => {
            if (isUkPack) {
              void handleStorecoveSandbox();
            } else {
              void handleGenerate();
            }
          }}
          title={generateTitle}
          type="button"
        >
          <Sparkles aria-hidden="true" size={17} />
          {isGenerating ? (isUkPack ? "Sending" : "Generating") : actionLabel}
        </button>
        {generationError ? <p className="action-error">{generationError}</p> : null}
        {acknowledgementRequired ? (
          <label className="acknowledgement v1-boundary-acknowledgement">
            <input
              checked={acknowledgementComplete}
              disabled={acknowledgementComplete || isAcknowledging}
              onChange={(event) => {
                if (event.target.checked) void handleAcknowledge();
              }}
              type="checkbox"
            />
            <span>
              {acknowledgementComplete
                ? "Saudi V1 boundary acknowledged."
                : "Acknowledge: generated only, not submitted, cleared or production-signed."}
            </span>
          </label>
        ) : null}
        {uploadRecord && canExportZip ? (
          <a
            aria-busy={isExporting}
            className={`button-primary action-button action-command-button export-zip-button ${isExporting ? "is-processing" : ""}`}
            href={evidenceBundleDownloadUrl(uploadRecord.upload_id)}
            onClick={handleExport}
          >
            <Archive aria-hidden="true" size={17} />
            {isExporting ? "Exporting" : "Export ZIP"}
          </a>
        ) : (
          <button className="button-primary action-button action-command-button export-zip-button" disabled type="button">
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
  validationReport
}: {
  detailView: Exclude<DetailView, null>;
  lines: Array<Record<string, unknown>>;
  onClose: () => void;
  uploadRecord: UploadRecord | null;
  validationReport: ValidationReport | null;
}) {
  const title =
    detailView === "validation"
      ? "Validation Details"
        : detailView === "canonical"
        ? "Canonical JSON"
        : detailView === "outputs"
          ? "Generated Outputs"
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
        {detailView === "outputs" ? <GeneratedOutputDetails uploadRecord={uploadRecord} /> : null}
      </section>
    </div>
  );
}

function GeneratedOutputDetails({ uploadRecord }: { uploadRecord: UploadRecord | null }) {
  const hasQr = Boolean(uploadRecord && hasStoredEvidenceFile(uploadRecord, "qr.png"));
  const hasPdf = Boolean(uploadRecord && hasStoredEvidenceFile(uploadRecord, "saudi_visual_invoice.pdf"));
  const hasStorecoveResponse = Boolean(uploadRecord && hasStoredEvidenceFile(uploadRecord, "storecove_response.json"));
  const [decodedQrPayload, setDecodedQrPayload] = useState<DecodedQrPayload | null>(null);
  const [decodedQrError, setDecodedQrError] = useState("");

  useEffect(() => {
    let active = true;
    if (!uploadRecord || !hasQr) {
      setDecodedQrPayload(null);
      setDecodedQrError("");
      return () => {
        active = false;
      };
    }

    void fetchGeneratedQrPayloadDecoded(uploadRecord.upload_id)
      .then((payload) => {
        if (active) setDecodedQrPayload(payload);
      })
      .catch(() => {
        if (active) setDecodedQrError("Decoded QR payload is not available.");
      });

    return () => {
      active = false;
    };
  }, [hasQr, uploadRecord?.upload_id]);

  if (!uploadRecord) {
    return <p className="muted compact">Generated outputs are available after successful generation.</p>;
  }
  if (!uploadRecord.generated_xml_path && !hasStorecoveResponse) {
    return <p className="muted compact">Generated outputs are available after successful generation.</p>;
  }

  return (
    <div className="modal-stack">
      <div className="output-artefact-list">
        {uploadRecord.generated_xml_path ? (
          <article className="output-artefact">
            <FileText aria-hidden="true" size={19} />
            <div>
              <strong>Invoice XML</strong>
              <span>Generated only; official artefact validation not configured</span>
            </div>
            <div className="output-artefact-links">
              <a aria-label="Open invoice XML" className="output-artefact-action" href={generatedXmlUrl(uploadRecord.upload_id)} rel="noreferrer" target="_blank" title="Open invoice XML">
                <ExternalLink aria-hidden="true" size={15} />
              </a>
              <a aria-label="Download invoice XML" className="output-artefact-action" href={generatedXmlDownloadUrl(uploadRecord.upload_id)} title="Download invoice XML">
                <Download aria-hidden="true" size={15} />
              </a>
            </div>
          </article>
        ) : null}
        {hasStorecoveResponse ? (
          <article className="output-artefact storecove-output">
            <FileText aria-hidden="true" size={19} />
            <div>
              <strong>Storecove sandbox result</strong>
              <span>Mocked/test only; no live Storecove API call was made</span>
              {uploadRecord.storecove_provider_reference ? <small>{uploadRecord.storecove_provider_reference}</small> : null}
            </div>
          </article>
        ) : null}
        {hasQr ? (
          <article className="output-artefact output-artefact-qr">
            <img alt="Saudi QR code" src={generatedQrUrl(uploadRecord.upload_id)} />
            <div>
              <strong>QR code</strong>
              <span>Phase-1-style tags 1-5 only</span>
            </div>
            <div className="output-artefact-links">
              <a aria-label="Open QR image" className="output-artefact-action" href={generatedQrUrl(uploadRecord.upload_id)} rel="noreferrer" target="_blank" title="Open QR image">
                <ExternalLink aria-hidden="true" size={15} />
              </a>
              <a aria-label="Download QR image" className="output-artefact-action" href={generatedQrDownloadUrl(uploadRecord.upload_id)} title="Download QR image">
                <Download aria-hidden="true" size={15} />
              </a>
              <a aria-label="Download decoded QR JSON" className="output-artefact-action" href={generatedQrPayloadDecodedDownloadUrl(uploadRecord.upload_id)} title="Download decoded QR JSON">
                <Code2 aria-hidden="true" size={15} />
              </a>
            </div>
            <p className="qr-output-note">Normal QR scanners may show an encoded TLV string. Use the decoded QR payload view to inspect the invoice fields.</p>
          </article>
        ) : null}
        {hasPdf ? (
          <article className="output-artefact">
            <FileText aria-hidden="true" size={19} />
            <div>
              <strong>Arabic/bilingual visual PDF</strong>
              <span>Visual only, not a PDF/A-3 e-invoice</span>
            </div>
            <div className="output-artefact-links">
              <a aria-label="Open visual PDF" className="output-artefact-action" href={generatedPdfUrl(uploadRecord.upload_id)} rel="noreferrer" target="_blank" title="Open visual PDF">
                <ExternalLink aria-hidden="true" size={15} />
              </a>
              <a aria-label="Download visual PDF" className="output-artefact-action" href={generatedPdfDownloadUrl(uploadRecord.upload_id)} title="Download visual PDF">
                <Download aria-hidden="true" size={15} />
              </a>
            </div>
          </article>
        ) : null}
      </div>
      {decodedQrPayload ? (
        <section aria-label="Decoded QR payload" className="qr-decoded-payload">
          <h4>Decoded QR payload</h4>
          <dl>
            {decodedQrPayload.tags.map((tag) => (
              <div key={tag.tag}>
                <dt>Tag {tag.tag}: {tag.label}</dt>
                <dd>{tag.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
      {decodedQrError ? <p className="muted compact">{decodedQrError}</p> : null}
    </div>
  );
}

function hasStoredEvidenceFile(uploadRecord: UploadRecord, filename: string): boolean {
  return uploadRecord.evidence_bundle_preview.files.some(
    (file) => file.filename === filename && file.status === "stored" && Boolean(file.storage_path)
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
