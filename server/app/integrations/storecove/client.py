from __future__ import annotations

import os
from typing import Any

from app.integrations.storecove.schemas import (
    StorecoveConfig,
    StorecoveConfigurationStatus,
    StorecoveSandboxRequest,
    StorecoveSandboxResponse,
    StorecoveSandboxStatus,
    UK_SANDBOX_WORDING,
)


CONFIGURATION_GUIDANCE = "Storecove sandbox is not configured. Add sandbox credentials to enable UK Peppol testing."
PRODUCTION_REJECTED_MESSAGE = "Production Storecove endpoints are rejected in Milestone 5A. Use a sandbox base URL."


def load_storecove_configuration_status() -> StorecoveConfigurationStatus:
    enabled = _env_bool("STORECOVE_SANDBOX_ENABLED")
    base_url = os.getenv("STORECOVE_API_BASE_URL", "").strip()
    values = {
        "STORECOVE_API_BASE_URL": base_url,
        "STORECOVE_API_KEY": os.getenv("STORECOVE_API_KEY", "").strip(),
        "STORECOVE_SENDER_LEGAL_ENTITY_ID": os.getenv("STORECOVE_SENDER_LEGAL_ENTITY_ID", "").strip(),
        "STORECOVE_RECEIVER_LEGAL_ENTITY_ID": os.getenv("STORECOVE_RECEIVER_LEGAL_ENTITY_ID", "").strip(),
    }
    missing = [name for name, value in values.items() if not value]

    if not enabled:
        return StorecoveConfigurationStatus(
            sandbox_enabled=False,
            configured=False,
            api_base_url=base_url or None,
            missing_fields=missing,
            mode="disabled",
            message=CONFIGURATION_GUIDANCE,
        )

    if base_url and _is_production_endpoint(base_url):
        return StorecoveConfigurationStatus(
            sandbox_enabled=True,
            configured=False,
            api_base_url=redact_secret(base_url, values["STORECOVE_API_KEY"]),
            missing_fields=missing,
            mode="configuration_error",
            message=PRODUCTION_REJECTED_MESSAGE,
        )

    if missing:
        return StorecoveConfigurationStatus(
            sandbox_enabled=True,
            configured=False,
            api_base_url=base_url or None,
            missing_fields=missing,
            mode="missing_credentials",
            message=CONFIGURATION_GUIDANCE,
        )

    return StorecoveConfigurationStatus(
        sandbox_enabled=True,
        configured=True,
        api_base_url=redact_secret(base_url, values["STORECOVE_API_KEY"]),
        missing_fields=[],
        mode="mocked_sandbox",
        message="Storecove sandbox scaffold is configured for mocked Milestone 5A testing. No live API call will be made.",
    )


def load_storecove_config() -> StorecoveConfig:
    status = load_storecove_configuration_status()
    if not status.configured:
        raise StorecoveConfigurationError(status.message)

    return StorecoveConfig(
        sandbox_enabled=True,
        api_base_url=os.environ["STORECOVE_API_BASE_URL"].strip(),
        api_key=os.environ["STORECOVE_API_KEY"].strip(),
        sender_legal_entity_id=os.environ["STORECOVE_SENDER_LEGAL_ENTITY_ID"].strip(),
        receiver_legal_entity_id=os.environ["STORECOVE_RECEIVER_LEGAL_ENTITY_ID"].strip(),
    )


def submit_storecove_sandbox_mock(
    request: StorecoveSandboxRequest,
) -> tuple[StorecoveSandboxResponse, StorecoveSandboxStatus]:
    provider_reference = f"MOCK-STORECOVE-{request.external_id}"
    response = StorecoveSandboxResponse(
        status="accepted_mocked",
        provider_reference=provider_reference,
    )
    status = StorecoveSandboxStatus(
        provider_reference=provider_reference,
        status="accepted_mocked",
    )
    return response, status


def build_storecove_evidence_object(
    request: StorecoveSandboxRequest,
    response: StorecoveSandboxResponse,
    status: StorecoveSandboxStatus,
    api_key: str,
) -> dict[str, Any]:
    return {
        "sandbox_only": True,
        "mocked": response.mocked,
        "disclaimer": UK_SANDBOX_WORDING,
        "request": redact_secrets(request.model_dump(mode="json"), api_key),
        "response": response.model_dump(mode="json"),
        "status": status.model_dump(mode="json"),
    }


def redact_secrets(payload: Any, api_key: str | None = None) -> Any:
    if isinstance(payload, dict):
        return {
            key: "[REDACTED]" if _secret_key(key) else redact_secrets(value, api_key)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_secrets(item, api_key) for item in payload]
    if isinstance(payload, str):
        return redact_secret(payload, api_key)
    return payload


def redact_secret(value: str, api_key: str | None = None) -> str:
    if api_key and api_key in value:
        return value.replace(api_key, "[REDACTED]")
    return value


def _env_bool(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("api_key", "secret", "token", "authorization"))


def _is_production_endpoint(base_url: str) -> bool:
    lowered = base_url.lower()
    return "storecove" in lowered and "sandbox" not in lowered


class StorecoveConfigurationError(ValueError):
    pass

