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
    if pack.country_pack_id == "saudi_zatca":
        return [
            ValidationResult(
                rule_id="SA-V1-BOUNDARY-001",
                layer="country_boundary",
                severity="warning_ack_required",
                status="failed",
                message="This file has not been submitted to ZATCA/FATOORA and is not a cleared Saudi tax invoice.",
                field_path="invoice.selected_country_pack",
                country_pack_id=pack.country_pack_id,
                country_pack_version=pack.pack_version,
                corrective_action="Acknowledge this warning before ZIP export in a later milestone.",
            ),
            ValidationResult(
                rule_id="SA-V1-BOUNDARY-002",
                layer="country_boundary",
                severity="warning_ack_required",
                status="failed",
                message="No ZATCA clearance stamp or production cryptographic stamp has been applied.",
                field_path="metadata.security_boundary",
                country_pack_id=pack.country_pack_id,
                country_pack_version=pack.pack_version,
                corrective_action="Use this output only as an offline workbench artefact.",
            ),
        ]
    return []
