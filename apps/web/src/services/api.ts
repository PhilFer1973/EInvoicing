import type { AuditEntry, CountryPack, CountryPackList, UploadRecord } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function workbookTemplateUrl(): string {
  return `${API_BASE_URL}/api/templates/workbook`;
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

export async function fetchAuditEntries(): Promise<AuditEntry[]> {
  return request<AuditEntry[]>("/api/audit");
}
