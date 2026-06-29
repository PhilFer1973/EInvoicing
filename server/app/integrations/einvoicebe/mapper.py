from __future__ import annotations

from app.integrations.einvoicebe.schemas import (
    EInvoiceBEConfig,
    EInvoiceBEExternalValidationStatus,
    EInvoiceBEValidationRequestEvidence,
    EInvoiceBEValidationResponse,
)
from app.storage.file_store import sha256_bytes


def build_ubl_validation_request_evidence(
    *,
    config: EInvoiceBEConfig,
    xml_bytes: bytes,
    filename: str,
) -> EInvoiceBEValidationRequestEvidence:
    return EInvoiceBEValidationRequestEvidence(
        endpoint=config.validation_url,
        form_fields=[
            {
                "name": "file",
                "filename": filename,
                "content_type": "application/xml",
                "sha256": sha256_bytes(xml_bytes),
            }
        ],
        sandbox_company_number=config.sandbox_company_number,
        sandbox_peppol_id=config.sandbox_peppol_id,
    )


def build_external_validation_status(
    *,
    response: EInvoiceBEValidationResponse,
    endpoint: str,
    validated_at: str,
) -> EInvoiceBEExternalValidationStatus:
    status = "passed" if response.is_valid else "failed"
    return EInvoiceBEExternalValidationStatus(
        status=status,
        is_valid=response.is_valid,
        reference=response.id,
        validated_at=validated_at,
        issue_count=len(response.issues),
        messages=_unique_messages(issue.message for issue in response.issues),
        endpoint=endpoint,
    )


def _unique_messages(messages) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for message in messages:
        normalised = str(message).strip()
        if not normalised or normalised in seen:
            continue
        seen.add(normalised)
        unique.append(normalised)
    return unique
