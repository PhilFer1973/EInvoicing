import { AlertCircle, CheckCircle2, ListFilter } from "lucide-react";
import { useState } from "react";

import type { UploadRecord, ValidationResult } from "../types";

interface ValidationSummaryCardProps {
  uploadRecord: UploadRecord | null;
}

export function ValidationSummaryCard({ uploadRecord }: ValidationSummaryCardProps) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const summary = uploadRecord?.validation_report.summary;
  const results = uploadRecord?.validation_report.results ?? [];
  const problemResults = results.filter((result) => result.status === "failed");

  return (
    <section className="card stack" aria-labelledby="validation-summary-heading">
      <div className="section-heading inline">
        <h2 id="validation-summary-heading">Validation Summary</h2>
        {summary?.blocking_errors ? (
          <AlertCircle aria-hidden="true" className="danger-icon" size={22} />
        ) : (
          <CheckCircle2 aria-hidden="true" className="success-icon" size={22} />
        )}
      </div>
      <div className="summary-grid">
        <StatusMetric label="Internal" value={summary?.internal_validation ?? "not_run"} />
        <StatusMetric label="Official artefact" value={summary?.official_artefact_validation ?? "not_configured"} />
        <StatusMetric label="Blocking errors" value={String(summary?.blocking_errors ?? 0)} />
        <StatusMetric label="Warnings" value={String((summary?.warnings ?? 0) + (summary?.warnings_ack_required ?? 0))} />
      </div>
      <button
        className="button-secondary drawer-trigger"
        disabled={!uploadRecord}
        onClick={() => setIsDrawerOpen((current) => !current)}
        type="button"
      >
        <ListFilter aria-hidden="true" size={16} />
        Error and warning drawer
      </button>
      {isDrawerOpen ? (
        <div className="validation-drawer">
          {problemResults.length ? (
            problemResults.map((result) => <ValidationDrawerItem key={result.rule_id} result={result} />)
          ) : (
            <p>No blocking errors or warnings are present.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}

function StatusMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value.replaceAll("_", " ")}</strong>
    </div>
  );
}

function ValidationDrawerItem({ result }: { result: ValidationResult }) {
  return (
    <article className={`drawer-item ${result.severity}`}>
      <strong>{result.rule_id}</strong>
      <p>{result.message}</p>
      {result.corrective_action ? <small>{result.corrective_action}</small> : null}
    </article>
  );
}
