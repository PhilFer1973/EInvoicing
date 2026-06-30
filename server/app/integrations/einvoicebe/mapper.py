from __future__ import annotations

from app.integrations.einvoicebe.schemas import (
    EInvoiceBEConfig,
    EInvoiceBEExternalValidationStatus,
    EInvoiceBESandboxSendResponse,
    EInvoiceBESandboxSendStatus,
    EInvoiceBESendRequestEvidence,
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


def build_ubl_sandbox_send_request_evidence(
    *,
    config: EInvoiceBEConfig,
    xml_bytes: bytes,
    filename: str,
    sender_peppol_id: str | None,
    receiver_peppol_id: str | None,
    document_id: str | None = None,
) -> EInvoiceBESendRequestEvidence:
    send_endpoint = (
        config.document_send_url(document_id)
        if document_id
        else f"{config.api_base_url.rstrip('/')}/api/documents/{{document_id}}/send"
    )
    return EInvoiceBESendRequestEvidence(
        create_endpoint=config.document_ubl_url,
        send_endpoint=send_endpoint,
        form_fields=[
            {
                "name": "file",
                "filename": filename,
                "content_type": "application/xml",
                "sha256": sha256_bytes(xml_bytes),
            }
        ],
        query_parameters=_send_query_parameters(sender_peppol_id, receiver_peppol_id),
        document_id=document_id,
        sandbox_company_number=config.sandbox_company_number,
        sandbox_peppol_id=config.sandbox_peppol_id,
    )


def build_sandbox_send_status(
    *,
    response: EInvoiceBESandboxSendResponse,
    endpoint: str,
    submitted_at: str,
    sender_identity_check: dict | None = None,
) -> EInvoiceBESandboxSendStatus:
    return EInvoiceBESandboxSendStatus(
        status=response.status,
        submitted_at=submitted_at,
        provider_reference=response.provider_reference,
        document_id=response.document_id,
        provider_document_state=response.provider_document_state,
        endpoint=endpoint,
        messages=_unique_messages([response.message]),
        sender_identity_check=sender_identity_check,
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


def _send_query_parameters(sender_peppol_id: str | None, receiver_peppol_id: str | None) -> dict[str, str]:
    params: dict[str, str] = {}
    sender = _split_peppol_id(sender_peppol_id)
    receiver = _split_peppol_id(receiver_peppol_id)
    if sender:
        params["sender_peppol_scheme"] = sender[0]
        params["sender_peppol_id"] = sender[1]
    if receiver:
        params["receiver_peppol_scheme"] = receiver[0]
        params["receiver_peppol_id"] = receiver[1]
    return params


def _split_peppol_id(peppol_id: str | None) -> tuple[str, str] | None:
    if not peppol_id or ":" not in peppol_id:
        return None
    scheme, value = peppol_id.split(":", 1)
    scheme = scheme.strip()
    value = value.strip()
    if not scheme or not value:
        return None
    return scheme, value
