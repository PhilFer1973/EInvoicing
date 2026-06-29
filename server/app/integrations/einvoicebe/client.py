from __future__ import annotations

import os
from typing import Any

import httpx

from app.integrations.einvoicebe.schemas import (
    EInvoiceBEConfig,
    EInvoiceBEConfigurationStatus,
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


def _env_bool(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


class EInvoiceBEConfigurationError(ValueError):
    pass

