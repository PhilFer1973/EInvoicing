import { Archive, FileCode2, FileText, QrCode } from "lucide-react";

import type { CountryPack, UploadRecord } from "../types";

interface ExportPanelProps {
  pack: CountryPack | null;
  uploadRecord: UploadRecord | null;
}

export function ExportPanel({ pack, uploadRecord }: ExportPanelProps) {
  const files = uploadRecord?.evidence_bundle_preview.files ?? [];
  const generationDisabled = true;
  const isInfoOnly = pack?.support_level === "info_only";

  return (
    <section className="card stack" aria-labelledby="export-heading">
      <h2 id="export-heading">Export</h2>
      {pack ? (
        <div className="capability-box">
          <strong>V1 app capability</strong>
          <ul>
            {pack.v1_app_capability.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="export-actions">
        {!isInfoOnly ? (
          <button className="button-primary" disabled={generationDisabled} type="button">
            <FileCode2 aria-hidden="true" size={16} />
            Generate XML
          </button>
        ) : null}
        {pack?.requires_pdf ? (
          <button className="button-secondary" disabled={generationDisabled} type="button">
            <FileText aria-hidden="true" size={16} />
            Generate Arabic/Bilingual Visual PDF
          </button>
        ) : null}
        {pack?.requires_qr ? (
          <button className="button-secondary" disabled={generationDisabled} type="button">
            <QrCode aria-hidden="true" size={16} />
            Generate QR
          </button>
        ) : null}
        <button className="button-secondary" disabled={generationDisabled || isInfoOnly} type="button">
          <Archive aria-hidden="true" size={16} />
          Generate ZIP bundle
        </button>
      </div>
      {pack?.requires_live_submission_for_validity ? (
        <label className="acknowledgement">
          <input disabled type="checkbox" />
          <span>{pack.v1_boundary_warning}</span>
        </label>
      ) : pack ? (
        <div className="acknowledgement neutral">{pack.v1_boundary_warning}</div>
      ) : null}
      <div className="bundle-list">
        {files.length ? (
          files.map((file) => (
            <div key={file.filename}>
              <span>{file.filename}</span>
              <strong>{file.status.replaceAll("_", " ")}</strong>
            </div>
          ))
        ) : (
          <p className="muted compact">Evidence bundle skeleton appears after workbook upload.</p>
        )}
      </div>
    </section>
  );
}
