import type { UploadRecord, ValidationResult } from "../types";

interface ValidationResultsPanelProps {
  uploadRecord: UploadRecord | null;
}

export function ValidationResultsPanel({ uploadRecord }: ValidationResultsPanelProps) {
  const results = uploadRecord?.validation_report.results ?? [];
  const blocking = results.filter((result) => result.severity === "error" && result.status === "failed");
  const ackWarnings = results.filter((result) => result.severity === "warning_ack_required" && result.status === "failed");
  const warnings = results.filter((result) => result.severity === "warning" && result.status === "failed");
  const passed = results.filter((result) => result.status === "passed");

  return (
    <section className="card stack" aria-labelledby="validation-results-heading">
      <h2 id="validation-results-heading">Validation Results</h2>
      <ResultGroup title="Blocking errors" results={blocking} emptyText="No blocking errors recorded." />
      <ResultGroup title="Warnings requiring acknowledgement" results={ackWarnings} emptyText="No acknowledgement warnings recorded." />
      <ResultGroup title="Non-blocking warnings" results={warnings} emptyText="No non-blocking warnings recorded." />
      <details className="technical-status">
        <summary>Technical validation status</summary>
        <p>Official artefact validation: {uploadRecord?.validation_report.summary.official_artefact_validation ?? "not_configured"}</p>
      </details>
      <details className="technical-status">
        <summary>Passed checks</summary>
        <ResultList results={passed} emptyText="Passed checks will appear after upload." />
      </details>
    </section>
  );
}

function ResultGroup({ title, results, emptyText }: { title: string; results: ValidationResult[]; emptyText: string }) {
  return (
    <div className="result-group">
      <h3>{title}</h3>
      <ResultList results={results} emptyText={emptyText} />
    </div>
  );
}

function ResultList({ results, emptyText }: { results: ValidationResult[]; emptyText: string }) {
  if (!results.length) {
    return <p className="muted compact">{emptyText}</p>;
  }
  return (
    <div className="result-list">
      {results.map((result) => (
        <article className={`result-item ${result.severity}`} key={`${result.rule_id}-${result.field_path ?? "root"}`}>
          <strong>{result.rule_id}</strong>
          <span>{result.layer.replaceAll("_", " ")}</span>
          <p>{result.message}</p>
        </article>
      ))}
    </div>
  );
}
