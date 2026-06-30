"""Evidence bundle metadata helpers for offline V1 outputs."""

from __future__ import annotations

import os
from typing import Any

from app.integrations.einvoicebe.client import DEFAULT_SANDBOX_PEPPOL_ID
from app.integrations.einvoicebe.diagnostics import build_sender_identity_check
from app.models.country_pack import CountryPack
from app.models.upload import UploadRecord
from app.storage.file_store import storage_path_from_relative


UK_SANDBOX_WORDING = (
    "UK Peppol sandbox test only. This tests Peppol-style invoice readiness through a sandbox provider. "
    "It does not prove final UK 2029 statutory compliance."
)
EINVOICEBE_NOT_RUN = "External e-invoice.be validation not run."
EINVOICEBE_SEND_NOT_RUN = "External e-invoice.be sandbox send not run."
EINVOICEBE_SANDBOX_IDENTITY_LIMITATION = (
    "The e-invoice.be sandbox send flow currently reaches the provider and captures the provider response, "
    "but successful sandbox send is blocked by a sandbox tenant Peppol ID mismatch. External validation passes; "
    "send completion is parked pending provider clarification."
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
        "xml_generation_for_validation": _xml_generation_for_validation_metadata(record),
        "xml_validation": _xml_validation_metadata(record),
        "official_xml_validator_status": _official_xml_validator_status(record),
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
        "external_validation": _external_validation_metadata(record),
        "external_sandbox_send": _external_sandbox_send_metadata(record),
        "sandbox_sender_identity_check": _sandbox_sender_identity_check(record),
        "known_limitations": _known_limitations(record),
        "v1_boundary": country_pack.v1_boundary,
    }


def _external_validation_metadata(record: UploadRecord) -> dict[str, Any]:
    if record.external_validation:
        return record.external_validation.model_dump(mode="json")
    if record.selected_country_pack == "belgium_peppol":
        return {
            "provider": "e-invoice.be",
            "status": "not_run",
            "message": EINVOICEBE_NOT_RUN,
            "disclaimer": "External sandbox validation only. This does not prove Peppol delivery or final statutory compliance.",
        }
    return {"status": "not_applicable"}


def _xml_validation_metadata(record: UploadRecord) -> dict[str, Any]:
    if record.xml_validation_report:
        return record.xml_validation_report.model_dump(mode="json")
    if record.selected_country_pack == "belgium_peppol":
        if record.validation_report.summary.blocking_errors > 0:
            return {
                "overall_status": "skipped",
                "message": "Belgium XML validation skipped because internal validation has blocking errors.",
            }
        return {
            "overall_status": "not_run",
            "message": "Belgium XML validation has not run.",
        }
    return {"overall_status": "not_applicable"}


def _official_xml_validator_status(record: UploadRecord) -> dict[str, Any]:
    if record.selected_country_pack != "belgium_peppol":
        return {"status": "not_applicable"}
    official_results = []
    if record.xml_validation_report:
        official_results = [
            result.model_dump(mode="json")
            for result in record.xml_validation_report.results
            if result.validator_type in {"ubl_xsd", "en16931", "peppol_schematron"}
        ]
    if official_results:
        return {
            "status": "not_configured",
            "validators": official_results,
            "note": "Full EN16931/Peppol Schematron validation is not yet configured. Official validator not configured in this milestone.",
        }
    return {
        "status": "not_configured",
        "note": "Official validator not configured in this milestone.",
    }


def _external_sandbox_send_metadata(record: UploadRecord) -> dict[str, Any]:
    if record.external_sandbox_send:
        metadata = record.external_sandbox_send.model_dump(mode="json")
        metadata["attempted"] = True
        if record.external_sandbox_send.status == "failed":
            metadata["provider_error_message"] = (
                record.external_sandbox_send.messages[-1]
                if record.external_sandbox_send.messages
                else "External e-invoice.be sandbox send failed."
            )
        if _einvoicebe_identity_limitation_applies(record):
            metadata["known_limitation"] = EINVOICEBE_SANDBOX_IDENTITY_LIMITATION
        return metadata
    if record.selected_country_pack == "belgium_peppol":
        return {
            "provider": "e-invoice.be",
            "status": "not_run",
            "attempted": False,
            "message": EINVOICEBE_SEND_NOT_RUN,
            "disclaimer": "Sandbox send only. This does not prove Peppol delivery, recipient acceptance or final statutory compliance.",
            "peppol_delivery": "not_claimed",
            "recipient_acceptance": "not_claimed",
            "smp_registration_claim": "not_claimed",
        }
    return {"status": "not_applicable"}


def _known_limitations(record: UploadRecord) -> list[str]:
    limitations: list[str] = []
    if _einvoicebe_identity_limitation_applies(record):
        limitations.append(EINVOICEBE_SANDBOX_IDENTITY_LIMITATION)
    return limitations


def _einvoicebe_identity_limitation_applies(record: UploadRecord) -> bool:
    send = record.external_sandbox_send
    if record.selected_country_pack != "belgium_peppol" or not send:
        return False
    messages = " ".join(send.messages).lower()
    if "tenant does not own the sender peppol id" in messages:
        return True
    sender_check = send.sender_identity_check or {}
    return send.status == "failed" and sender_check.get("xml_sender_matches_tenant") is False


def _sandbox_sender_identity_check(record: UploadRecord) -> dict[str, Any] | None:
    if record.selected_country_pack != "belgium_peppol":
        return None
    tenant_peppol_id = os.getenv("EINVOICEBE_SANDBOX_PEPPOL_ID", DEFAULT_SANDBOX_PEPPOL_ID).strip() or DEFAULT_SANDBOX_PEPPOL_ID
    if record.external_sandbox_send and record.external_sandbox_send.sender_identity_check:
        return record.external_sandbox_send.sender_identity_check
    if not record.generated_xml_path:
        return {
            "tenant_owned_sender_peppol_id": tenant_peppol_id,
            "status": "not_available",
            "message": "Belgium XML has not been generated for sender identity diagnostics.",
        }
    try:
        xml_bytes = storage_path_from_relative(record.generated_xml_path).read_bytes()
    except OSError:
        return {
            "tenant_owned_sender_peppol_id": tenant_peppol_id,
            "status": "not_available",
            "message": "Generated Belgium XML could not be read for sender identity diagnostics.",
        }
    return build_sender_identity_check(
        tenant_peppol_id=tenant_peppol_id,
        xml_bytes=xml_bytes,
        send_request_sender_peppol_id=None,
    )


def _xml_generation_for_validation_metadata(record: UploadRecord) -> dict[str, Any]:
    if record.selected_country_pack != "belgium_peppol":
        return {"status": "not_applicable"}
    if record.generated_xml_path:
        return {
            "status": "generated",
            "filename": "invoice.xml",
            "sha256": record.generated_xml_sha256_hash,
            "note": "Belgium UBL XML was generated from canonical invoice JSON for validation/output evidence.",
        }
    if record.validation_report.summary.blocking_errors > 0:
        return {
            "status": "skipped",
            "note": "Belgium XML generation for validation was skipped because internal validation has blocking errors.",
        }
    return {
        "status": "not_run",
        "note": "Belgium XML generation for validation has not run.",
    }
