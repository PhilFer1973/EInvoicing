from __future__ import annotations

from app.models.country_pack import CountryPack
from app.models.validation import ValidationReport, ValidationResult, ValidationSummary


def build_validation_report(results: list[ValidationResult]) -> ValidationReport:
    blocking_errors = sum(1 for result in results if result.severity == "error" and result.status == "failed")
    ack_warnings = sum(
        1 for result in results if result.severity == "warning_ack_required" and result.status == "failed"
    )
    warnings = sum(1 for result in results if result.severity == "warning" and result.status == "failed")
    passed = sum(1 for result in results if result.status == "passed")

    if blocking_errors:
        overall_status = "failed"
        internal_status = "failed"
    elif ack_warnings or warnings:
        overall_status = "passed_with_warnings"
        internal_status = "passed_with_warnings"
    else:
        overall_status = "passed"
        internal_status = "passed"

    return ValidationReport(
        summary=ValidationSummary(
            overall_status=overall_status,
            internal_validation=internal_status,
            official_artefact_validation="not_configured",
            blocking_errors=blocking_errors,
            warnings_ack_required=ack_warnings,
            warnings=warnings,
            passed_checks=passed,
        ),
        results=results,
    )


def boundary_results_for_pack(pack: CountryPack) -> list[ValidationResult]:
    return []
