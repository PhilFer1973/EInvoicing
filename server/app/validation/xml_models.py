from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


XMLValidationStatus = Literal["passed", "failed", "warning", "skipped", "not_configured"]


class XMLValidationMessage(BaseModel):
    code: str
    message: str
    location: str | None = None
    line: int | None = None
    column: int | None = None
    detail: str | None = None


class XMLValidatorResult(BaseModel):
    validator_name: str
    validator_type: str
    status: XMLValidationStatus
    errors: list[XMLValidationMessage] = Field(default_factory=list)
    warnings: list[XMLValidationMessage] = Field(default_factory=list)
    informational_messages: list[str] = Field(default_factory=list)
    executed_at: str
    artefact_version: str | None = None
    raw_output_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class XMLValidationReport(BaseModel):
    overall_status: Literal["passed", "failed", "warning"]
    executed_at: str
    results: list[XMLValidatorResult] = Field(default_factory=list)

