from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["error", "warning_ack_required", "warning", "info"]
ValidationStatus = Literal["passed", "failed", "not_configured", "acknowledged"]


class ValidationResult(BaseModel):
    rule_id: str
    layer: str
    severity: Severity
    status: ValidationStatus
    message: str
    field_path: str | None = None
    country_pack_id: str | None = None
    country_pack_version: str | None = None
    corrective_action: str | None = None
    technical_detail: str | None = None


class ValidationSummary(BaseModel):
    overall_status: Literal[
        "not_uploaded",
        "failed",
        "passed",
        "passed_with_warnings",
        "not_implemented_milestone_1",
    ]
    internal_validation: Literal["not_run", "failed", "passed", "passed_with_warnings"]
    official_artefact_validation: Literal["not_configured", "configuration_error", "passed", "failed"] = "not_configured"
    blocking_errors: int = 0
    warnings_ack_required: int = 0
    warnings: int = 0
    passed_checks: int = 0


class ValidationReport(BaseModel):
    summary: ValidationSummary
    results: list[ValidationResult] = Field(default_factory=list)

