import { useEffect, useState } from "react";

import { fetchAuditEntries } from "../services/api";
import type { AuditEntry } from "../types";

export function AuditTrailScreen() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [status, setStatus] = useState("Loading audit trail");

  useEffect(() => {
    let isMounted = true;
    fetchAuditEntries()
      .then((payload) => {
        if (!isMounted) return;
        setEntries(payload);
        setStatus(payload.length ? "Loaded" : "No evidence records yet");
      })
      .catch((error: unknown) => {
        if (!isMounted) return;
        setStatus(error instanceof Error ? error.message : "Audit trail unavailable");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="audit-page">
      <section className="card audit-card" aria-labelledby="audit-heading">
        <div className="section-heading">
          <p className="eyebrow">Audit Trail</p>
          <h2 id="audit-heading">Evidence records</h2>
        </div>
        <div className="table-shell">
          <table>
            <thead>
              <tr>
                <th>Generated at</th>
                <th>Invoice number</th>
                <th>Country pack</th>
                <th>Output profile</th>
                <th>Status</th>
                <th>Warnings</th>
                <th>Pack version</th>
                <th>Download ZIP</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={`${entry.invoice_number ?? "pending"}-${entry.country_pack}`}>
                  <td>{entry.generated_at}</td>
                  <td>{entry.invoice_number ?? "Pending"}</td>
                  <td>{entry.country_pack}</td>
                  <td>{entry.output_profile ?? "None"}</td>
                  <td>{entry.status}</td>
                  <td>{entry.warnings}</td>
                  <td>{entry.pack_version}</td>
                  <td>{entry.download_zip ?? "Not generated"}</td>
                </tr>
              ))}
              {!entries.length ? (
                <tr>
                  <td colSpan={8}>{status}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
