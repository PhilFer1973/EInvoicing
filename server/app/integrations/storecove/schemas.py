from __future__ import annotations

from pydantic import BaseModel, Field


UK_SANDBOX_WORDING = (
    "UK Peppol sandbox test only. This tests Peppol-style invoice readiness through a sandbox provider. "
    "It does not prove final UK 2029 statutory compliance."
)


class StorecoveConfigurationStatus(BaseModel):
    sandbox_enabled: bool
    configured: bool
    api_base_url: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    mode: str = "disabled"
    message: str


class StorecoveConfig(BaseModel):
    sandbox_enabled: bool
    api_base_url: str
    api_key: str
    sender_legal_entity_id: str
    receiver_legal_entity_id: str


class StorecoveParty(BaseModel):
    legal_entity_id: str
    name: str
    country_code: str
    tax_registration_number: str


class StorecoveLine(BaseModel):
    line_number: str
    description: str
    quantity: str
    unit_code: str
    unit_price: str
    net_amount: str
    tax_category_code: str
    tax_rate: str
    tax_amount: str


class StorecoveSandboxRequest(BaseModel):
    mode: str = "mocked_sandbox_readiness"
    network: str = "peppol"
    document_type: str = "invoice"
    sandbox_only: bool = True
    external_id: str
    sender: StorecoveParty
    receiver: StorecoveParty
    invoice: dict[str, str]
    totals: dict[str, str]
    tax_summary: list[dict[str, str]]
    lines: list[StorecoveLine]
    disclaimer: str = UK_SANDBOX_WORDING


class StorecoveSandboxResponse(BaseModel):
    mocked: bool = True
    provider: str = "storecove"
    status: str
    provider_reference: str
    message: str = "Mocked Storecove sandbox response. No live Storecove API call was made."
    disclaimer: str = UK_SANDBOX_WORDING


class StorecoveSandboxStatus(BaseModel):
    mocked: bool = True
    provider_reference: str
    status: str
    peppol_network_delivery: str = "not_submitted"
    official_validation: str = "not_configured"
    statutory_compliance: str = "not_proven"
    disclaimer: str = UK_SANDBOX_WORDING

