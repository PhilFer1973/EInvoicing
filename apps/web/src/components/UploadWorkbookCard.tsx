import { UploadCloud } from "lucide-react";
import { DragEvent, useRef, useState } from "react";

import { uploadWorkbook } from "../services/api";
import type { UploadRecord } from "../types";

interface UploadWorkbookCardProps {
  selectedPackId: string | null;
  onUploadComplete: (record: UploadRecord) => void;
}

export function UploadWorkbookCard({ selectedPackId, onUploadComplete }: UploadWorkbookCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "uploaded" | "failed">("idle");
  const [message, setMessage] = useState("No workbook uploaded");

  async function handleFile(file: File | undefined) {
    if (!file || !selectedPackId) return;
    setStatus("uploading");
    setMessage(`Uploading ${file.name}`);
    try {
      const record = await uploadWorkbook(file, selectedPackId);
      onUploadComplete(record);
      setStatus(record.validation_report.summary.blocking_errors > 0 ? "failed" : "uploaded");
      setMessage(record.validation_report.summary.blocking_errors > 0 ? "Parsed with blocking errors" : "Workbook parsed");
    } catch (error) {
      setStatus("failed");
      setMessage(error instanceof Error ? error.message : "Upload failed");
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    void handleFile(event.dataTransfer.files.item(0) ?? undefined);
  }

  return (
    <section className="card stack" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload Workbook</h2>
      <div
        className={`drop-zone ${status}`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={onDrop}
      >
        <UploadCloud aria-hidden="true" size={26} />
        <strong>Excel workbook</strong>
        <button
          className="button-secondary"
          disabled={!selectedPackId || status === "uploading"}
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          Select file
        </button>
        <input
          accept=".xlsx"
          aria-label="Select Excel workbook"
          hidden
          onChange={(event) => void handleFile(event.target.files?.item(0) ?? undefined)}
          ref={inputRef}
          type="file"
        />
      </div>
      <div className={`status-line ${status}`}>{message}</div>
    </section>
  );
}
