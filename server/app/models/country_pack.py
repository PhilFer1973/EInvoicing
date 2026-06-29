from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OfficialSource(BaseModel):
    label: str
    url: str


class CountryPack(BaseModel):
    country_pack_id: str
    display_name: str
    country_code: str
    pack_version: str
    support_level: str
    sandbox_test_available_when_configured: bool = False
    v1_boundary: str
    v1_boundary_warning: str = ""
    output_profiles: list[str] = Field(default_factory=list)
    default_output_profile: str | None = None
    requires_pdf: bool = False
    requires_qr: bool = False
    requires_signature: bool = False
    requires_live_submission_for_validity: bool = False
    live_submission_supported: bool = False
    live_clearance_supported: bool = False
    production_signing_supported: bool = False
    official_artefact_validation: str = "not_configured"
    legal_regime_summary: str = ""
    scope: list[str] = Field(default_factory=list)
    mandatory_format: list[str] = Field(default_factory=list)
    transmission_or_clearance_model: list[str] = Field(default_factory=list)
    qr_signature_requirements: list[str] = Field(default_factory=list)
    retention_or_audit_notes: list[str] = Field(default_factory=list)
    v1_app_capability: list[str] = Field(default_factory=list)
    official_sources: list[OfficialSource] = Field(default_factory=list)
    regime_summary: str = ""
    legal_invoice_requirements: list[str] = Field(default_factory=list)
    einvoice_requirements: list[str] = Field(default_factory=list)
    source_status: list[str] = Field(default_factory=list)
    boundary_highlights: list[str] = Field(default_factory=list)
    last_reviewed: str
    raw: dict[str, Any] = Field(default_factory=dict)


class CountryPackList(BaseModel):
    country_packs: list[CountryPack]
