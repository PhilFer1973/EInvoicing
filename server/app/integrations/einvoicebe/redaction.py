from __future__ import annotations

from typing import Any


def redact_einvoicebe_secrets(payload: Any, api_key: str | None = None) -> Any:
    if isinstance(payload, dict):
        return {
            key: "[REDACTED]" if _secret_key(key) else redact_einvoicebe_secrets(value, api_key)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_einvoicebe_secrets(item, api_key) for item in payload]
    if isinstance(payload, str) and api_key:
        return payload.replace(api_key, "[REDACTED]")
    return payload


def _secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("api_key", "authorization", "secret", "token"))

