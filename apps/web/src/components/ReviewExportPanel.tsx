import { Archive, Code2, Download, ExternalLink, FileText, ListChecks, Send, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";

import {
  acknowledgeBoundaryWarnings,
  canonicalInvoiceDownloadUrl,
  canonicalInvoiceUrl,
  evidenceBundleDownloadUrl,
  fetchEInvoiceBEConfiguration,
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
  sendToEInvoiceBESandbox,
  sendToStorecoveSandbox,
  validateUploadPipeline
} from "../services/api";
import type {
  CountryPack,
  DecodedQrPayload,
  EInvoiceBEConfigurationStatus,
  ExternalValidationRecord,
  StorecoveConfigurationStatus,
  UploadRecord,
  ValidationReport
} from "../types";

interface ReviewExportPanelProps {
  pack: CountryPack | null;
  uploadRecord: UploadRecord | null;
  onUploadRecordChange?: (record: UploadRecord) => void;
}

type DetailView = "validation" | "canonical" | "lines" | "outputs" | null;

export function ReviewExportPanel({ pack, uploadRecord: incomingUploadRecord, onUploadRecordChange }: ReviewExportPanelProps) {
  const [localUploadRecord, setLocalUploadRecord] = useState<UploadRecord | null>(incomingUploadRecord);
  const uploadRecord = localUploadRecord;
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
  const [isSendingEInvoiceBE, setIsSendingEInvoiceBE] = useState(false);
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [validationPipelineAttempted, setValidationPipelineAttempted] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [storecoveConfig, setStorecoveConfig] = useState<StorecoveConfigurationStatus | null>(null);
  const [eInvoiceBEConfig, setEInvoiceBEConfig] = useState<EInvoiceBEConfigurationStatus | null>(null);
  const isBelgiumPack = pack?.country_pack_id === "belgium_peppol";
  const isSaudiPack = pack?.country_pack_id === "saudi_zatca";
  const isUkPack = pack?.country_pack_id === "uk_info";
  const acknowledgementRequired = isSaudiPack && (validationReport?.summary.warnings_ack_required ?? 0) > 0;
  const acknowledgementComplete = Boolean(uploadRecord?.acknowledged_warning_rule_ids?.length);
  const generationSupported = pack?.country_pack_id === "belgium_peppol" || isSaudiPack;
  const storecoveActionSupported = isUkPack && Boolean(pack?.sandbox_test_available_when_configured);
  const externalValidationPassed = uploadRecord?.external_validation?.status === "passed" && uploadRecord.external_validation.is_valid === true;
  const eInvoiceBESenderMatchesTenant = eInvoiceBESellerMatchesTenant(uploadRecord, eInvoiceBEConfig);
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
  const canSendEInvoiceBESandbox =
    isBelgiumPack &&
    Boolean(uploadRecord?.generated_xml_path) &&
    !hasRegimeMismatch &&
    (validationReport?.summary.blocking_errors ?? 1) === 0 &&
    externalValidationPassed &&
    eInvoiceBESenderMatchesTenant &&
    Boolean(eInvoiceBEConfig?.configured);
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
  const eInvoiceBESendTitle = eInvoiceBESandboxSendTitle({
    config: eInvoiceBEConfig,
    externalValidationPassed,
    hasXml: Boolean(uploadRecord?.generated_xml_path),
    senderMatchesTenant: eInvoiceBESenderMatchesTenant,
    uploadRecord,
    validationBlockingErrors: validationReport?.summary.blocking_errors ?? 1
  });

  useEffect(() => {
    setLocalUploadRecord(incomingUploadRecord);
    setValidationReport(incomingUploadRecord?.validation_report ?? null);
    setDetailView(null);
    setGenerationError("");
    setIsExporting(false);
    setValidationPipelineAttempted(false);
    setIsSendingEInvoiceBE(false);
  }, [incomingUploadRecord?.upload_id]);

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

  useEffect(() => {
    let active = true;
    if (!isBelgiumPack || !externalValidationPassed) {
      setEInvoiceBEConfig(null);
      return () => {
        active = false;
      };
    }

    void fetchEInvoiceBEConfiguration()
      .then((config) => {
        if (active) setEInvoiceBEConfig(config);
      })
      .catch(() => {
        if (active) {
          setEInvoiceBEConfig({
            enabled: false,
            configured: false,
            api_base_url: "https://api.e-invoice.be",
            sandbox_company_number: "",
            sandbox_peppol_id: "",
            missing_fields: [],
            mode: "disabled",
            message: "e-invoice.be sandbox send is not configured. Add API credentials to enable sandbox send."
          });
        }
      });

    return () => {
      active = false;
    };
  }, [externalValidationPassed, isBelgiumPack]);

  async function handleValidate() {
    if (!uploadRecord) return;
    setIsValidating(true);
    try {
      const record = await validateUploadPipeline(uploadRecord.upload_id);
      setLocalUploadRecord(record);
      setValidationReport(record.validation_report);
      onUploadRecordChange?.(record);
      setValidationPipelineAttempted(true);
      setDetailView("validation");
    } catch {
      setValidationPipelineAttempted(true);
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
      const nextRecord = {
        ...uploadRecord,
        status: "generated",
        evidence_bundle_preview: evidence,
        generated_xml_path: xmlFile?.storage_path ?? uploadRecord.generated_xml_path,
        generated_xml_sha256_hash: xmlFile?.sha256 ?? uploadRecord.generated_xml_sha256_hash
      };
      setLocalUploadRecord(nextRecord);
      onUploadRecordChange?.(nextRecord);
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
      setLocalUploadRecord(record);
      onUploadRecordChange?.(record);
      setDetailView("outputs");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "Storecove sandbox test failed");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleEInvoiceBESandboxSend() {
    if (!uploadRecord || !canSendEInvoiceBESandbox) return;
    setIsSendingEInvoiceBE(true);
    setGenerationError("");
    try {
      const record = await sendToEInvoiceBESandbox(uploadRecord.upload_id);
      setLocalUploadRecord(record);
      onUploadRecordChange?.(record);
      setDetailView("outputs");
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "e-invoice.be sandbox send failed");
    } finally {
      setIsSendingEInvoiceBE(false);
    }
  }

  async function handleAcknowledge() {
    if (!uploadRecord || acknowledgementComplete) return;
    setIsAcknowledging(true);
    setGenerationError("");
    try {
      const record = await acknowledgeBoundaryWarnings(uploadRecord.upload_id);
      setLocalUploadRecord(record);
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
        {isBelgiumPack ? (
          <button
            aria-busy={isSendingEInvoiceBE}
            className={`button-primary action-button action-command-button ${isSendingEInvoiceBE ? "is-processing" : ""}`}
            disabled={!canSendEInvoiceBESandbox || isSendingEInvoiceBE}
            onClick={() => void handleEInvoiceBESandboxSend()}
            title={eInvoiceBESendTitle}
            type="button"
          >
            <Send aria-hidden="true" size={17} />
            {isSendingEInvoiceBE ? "Sending" : "Send to e-invoice.be sandbox"}
          </button>
        ) : null}
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
          pipelineAttempted={validationPipelineAttempted}
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
  pipelineAttempted,
  uploadRecord,
  validationReport
}: {
  detailView: Exclude<DetailView, null>;
  lines: Array<Record<string, unknown>>;
  onClose: () => void;
  pipelineAttempted: boolean;
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
        {detailView === "validation" ? (
          <ValidationDetails
            pipelineAttempted={pipelineAttempted}
            report={validationReport}
            uploadRecord={uploadRecord}
          />
        ) : null}
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
  const hasEInvoiceBESendResponse = Boolean(uploadRecord && hasStoredEvidenceFile(uploadRecord, "einvoicebe_send_response.json"));
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
  if (!uploadRecord.generated_xml_path && !hasStorecoveResponse && !hasEInvoiceBESendResponse) {
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
        {uploadRecord.external_validation ? (
          <article className={`output-artefact external-validation-output ${uploadRecord.external_validation.status}`}>
            <ListChecks aria-hidden="true" size={19} />
            <div>
              <strong>External sandbox validation</strong>
              <span>{formatExternalValidationStatus(uploadRecord.external_validation.status, uploadRecord.external_validation.is_valid)}</span>
              <small>{uploadRecord.external_validation.validated_at}</small>
              {uploadRecord.external_validation.reference ? <small>{uploadRecord.external_validation.reference}</small> : null}
            </div>
            <p className="external-validation-disclaimer">{uploadRecord.external_validation.disclaimer}</p>
            {uploadRecord.external_validation.messages.length ? (
              <ul className="external-validation-messages">
                {uniqueMessages(uploadRecord.external_validation.messages).map((message, index) => (
                  <li key={`${message}-${index}`}>{message}</li>
                ))}
              </ul>
            ) : null}
          </article>
        ) : null}
        {uploadRecord.external_sandbox_send ? (
          <article className={`output-artefact external-validation-output ${uploadRecord.external_sandbox_send.status}`}>
            <Send aria-hidden="true" size={19} />
            <div>
              <strong>External sandbox send</strong>
              <span>{formatExternalSandboxSendStatus(uploadRecord.external_sandbox_send.status)}</span>
              <small>{uploadRecord.external_sandbox_send.submitted_at}</small>
              {uploadRecord.external_sandbox_send.provider_reference ? <small>{uploadRecord.external_sandbox_send.provider_reference}</small> : null}
            </div>
            <p className="external-validation-disclaimer">{uploadRecord.external_sandbox_send.disclaimer}</p>
            {uploadRecord.external_sandbox_send.messages.length ? (
              <ul className="external-validation-messages">
                {uniqueMessages(uploadRecord.external_sandbox_send.messages).map((message, index) => (
                  <li key={`${message}-${index}`}>{message}</li>
                ))}
              </ul>
            ) : null}
          </article>
        ) : null}
        {uploadRecord.external_sandbox_send?.sender_identity_check ? (
          <article className="output-artefact sender-identity-output">
            <ListChecks aria-hidden="true" size={19} />
            <div>
              <strong>Sandbox sender identity check</strong>
              <span>Tenant {uploadRecord.external_sandbox_send.sender_identity_check.tenant_owned_sender_peppol_id ?? "not configured"}</span>
              <small>
                XML {uploadRecord.external_sandbox_send.sender_identity_check.xml_seller_endpoint_scheme ?? "-"}:
                {uploadRecord.external_sandbox_send.sender_identity_check.xml_seller_endpoint_id ?? "-"}
              </small>
              <small>
                Request {uploadRecord.external_sandbox_send.sender_identity_check.send_request_sender_scheme ?? "-"}:
                {uploadRecord.external_sandbox_send.sender_identity_check.send_request_sender_id ?? "-"}
              </small>
            </div>
            <p className="external-validation-disclaimer">
              XML sender match: {formatBoolean(uploadRecord.external_sandbox_send.sender_identity_check.xml_sender_matches_tenant)}. Send request match:{" "}
              {formatBoolean(uploadRecord.external_sandbox_send.sender_identity_check.send_request_sender_matches_tenant)}.
            </p>
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

function ValidationDetails({
  pipelineAttempted,
  report,
  uploadRecord
}: {
  pipelineAttempted: boolean;
  report: ValidationReport | null;
  uploadRecord: UploadRecord | null;
}) {
  if (!report) {
    return <p className="muted compact">Upload and validate a workbook to view validation details.</p>;
  }
  const externalValidation = uploadRecord?.external_validation ?? null;

  return (
    <div className="modal-stack">
      <section className="validation-detail-group">
        <h4>Internal validation</h4>
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
      </section>
      <section className="validation-detail-group">
        <h4>XML generation for validation</h4>
        <article className={`validation-result-item ${xmlGenerationTone(uploadRecord, report, pipelineAttempted)}`}>
          <strong>{xmlGenerationStatusLabel(uploadRecord, report, pipelineAttempted)}</strong>
          <span>{xmlGenerationStatusDetail(uploadRecord, report, pipelineAttempted)}</span>
          <p>{xmlGenerationStatusMessage(uploadRecord, report, pipelineAttempted)}</p>
        </article>
      </section>
      <section className="validation-detail-group">
        <h4>External sandbox validation</h4>
        <article className={`validation-result-item ${externalValidationTone(externalValidation)}`}>
          <strong>{externalValidationStatusTitle(externalValidation)}</strong>
          <span>{externalValidation?.status?.replaceAll("_", " ") ?? "not run"}</span>
          <p>{externalValidationStatusMessage(externalValidation)}</p>
          <small>External sandbox validation only. This does not prove Peppol delivery or final statutory compliance.</small>
          {externalValidation?.status === "failed" && externalValidation.messages.length ? (
            <ul className="external-validation-messages in-validation-details">
              {uniqueMessages(externalValidation.messages).map((message, index) => (
                <li key={`${message}-${index}`}>{message}</li>
              ))}
            </ul>
          ) : null}
        </article>
      </section>
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

function formatExternalValidationStatus(status: string, isValid: boolean | null): string {
  if (status === "passed" || isValid === true) return "Provider result: passed";
  if (status === "failed" || isValid === false) return "External sandbox validation failed";
  return `Provider result: ${status.replaceAll("_", " ")}`;
}

function formatExternalSandboxSendStatus(status: string): string {
  if (status === "submitted") return "Sandbox send submitted";
  if (status === "failed") return "Sandbox send failed";
  if (status === "pending") return "Sandbox send pending";
  if (status === "not_run") return "Sandbox send not run";
  return `Sandbox send ${status.replaceAll("_", " ")}`;
}

function formatBoolean(value: boolean | null | undefined): string {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "not checked";
}

function eInvoiceBESandboxSendTitle({
  config,
  externalValidationPassed,
  hasXml,
  senderMatchesTenant,
  uploadRecord,
  validationBlockingErrors
}: {
  config: EInvoiceBEConfigurationStatus | null;
  externalValidationPassed: boolean;
  hasXml: boolean;
  senderMatchesTenant: boolean;
  uploadRecord: UploadRecord | null;
  validationBlockingErrors: number;
}): string {
  if (!uploadRecord) return "Upload and validate a Belgium workbook before sandbox send.";
  if (validationBlockingErrors > 0) return "Internal validation must pass before e-invoice.be sandbox send.";
  if (!hasXml) return "Belgium XML must be generated before e-invoice.be sandbox send.";
  if (!externalValidationPassed) return "External e-invoice.be sandbox validation must pass before sandbox send.";
  if (!config) return "Checking e-invoice.be sandbox configuration.";
  if (!config.configured) return "e-invoice.be sandbox send is not configured. Add API credentials to enable sandbox send.";
  if (!senderMatchesTenant) return "Sandbox send requires configured sender metadata to match the e-invoice.be tenant-owned sender Peppol ID.";
  return "Sandbox send only. This does not prove Peppol delivery, recipient acceptance or final statutory compliance.";
}

function eInvoiceBESellerMatchesTenant(uploadRecord: UploadRecord | null, config: EInvoiceBEConfigurationStatus | null): boolean {
  if (!uploadRecord?.canonical_invoice || !config?.sandbox_peppol_id) return false;
  const sellerPeppolId = uploadRecord.canonical_invoice.seller.einvoicebe_sender_peppol_id;
  if (sellerPeppolId === undefined || sellerPeppolId === null) return false;
  return normalisePeppolId(String(sellerPeppolId)) === normalisePeppolId(config.sandbox_peppol_id);
}

function normalisePeppolId(value: string): string {
  const [scheme, identifier] = value.split(":", 2);
  if (!scheme || !identifier) return value.trim();
  return `${scheme.trim()}:${identifier.trim()}`;
}

function xmlGenerationTone(uploadRecord: UploadRecord | null, report: ValidationReport, pipelineAttempted: boolean): string {
  if (uploadRecord?.generated_xml_path) return "info";
  if (uploadRecord?.selected_country_pack !== "belgium_peppol") return "info";
  if (report.summary.blocking_errors > 0) return "warning";
  if (pipelineAttempted) return "error";
  return "warning";
}

function xmlGenerationStatusLabel(uploadRecord: UploadRecord | null, report: ValidationReport, pipelineAttempted: boolean): string {
  if (uploadRecord?.generated_xml_path) return "Passed";
  if (uploadRecord?.selected_country_pack !== "belgium_peppol") return "Not required";
  if (report.summary.blocking_errors > 0) return "Skipped due to blocking validation errors";
  if (pipelineAttempted) return "Failed";
  return "Not run";
}

function xmlGenerationStatusDetail(uploadRecord: UploadRecord | null, report: ValidationReport, pipelineAttempted: boolean): string {
  if (uploadRecord?.generated_xml_path) return "generated";
  if (uploadRecord?.selected_country_pack !== "belgium_peppol") return "not required";
  if (report.summary.blocking_errors > 0) return "skipped";
  if (pipelineAttempted) return "failed";
  return "not run";
}

function xmlGenerationStatusMessage(uploadRecord: UploadRecord | null, report: ValidationReport, pipelineAttempted: boolean): string {
  if (uploadRecord?.generated_xml_path) return "Belgium XML was generated from canonical invoice JSON for validation/output evidence.";
  if (uploadRecord?.selected_country_pack !== "belgium_peppol") return "XML generation for external Belgium sandbox validation is not required for this country pack.";
  if (report.summary.blocking_errors > 0) return "Belgium XML generation for validation was skipped because internal validation has blocking errors.";
  if (pipelineAttempted) return "Belgium XML generation for validation did not complete. Check backend logs and retry validation.";
  return "Belgium XML generation for validation has not run.";
}

function externalValidationTone(externalValidation: ExternalValidationRecord | null): string {
  if (!externalValidation) return "info";
  if (externalValidation.status === "failed") return "warning";
  if (externalValidation.status === "passed") return "info";
  return "warning";
}

function externalValidationStatusTitle(externalValidation: ExternalValidationRecord | null): string {
  if (!externalValidation) return "External sandbox validation not run";
  if (externalValidation.status === "failed") return "External sandbox validation failed";
  if (externalValidation.status === "passed") return "External sandbox validation passed";
  if (externalValidation.status === "configuration_error") return "External sandbox validation configuration issue";
  if (externalValidation.status === "skipped") return "External sandbox validation skipped";
  if (externalValidation.status === "not_configured") return "External e-invoice.be sandbox validation not configured.";
  return `External sandbox validation ${externalValidation.status.replaceAll("_", " ")}`;
}

function externalValidationStatusMessage(externalValidation: ExternalValidationRecord | null): string {
  if (!externalValidation) return "External e-invoice.be sandbox validation has not run for this upload.";
  if (externalValidation.status === "configuration_error") {
    return externalValidation.messages[0] ?? "External sandbox validation could not run because the provider configuration needs attention.";
  }
  if (externalValidation.status === "not_configured") return "External e-invoice.be sandbox validation not configured.";
  if (externalValidation.status === "skipped") return externalValidation.messages[0] ?? "External sandbox validation skipped.";
  if (externalValidation.status === "not_run") return externalValidation.messages[0] ?? "External sandbox validation not run.";
  if (externalValidation.status === "failed") return "The external provider returned validation issues for the generated Belgium XML.";
  if (externalValidation.status === "passed") return "The external provider accepted the generated Belgium XML for sandbox validation.";
  return externalValidation.messages[0] ?? "External sandbox validation status is available.";
}

function uniqueMessages(messages: string[]): string[] {
  const seen = new Set<string>();
  return messages.filter((message) => {
    const normalised = message.trim();
    if (!normalised || seen.has(normalised)) return false;
    seen.add(normalised);
    return true;
  });
}
