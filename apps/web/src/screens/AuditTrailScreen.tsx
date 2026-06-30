import { useEffect, useMemo, useState } from "react";
import { Download, Eye, FileJson, FileText, PackageOpen, Search } from "lucide-react";

import {
  auditEvidenceFileDownloadUrl,
  evidenceBundleDownloadUrl,
  fetchAuditDetail,
  fetchAuditEntries,
  fetchAuditEvidenceFilePreview
} from "../services/api";
import type { AuditDetail, AuditEntry, AuditEvidenceFile, EvidenceFilePreview } from "../types";

export function AuditTrailScreen() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [selectedUploadId, setSelectedUploadId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AuditDetail | null>(null);
  const [preview, setPreview] = useState<EvidenceFilePreview | null>(null);
  const [countryFilter, setCountryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("Loading audit trail");
  const [detailStatus, setDetailStatus] = useState("Select an audit item");

  useEffect(() => {
    let isMounted = true;
    fetchAuditEntries()
      .then((payload) => {
        if (!isMounted) return;
        setEntries(payload);
        setStatus(payload.length ? "Loaded" : "No evidence records yet");
        setSelectedUploadId((current) => current ?? payload[0]?.upload_id ?? null);
      })
      .catch((error: unknown) => {
        if (!isMounted) return;
        setStatus(error instanceof Error ? error.message : "Audit trail unavailable");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedUploadId) {
      setDetail(null);
      setPreview(null);
      setDetailStatus("Select an audit item");
      return;
    }
    let isMounted = true;
    setDetailStatus("Loading audit detail");
    fetchAuditDetail(selectedUploadId)
      .then((payload) => {
        if (!isMounted) return;
        setDetail(payload);
        setPreview(null);
        setDetailStatus("Loaded");
      })
      .catch((error: unknown) => {
        if (!isMounted) return;
        setDetail(null);
        setPreview(null);
        setDetailStatus(error instanceof Error ? error.message : "Audit detail unavailable");
      });
    return () => {
      isMounted = false;
    };
  }, [selectedUploadId]);

  const countries = useMemo(
    () => Array.from(new Set(entries.map((entry) => entry.country_regime))).sort(),
    [entries]
  );

  const filteredEntries = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return entries.filter((entry) => {
      const countryMatches = countryFilter === "all" || entry.country_regime === countryFilter;
      const statusMatches = statusFilter === "all" || entry.validation_status === statusFilter;
      const textMatches =
        !needle ||
        [entry.invoice_number, entry.seller, entry.buyer, entry.original_filename]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(needle));
      return countryMatches && statusMatches && textMatches;
    });
  }, [countryFilter, entries, search, statusFilter]);

  async function handlePreview(file: AuditEvidenceFile) {
    if (!detail || !file.preview_available) return;
    const payload = await fetchAuditEvidenceFilePreview(detail.entry.upload_id, file.filename);
    setPreview(payload);
  }

  return (
    <main className="audit-page">
      <section className="card audit-shell" aria-labelledby="audit-heading">
        <div className="audit-header">
          <div>
            <p className="eyebrow">Audit Trail</p>
            <h2 id="audit-heading">Evidence history</h2>
          </div>
          <p className="muted compact">Generated only. External sandbox statuses are evidence records, not delivery claims.</p>
        </div>

        <div className="audit-filters" aria-label="Audit filters">
          <label className="audit-search">
            <Search size={16} aria-hidden="true" />
            <span className="sr-only">Search invoice number, seller or buyer</span>
            <input
              type="search"
              value={search}
              placeholder="Search invoice, seller or buyer"
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <label>
            <span>Country</span>
            <select value={countryFilter} onChange={(event) => setCountryFilter(event.target.value)}>
              <option value="all">All regimes</option>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="all">All statuses</option>
              <option value="passed">Passed</option>
              <option value="passed_with_warnings">Passed with warnings</option>
              <option value="failed">Failed</option>
            </select>
          </label>
        </div>

        <div className="audit-layout">
          <div className="audit-list" aria-label="Audit records">
            <div className="audit-table-head">
              <span>Uploaded</span>
              <span>Invoice</span>
              <span>Regime</span>
              <span>Gross</span>
              <span>Validation</span>
            </div>
            {filteredEntries.map((entry) => (
              <button
                className={entry.upload_id === selectedUploadId ? "audit-row selected" : "audit-row"}
                key={entry.upload_id}
                onClick={() => setSelectedUploadId(entry.upload_id)}
                type="button"
              >
                <span>{formatDate(entry.uploaded_at)}</span>
                <strong>{entry.invoice_number ?? "Pending"}</strong>
                <span>{entry.country_regime}</span>
                <span>{formatMoney(entry.gross_amount, entry.currency)}</span>
                <StatusBadge status={entry.validation_status} />
              </button>
            ))}
            {!filteredEntries.length ? <div className="audit-empty">{status}</div> : null}
          </div>

          <section className="audit-detail" aria-label="Audit detail">
            {detail ? (
              <>
                <div className="audit-detail-title">
                  <div>
                    <p className="eyebrow">Selected Evidence</p>
                    <h3>{detail.entry.invoice_number ?? "No valid invoice loaded"}</h3>
                  </div>
                  {detail.evidence_bundle_download_url ? (
                    <a
                      className="audit-icon-button"
                      href={evidenceBundleDownloadUrl(detail.entry.upload_id)}
                      title="Download evidence bundle"
                    >
                      <PackageOpen size={16} aria-hidden="true" />
                      <span>ZIP</span>
                    </a>
                  ) : (
                    <span className="audit-missing">Evidence bundle not available for this item.</span>
                  )}
                </div>

                <SummaryStrip detail={detail} />
                <StatusSections detail={detail} />
                <EvidenceViewer detail={detail} preview={preview} onPreview={handlePreview} />
              </>
            ) : (
              <div className="audit-empty">{detailStatus}</div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function SummaryStrip({ detail }: { detail: AuditDetail }) {
  return (
    <div className="audit-summary-strip">
      <SummaryCell label="Seller" value={textValue(detail.invoice_summary.seller)} />
      <SummaryCell label="Buyer" value={textValue(detail.invoice_summary.buyer)} />
      <SummaryCell label="Currency" value={textValue(detail.invoice_summary.currency)} />
      <SummaryCell
        label="Gross"
        value={formatMoney(textValue(detail.invoice_summary.gross), textValue(detail.invoice_summary.currency))}
      />
    </div>
  );
}

function SummaryCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="audit-summary-cell">
      <span>{label}</span>
      <strong>{value || "Not available"}</strong>
    </div>
  );
}

function StatusSections({ detail }: { detail: AuditDetail }) {
  return (
    <div className="audit-status-grid">
      <StatusBlock title="Internal validation" status={textValue(detail.validation_summary.overall_status)} />
      <StatusBlock title="XML generation" status={detail.entry.xml_generation_status} />
      <StatusBlock title="XML validation" status={textValue(detail.xml_validation_summary.overall_status)} />
      <StatusBlock title="Official validators" status={textValue(detail.official_validator_status.status)} />
      <StatusBlock title="External sandbox validation" status={textValue(detail.external_validation.status)} />
      <StatusBlock title="Sandbox send" status={textValue(detail.sandbox_send.status)} />
    </div>
  );
}

function StatusBlock({ title, status }: { title: string; status: string }) {
  return (
    <div className="audit-status-block">
      <span>{title}</span>
      <StatusBadge status={status || "not_available"} />
    </div>
  );
}

function EvidenceViewer({
  detail,
  preview,
  onPreview
}: {
  detail: AuditDetail;
  preview: EvidenceFilePreview | null;
  onPreview: (file: AuditEvidenceFile) => void;
}) {
  return (
    <div className="evidence-viewer">
      <div className="audit-subheading">
        <FileJson size={16} aria-hidden="true" />
        <span>Evidence files</span>
      </div>
      <div className="evidence-file-list">
        {detail.evidence_files.map((file) => (
          <div className="evidence-file-row" key={file.filename}>
            <div>
              <strong>{file.filename}</strong>
              <span>{file.status}</span>
            </div>
            <div className="evidence-actions">
              <button disabled={!file.preview_available} onClick={() => onPreview(file)} title="Preview file" type="button">
                <Eye size={15} aria-hidden="true" />
              </button>
              {file.download_url ? (
                <a href={auditEvidenceFileDownloadUrl(detail.entry.upload_id, file.filename)} title="Download file">
                  <Download size={15} aria-hidden="true" />
                </a>
              ) : (
                <button disabled title="Download unavailable" type="button">
                  <Download size={15} aria-hidden="true" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="evidence-preview">
        <div className="audit-subheading">
          <FileText size={16} aria-hidden="true" />
          <span>{preview ? preview.filename : "Preview"}</span>
        </div>
        {preview ? (
          preview.preview_available ? (
            <pre>{typeof preview.content === "string" ? preview.content : JSON.stringify(preview.content, null, 2)}</pre>
          ) : (
            <p>{preview.message ?? "Preview is not available for this file."}</p>
          )
        ) : (
          <p>Select a JSON, XML or text evidence file to preview it here.</p>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalised = status.replaceAll("_", " ");
  const tone = status.includes("failed") || status === "failed" ? "failed" : status.includes("passed") ? "passed" : "neutral";
  return <span className={`audit-status ${tone}`}>{normalised}</span>;
}

function formatDate(value: string | null): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function formatMoney(amount: string | null, currency: string | null): string {
  if (!amount) return "Not available";
  const parsed = Number(amount);
  if (Number.isNaN(parsed)) return currency ? `${amount} ${currency}` : amount;
  return `${parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${currency ? ` ${currency}` : ""}`;
}

function textValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}
