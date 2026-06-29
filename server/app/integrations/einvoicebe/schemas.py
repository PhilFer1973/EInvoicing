from __future__ import annotations

from pydantic import BaseModel, Field


EINVOICEBE_SANDBOX_WORDING = (
    "External sandbox validation only. This does not prove Peppol delivery or final statutory compliance."
)


class EInvoiceBEConfigurationStatus(BaseModel):
    enabled: bool
    configured: bool
    api_base_url: str
    sandbox_company_number: str
    sandbox_peppol_id: str
    missing_fields: list[str] = Field(default_factory=list)
    mode: str = "disabled"
    message: str


class EInvoiceBEConfig(BaseModel):
    enabled: bool
    api_base_url: str
    api_key: str
    sandbox_company_number: str
    sandbox_peppol_id: str

    @property
    def validation_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/api/validate/ubl"


class EInvoiceBEValidationIssue(BaseModel):
    message: str
    type: str = "error"
    location: str | None = None
    rule_id: str | None = None
    flag: str | None = None
    test: str | None = None
    schematron: str = ""


class EInvoiceBEValidationResponse(BaseModel):
    id: str
    file_name: str | None = None
    is_valid: bool
    issues: list[EInvoiceBEValidationIssue] = Field(default_factory=list)
    ubl_document: str | None = None
    http_status_code: int = 201
    raw_response: dict | None = None


class EInvoiceBEValidationRequestEvidence(BaseModel):
    provider: str = "e-invoice.be"
    endpoint: str
    method: str = "POST"
    content_type: str = "multipart/form-data"
    authorization: str = "Bearer [REDACTED]"
    form_fields: list[dict[str, str]]
    sandbox_company_number: str
    sandbox_peppol_id: str
    disclaimer: str = EINVOICEBE_SANDBOX_WORDING


class EInvoiceBEExternalValidationStatus(BaseModel):
    provider: str = "e-invoice.be"
    label: str = "External sandbox validation"
    status: str
    is_valid: bool | None = None
    reference: str | None = None
    validated_at: str
    issue_count: int
    messages: list[str] = Field(default_factory=list)
    endpoint: str
    peppol_delivery: str = "not_delivered"
    recipient_acceptance: str = "not_requested"
    smp_registration_claim: str = "not_claimed"
    disclaimer: str = EINVOICEBE_SANDBOX_WORDING

