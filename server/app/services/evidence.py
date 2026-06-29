"""Evidence bundle metadata helpers for offline V1 outputs."""

from __future__ import annotations

from typing import Any

from app.models.country_pack import CountryPack
from app.models.upload import UploadRecord


UK_SANDBOX_WORDING = (
    "UK Peppol sandbox test only. This tests Peppol-style invoice readiness through a sandbox provider. "
    "It does not prove final UK 2029 statutory compliance."
)


def official_validation_note(country_pack_id: str) -> str:
    """Return a deliberately conservative official validation statement."""
    if country_pack_id == "belgium_peppol":
        return (
            "Official artefact validation not configured. Generated only: no UBL XSD, "
            "EN 16931 or Peppol Schematron validation has run, and no Peppol "
            "transmission has occurred."
        )
    if country_pack_id == "saudi_zatca":
        return (
            "Official artefact validation not configured. Generated only: no ZATCA SDK "
            "validation, submission, clearance, reporting or production signing has occurred."
        )
    if country_pack_id == "uk_info":
        return (
            "Official artefact validation not configured. UK Peppol sandbox test only: no final UK 2029 "
            "statutory compliance validation, Peppol production transmission, HMRC submission or live "
            "acceptance has occurred."
        )
    return "Official artefact validation not configured. Generated only."


def build_evidence_metadata(record: UploadRecord, country_pack: CountryPack) -> dict[str, Any]:
    """Build a portable, explicit manifest for a locally generated evidence bundle."""
    report = record.validation_report
    acknowledgement_rules = [
        result.rule_id
        for result in report.results
        if result.severity == "warning_ack_required" and result.status == "failed"
    ]
    acknowledged_rules = record.acknowledged_warning_rule_ids
    acknowledgement_complete = bool(acknowledgement_rules) and all(
        rule_id in acknowledged_rules for rule_id in acknowledgement_rules
    )

    generated_outputs = [
        {
            "filename": evidence_file.filename,
            "status": evidence_file.status,
            "sha256": evidence_file.sha256,
        }
        for evidence_file in record.evidence_bundle_preview.files
        if evidence_file.status == "stored"
        and evidence_file.filename
        not in {
            "source_upload_snapshot.xlsx",
            "canonical_invoice.json",
            "validation_report.json",
            "country_pack_manifest.json",
            "hashes.txt",
        }
    ]

    return {
        "generated_at": record.generated_at,
        "selected_country_pack": record.selected_country_pack,
        "country_pack_version": country_pack.pack_version,
        "selected_output_profile": record.selected_output_profile,
        "source_workbook": {
            "filename": record.original_filename,
            "sha256": record.workbook_sha256_hash,
        },
        "validation": {
            "status": report.summary.overall_status,
            "internal_validation": "passed"
            if report.summary.blocking_errors == 0
            else "failed",
            "blocking_errors": report.summary.blocking_errors,
            "warnings": report.summary.warnings,
            "warnings_ack_required": report.summary.warnings_ack_required,
            "official_validator_status": report.summary.official_artefact_validation,
        },
        "generated_outputs": generated_outputs,
        "warning_acknowledgement": {
            "required_rule_ids": acknowledgement_rules,
            "acknowledged_rule_ids": acknowledged_rules,
            "acknowledged": acknowledgement_complete or not acknowledgement_rules,
            "acknowledged_at": record.warning_acknowledged_at,
        },
        "official_artefact_validation": {
            "status": report.summary.official_artefact_validation,
            "note": official_validation_note(record.selected_country_pack),
        },
        "storecove_sandbox": (
            {
                "sandbox_only": True,
                "mocked": record.storecove_mocked,
                "provider_reference": record.storecove_provider_reference,
                "status": record.storecove_submission_status,
                "disclaimer": UK_SANDBOX_WORDING,
            }
            if record.selected_country_pack == "uk_info"
            else None
        ),
        "v1_boundary": country_pack.v1_boundary,
    }
