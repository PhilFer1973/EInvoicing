from __future__ import annotations

import os
from typing import Any

import httpx

from app.integrations.einvoicebe.schemas import (
    EInvoiceBEConfig,
    EInvoiceBEConfigurationStatus,
    EInvoiceBEDocumentResponse,
    EInvoiceBESandboxSendResponse,
    EInvoiceBEValidationIssue,
    EInvoiceBEValidationResponse,
)


CONFIGURATION_GUIDANCE = (
    "e-invoice.be validation is not configured. Add API credentials to enable external sandbox validation."
)
DEFAULT_API_BASE_URL = "https://api.e-invoice.be"
DEFAULT_SANDBOX_COMPANY_NUMBER = "099025170"
DEFAULT_SANDBOX_PEPPOL_ID = "0208:099025170"


def load_einvoicebe_configuration_status() -> EInvoiceBEConfigurationStatus:
    enabled = _env_bool("EINVOICEBE_ENABLED")
    base_url = os.getenv("EINVOICEBE_API_BASE_URL", DEFAULT_API_BASE_URL).strip() or DEFAULT_API_BASE_URL
    api_key = os.getenv("EINVOICEBE_API_KEY", "").strip()
    company_number = (
        os.getenv("EINVOICEBE_SANDBOX_COMPANY_NUMBER", DEFAULT_SANDBOX_COMPANY_NUMBER).strip()
        or DEFAULT_SANDBOX_COMPANY_NUMBER
    )
    peppol_id = (
        os.getenv("EINVOICEBE_SANDBOX_PEPPOL_ID", DEFAULT_SANDBOX_PEPPOL_ID).strip()
        or DEFAULT_SANDBOX_PEPPOL_ID
    )
    missing = ["EINVOICEBE_API_KEY"] if enabled and not api_key else []

    if not enabled:
        return EInvoiceBEConfigurationStatus(
            enabled=False,
            configured=False,
            api_base_url=base_url,
            sandbox_company_number=company_number,
            sandbox_peppol_id=peppol_id,
            missing_fields=["EINVOICEBE_API_KEY"] if not api_key else [],
            mode="disabled",
            message=CONFIGURATION_GUIDANCE,
        )

    if missing:
        return EInvoiceBEConfigurationStatus(
            enabled=True,
            configured=False,
            api_base_url=base_url,
            sandbox_company_number=company_number,
            sandbox_peppol_id=peppol_id,
            missing_fields=missing,
            mode="missing_credentials",
            message=CONFIGURATION_GUIDANCE,
        )

    return EInvoiceBEConfigurationStatus(
        enabled=True,
        configured=True,
        api_base_url=base_url,
        sandbox_company_number=company_number,
        sandbox_peppol_id=peppol_id,
        missing_fields=[],
        mode="sandbox_validation",
        message="e-invoice.be sandbox validation is configured.",
    )


def load_einvoicebe_config() -> EInvoiceBEConfig:
    status = load_einvoicebe_configuration_status()
    if not status.configured:
        raise EInvoiceBEConfigurationError(status.message)

    return EInvoiceBEConfig(
        enabled=True,
        api_base_url=status.api_base_url,
        api_key=os.environ["EINVOICEBE_API_KEY"].strip(),
        sandbox_company_number=status.sandbox_company_number,
        sandbox_peppol_id=status.sandbox_peppol_id,
    )


def submit_ubl_validation(
    *,
    config: EInvoiceBEConfig,
    xml_bytes: bytes,
    filename: str,
) -> EInvoiceBEValidationResponse:
    headers = {"Authorization": f"Bearer {config.api_key}"}
    files = {"file": (filename, xml_bytes, "application/xml")}

    with httpx.Client(timeout=45) as client:
        response = client.post(config.validation_url, headers=headers, files=files)

    return _response_to_validation(response, filename)


def submit_ubl_sandbox_send(
    *,
    config: EInvoiceBEConfig,
    xml_bytes: bytes,
    filename: str,
    sender_peppol_id: str | None = None,
    receiver_peppol_id: str | None = None,
) -> EInvoiceBESandboxSendResponse:
    headers = {"Authorization": f"Bearer {config.api_key}"}
    files = {"file": (filename, xml_bytes, "application/xml")}

    with httpx.Client(timeout=60) as client:
        create_response = client.post(config.document_ubl_url, headers=headers, files=files)
        created_document = _response_to_document(create_response)
        if create_response.status_code != 201 or not created_document.id:
            return EInvoiceBESandboxSendResponse(
                document_id=created_document.id,
                provider_reference=created_document.id,
                status="failed",
                message=_provider_message(created_document.raw_response, "e-invoice.be document creation failed."),
                create_http_status_code=create_response.status_code,
                provider_document_state=created_document.state,
                create_response=created_document.raw_response,
            )

        params = _send_query_parameters(sender_peppol_id, receiver_peppol_id)
        send_response = client.post(
            config.document_send_url(created_document.id),
            headers=headers,
            params=params,
        )
        sent_document = _response_to_document(send_response)

    if send_response.status_code == 200:
        return EInvoiceBESandboxSendResponse(
            document_id=sent_document.id or created_document.id,
            provider_reference=sent_document.id or created_document.id,
            status="submitted",
            message="Sandbox send submitted to e-invoice.be.",
            create_http_status_code=create_response.status_code,
            send_http_status_code=send_response.status_code,
            provider_document_state=sent_document.state,
            create_response=created_document.raw_response,
            send_response=sent_document.raw_response,
        )

    return EInvoiceBESandboxSendResponse(
        document_id=sent_document.id or created_document.id,
        provider_reference=sent_document.id or created_document.id,
        status="failed",
        message=_provider_message(sent_document.raw_response, f"e-invoice.be sandbox send failed with HTTP {send_response.status_code}."),
        create_http_status_code=create_response.status_code,
        send_http_status_code=send_response.status_code,
        provider_document_state=sent_document.state,
        create_response=created_document.raw_response,
        send_response=sent_document.raw_response,
    )


def _response_to_validation(response: httpx.Response, filename: str) -> EInvoiceBEValidationResponse:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.status_code == 201:
        return EInvoiceBEValidationResponse(
            **payload,
            http_status_code=response.status_code,
            raw_response=payload,
        )

    detail = str(payload.get("detail") or f"e-invoice.be validation failed with HTTP {response.status_code}.")
    return EInvoiceBEValidationResponse(
        id="",
        file_name=filename,
        is_valid=False,
        issues=[
            EInvoiceBEValidationIssue(
                message=detail,
                type="error",
                schematron="http_error",
            )
        ],
        http_status_code=response.status_code,
        raw_response=payload,
    )


def _response_to_document(response: httpx.Response) -> EInvoiceBEDocumentResponse:
    try:
        parsed: Any = response.json()
    except ValueError:
        parsed = {"detail": response.text}
    payload: dict[str, Any] = parsed if isinstance(parsed, dict) else {"detail": parsed}

    return EInvoiceBEDocumentResponse(
        id=payload.get("id"),
        state=payload.get("state"),
        document_type=payload.get("document_type"),
        direction=payload.get("direction"),
        invoice_id=payload.get("invoice_id"),
        customer_name=payload.get("customer_name"),
        http_status_code=response.status_code,
        raw_response=payload,
    )


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


def _provider_message(payload: dict[str, Any] | None, fallback: str) -> str:
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    return fallback


def _env_bool(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


class EInvoiceBEConfigurationError(ValueError):
    pass
