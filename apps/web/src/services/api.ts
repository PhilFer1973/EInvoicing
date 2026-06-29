import type {
  AuditEntry,
  CountryPack,
  CountryPackList,
  DecodedQrPayload,
  EInvoiceBEConfigurationStatus,
  StorecoveConfigurationStatus,
  UploadRecord,
  ValidationReport
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function workbookTemplateUrl(): string {
  return `${API_BASE_URL}/api/templates/workbook`;
}

export function canonicalInvoiceUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/canonical-invoice`;
}

export function canonicalInvoiceDownloadUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/canonical-invoice/download`;
}

export function evidenceBundleDownloadUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/evidence-bundle/download`;
}

export function generatedXmlUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-xml`;
}

export function generatedXmlDownloadUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-xml/download`;
}

export function generatedQrUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-qr`;
}

export function generatedQrDownloadUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-qr/download`;
}

export function generatedPdfUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-pdf`;
}

export function generatedPdfDownloadUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-pdf/download`;
}

export function generatedQrPayloadDecodedDownloadUrl(uploadId: string): string {
  return `${API_BASE_URL}/api/uploads/${uploadId}/generated-qr-payload-decoded/download`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchCountryPacks(): Promise<CountryPack[]> {
  const payload = await request<CountryPackList>("/api/country-packs");
  return payload.country_packs;
}

export async function uploadWorkbook(file: File, selectedCountryPack: string): Promise<UploadRecord> {
  const body = new FormData();
  body.append("selected_country_pack", selectedCountryPack);
  body.append("file", file);
  return request<UploadRecord>("/api/uploads", {
    method: "POST",
    body
  });
}

export async function validateUpload(uploadId: string): Promise<ValidationReport> {
  return request<ValidationReport>(`/api/uploads/${uploadId}/validate`, {
    method: "POST"
  });
}

export async function validateUploadPipeline(uploadId: string): Promise<UploadRecord> {
  return request<UploadRecord>(`/api/uploads/${uploadId}/validate-pipeline`, {
    method: "POST"
  });
}

export async function generateOutput(uploadId: string): Promise<UploadRecord["evidence_bundle_preview"]> {
  return request<UploadRecord["evidence_bundle_preview"]>(`/api/uploads/${uploadId}/generate`, {
    method: "POST"
  });
}

export async function fetchStorecoveSandboxConfiguration(): Promise<StorecoveConfigurationStatus> {
  return request<StorecoveConfigurationStatus>("/api/uploads/storecove-sandbox/configuration");
}

export async function fetchEInvoiceBEConfiguration(): Promise<EInvoiceBEConfigurationStatus> {
  return request<EInvoiceBEConfigurationStatus>("/api/uploads/einvoicebe/configuration");
}

export async function sendToStorecoveSandbox(uploadId: string): Promise<UploadRecord> {
  return request<UploadRecord>(`/api/uploads/${uploadId}/storecove-sandbox`, {
    method: "POST"
  });
}

export async function validateWithEInvoiceBE(uploadId: string): Promise<UploadRecord> {
  return request<UploadRecord>(`/api/uploads/${uploadId}/einvoicebe-validation`, {
    method: "POST"
  });
}

export async function acknowledgeBoundaryWarnings(uploadId: string): Promise<UploadRecord> {
  return request<UploadRecord>(`/api/uploads/${uploadId}/acknowledge-boundaries`, {
    method: "POST"
  });
}

export async function fetchGeneratedQrPayloadDecoded(uploadId: string): Promise<DecodedQrPayload> {
  return request<DecodedQrPayload>(`/api/uploads/${uploadId}/generated-qr-payload-decoded`);
}

export async function fetchAuditEntries(): Promise<AuditEntry[]> {
  return request<AuditEntry[]>("/api/audit");
}
