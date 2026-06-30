from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import shlex
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from app.validation.validator_config import SchematronValidatorConfig
from app.validation.xml_models import XMLValidationMessage, XMLValidatorResult


SVRL_NS = "http://purl.oclc.org/dsdl/svrl"
NS = {"svrl": SVRL_NS}


@dataclass
class RawValidatorOutput:
    validator_type: str
    filename: str
    content: bytes


@dataclass
class SchematronExecution:
    result: XMLValidatorResult
    raw_output: RawValidatorOutput | None = None


def run_schematron_validator(xml_bytes: bytes, config: SchematronValidatorConfig) -> SchematronExecution:
    artefact_path = config.resolved_artefact_path
    if not artefact_path.exists():
        return SchematronExecution(_not_configured(config, "Official validator artefact not configured."))

    if config.mode == "svrl_fixture":
        raw_output = artefact_path.read_bytes()
        return _result_from_svrl(raw_output, config, artefact_path)

    if not config.engine_command:
        return SchematronExecution(_not_configured(config, "Official validator artefact configured but XSLT/Schematron engine is not configured."))

    return _run_external_validator(xml_bytes, config, artefact_path)


def parse_svrl_output(raw_output: bytes, config: SchematronValidatorConfig, artefact_path: Path | None = None) -> XMLValidatorResult:
    return _result_from_svrl(raw_output, config, artefact_path).result


def _run_external_validator(
    xml_bytes: bytes,
    config: SchematronValidatorConfig,
    artefact_path: Path,
) -> SchematronExecution:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        xml_path = temp_path / "invoice.xml"
        report_path = temp_path / "report.svrl"
        xml_path.write_bytes(xml_bytes)
        command = _build_command(config.engine_command or "", xml_path, artefact_path, report_path)
        try:
            completed = subprocess.run(command, capture_output=True, timeout=60, check=False)
        except FileNotFoundError:
            return SchematronExecution(_not_configured(config, "Official validator execution engine not available."))
        except subprocess.TimeoutExpired:
            return SchematronExecution(_execution_failed(config, "Official validator execution failed.", "Validator execution timed out."))

        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace") or completed.stdout.decode("utf-8", errors="replace")
            return SchematronExecution(_execution_failed(config, "Official validator execution failed.", detail.strip() or "Validator returned a non-zero exit code."))

        raw_output = report_path.read_bytes() if report_path.exists() else completed.stdout
        if not raw_output:
            return SchematronExecution(_execution_failed(config, "Official validator execution failed.", "Validator produced no SVRL output."))
        return _result_from_svrl(raw_output, config, artefact_path)


def _result_from_svrl(
    raw_output: bytes,
    config: SchematronValidatorConfig,
    artefact_path: Path | None,
) -> SchematronExecution:
    try:
        root = ET.fromstring(raw_output)
    except ET.ParseError as exc:
        line, column = exc.position
        result = _execution_failed(
            config,
            "Official validator execution failed.",
            f"Validator output was not valid SVRL XML: {exc}",
            line=line,
            column=column,
            artefact_path=artefact_path,
        )
        return SchematronExecution(result, RawValidatorOutput(config.validator_type, config.raw_report_filename, raw_output))

    failed_asserts = [
        _svrl_message(element, "SCH-FAILED-ASSERT")
        for element in root.findall(".//svrl:failed-assert", NS)
    ]
    warnings = [
        _svrl_message(element, "SCH-SUCCESSFUL-REPORT")
        for element in root.findall(".//svrl:successful-report", NS)
    ]

    status = "failed" if failed_asserts else "warning" if warnings else "passed"
    result = XMLValidatorResult(
        validator_name=config.validator_name,
        validator_type=config.validator_type,
        status=status,
        errors=failed_asserts,
        warnings=warnings,
        informational_messages=[f"{config.validator_name} passed."] if status == "passed" else [],
        executed_at=_now(),
        artefact_version=config.artefact_version,
        artefact_path=str(artefact_path) if artefact_path else None,
        validator_executed=True,
        metadata={"mode": config.mode, "raw_report_filename": config.raw_report_filename},
    )
    return SchematronExecution(result, RawValidatorOutput(config.validator_type, config.raw_report_filename, raw_output))


def _svrl_message(element: ET.Element, default_code: str) -> XMLValidationMessage:
    text = element.findtext("./svrl:text", namespaces=NS)
    return XMLValidationMessage(
        code=element.attrib.get("id") or element.attrib.get("flag") or default_code,
        message=(text or "Official validator reported an issue.").strip(),
        location=element.attrib.get("location"),
        detail=element.attrib.get("test"),
    )


def _build_command(command_template: str, xml_path: Path, artefact_path: Path, report_path: Path) -> list[str]:
    parts = shlex.split(command_template)
    replacements = {
        "{xml}": str(xml_path),
        "{artefact}": str(artefact_path),
        "{output}": str(report_path),
    }
    return [replacements.get(part, _replace_placeholders(part, replacements)) for part in parts]


def _replace_placeholders(value: str, replacements: dict[str, str]) -> str:
    for placeholder, replacement in replacements.items():
        value = value.replace(placeholder, replacement)
    return value


def _not_configured(config: SchematronValidatorConfig, message: str) -> XMLValidatorResult:
    return XMLValidatorResult(
        validator_name=config.validator_name,
        validator_type=config.validator_type,
        status="not_configured",
        informational_messages=[message],
        executed_at=_now(),
        artefact_version=config.artefact_version,
        artefact_path=str(config.resolved_artefact_path),
        validator_executed=False,
        metadata={"mode": config.mode},
    )


def _execution_failed(
    config: SchematronValidatorConfig,
    message: str,
    detail: str,
    *,
    line: int | None = None,
    column: int | None = None,
    artefact_path: Path | None = None,
) -> XMLValidatorResult:
    return XMLValidatorResult(
        validator_name=config.validator_name,
        validator_type=config.validator_type,
        status="failed",
        errors=[
            XMLValidationMessage(
                code="SCH-EXECUTION-001",
                message=message,
                line=line,
                column=column,
                detail=detail,
            )
        ],
        executed_at=_now(),
        artefact_version=config.artefact_version,
        artefact_path=str(artefact_path or config.resolved_artefact_path),
        validator_executed=False,
        metadata={"mode": config.mode},
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

