from __future__ import annotations

from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from app.validation.peppol_readiness import validate_basic_ubl_structure, validate_peppol_readiness
from app.validation.xml_models import XMLValidationMessage, XMLValidationReport, XMLValidatorResult


OFFICIAL_VALIDATOR_NOT_CONFIGURED_MESSAGE = "Official validator not configured in this milestone."


def validate_belgium_invoice_xml(xml_bytes: bytes) -> XMLValidationReport:
    executed_at = _now()
    results: list[XMLValidatorResult] = []
    well_formedness = validate_xml_well_formedness(xml_bytes)
    results.append(well_formedness)

    if well_formedness.status == "failed":
        results.append(_skipped_result("Basic UBL invoice structure checks", "ubl_structure", "Skipped because XML is not well-formed."))
        results.append(_skipped_result("Peppol readiness checks", "peppol_readiness", "Skipped because XML is not well-formed."))
    else:
        root = ET.fromstring(xml_bytes)
        results.append(validate_basic_ubl_structure(root))
        results.append(validate_peppol_readiness(root))

    results.extend(official_validator_statuses())
    return XMLValidationReport(
        overall_status=_overall_status(results),
        executed_at=executed_at,
        results=results,
    )


def validate_xml_well_formedness(xml_bytes: bytes) -> XMLValidatorResult:
    try:
        ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        line, column = exc.position
        return XMLValidatorResult(
            validator_name="XML well-formedness",
            validator_type="xml_well_formedness",
            status="failed",
            errors=[
                XMLValidationMessage(
                    code="XML-WELLFORMED-001",
                    message="Generated XML is not well-formed.",
                    line=line,
                    column=column,
                    detail=str(exc),
                )
            ],
            executed_at=_now(),
            artefact_version="Python xml.etree.ElementTree",
        )

    return XMLValidatorResult(
        validator_name="XML well-formedness",
        validator_type="xml_well_formedness",
        status="passed",
        informational_messages=["Generated XML is well-formed."],
        executed_at=_now(),
        artefact_version="Python xml.etree.ElementTree",
    )


def official_validator_statuses() -> list[XMLValidatorResult]:
    return [
        _not_configured_result("UBL XSD validation", "ubl_xsd"),
        _not_configured_result("EN16931 validation", "en16931"),
        _not_configured_result("Peppol Schematron validation", "peppol_schematron"),
    ]


def _skipped_result(validator_name: str, validator_type: str, message: str) -> XMLValidatorResult:
    return XMLValidatorResult(
        validator_name=validator_name,
        validator_type=validator_type,
        status="skipped",
        informational_messages=[message],
        executed_at=_now(),
        artefact_version="Milestone 6A local readiness checks",
    )


def _not_configured_result(validator_name: str, validator_type: str) -> XMLValidatorResult:
    return XMLValidatorResult(
        validator_name=validator_name,
        validator_type=validator_type,
        status="not_configured",
        informational_messages=[OFFICIAL_VALIDATOR_NOT_CONFIGURED_MESSAGE],
        executed_at=_now(),
    )


def _overall_status(results: list[XMLValidatorResult]) -> str:
    if any(result.status == "failed" for result in results):
        return "failed"
    if any(result.status == "warning" for result in results):
        return "warning"
    return "passed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

