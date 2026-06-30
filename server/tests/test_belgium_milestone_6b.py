from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app
from app.models.canonical import CanonicalInvoice
from app.services.ubl_xml import generate_belgium_ubl_invoice_xml
from app.validation.schematron_runner import parse_svrl_output, run_schematron_validator
from app.validation.validator_config import SchematronValidatorConfig
from app.validation.xml_validator import run_belgium_xml_validation
from tests.workbook_fixtures import belgium_valid_workbook_bytes


pytestmark = pytest.mark.anyio

SVRL_PASS = b"""<?xml version="1.0" encoding="UTF-8"?>
<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
  <svrl:active-pattern id="test"/>
</svrl:schematron-output>
"""

SVRL_FAIL = b"""<?xml version="1.0" encoding="UTF-8"?>
<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
  <svrl:failed-assert id="BR-CL-01" location="/Invoice" test="cbc:ID">
    <svrl:text>Invoice failed the configured official validation fixture.</svrl:text>
  </svrl:failed-assert>
</svrl:schematron-output>
"""


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as api_client:
        yield api_client


async def test_en16931_and_peppol_validators_are_not_configured_by_default(client: AsyncClient) -> None:
    payload = await _upload_belgium_workbook(client)
    report = run_belgium_xml_validation(_xml_for_payload(payload)).report

    statuses = {result.validator_type: result for result in report.results}
    assert statuses["en16931"].status == "not_configured"
    assert statuses["en16931"].validator_executed is False
    assert statuses["peppol_schematron"].status == "not_configured"
    assert statuses["peppol_schematron"].validator_executed is False
    assert statuses["en16931"].informational_messages == ["Official validator artefact not configured."]


async def test_configured_validator_success_returns_passed(client: AsyncClient, tmp_path: Path) -> None:
    payload = await _upload_belgium_workbook(client)
    svrl_path = _write_svrl(tmp_path, "passed.svrl", SVRL_PASS)

    execution = run_schematron_validator(_xml_for_payload(payload), _fixture_config("EN16931 validation", "en16931", svrl_path))

    assert execution.result.status == "passed"
    assert execution.result.validator_executed is True
    assert execution.result.informational_messages == ["EN16931 validation passed."]
    assert execution.raw_output is not None
    assert execution.raw_output.content == SVRL_PASS


async def test_configured_validator_failure_returns_failed_with_clear_messages(client: AsyncClient, tmp_path: Path) -> None:
    payload = await _upload_belgium_workbook(client)
    svrl_path = _write_svrl(tmp_path, "failed.svrl", SVRL_FAIL)

    execution = run_schematron_validator(_xml_for_payload(payload), _fixture_config("Peppol Schematron validation", "peppol_schematron", svrl_path))

    assert execution.result.status == "failed"
    assert execution.result.validator_executed is True
    assert execution.result.errors[0].code == "BR-CL-01"
    assert execution.result.errors[0].message == "Invoice failed the configured official validation fixture."
    assert execution.result.errors[0].location == "/Invoice"


def test_malformed_validator_output_fails_safely(tmp_path: Path) -> None:
    svrl_path = _write_svrl(tmp_path, "broken.svrl", b"<svrl:schematron-output>")

    execution = run_schematron_validator(b"<Invoice/>", _fixture_config("EN16931 validation", "en16931", svrl_path))

    assert execution.result.status == "failed"
    assert execution.result.validator_executed is False
    assert execution.result.errors[0].message == "Official validator execution failed."
    assert "not valid SVRL XML" in (execution.result.errors[0].detail or "")
    assert execution.raw_output is not None
    assert execution.raw_output.content == b"<svrl:schematron-output>"


def test_parse_svrl_output_preserves_warnings(tmp_path: Path) -> None:
    warning_svrl = b"""<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
  <svrl:successful-report id="BR-WARN" location="/Invoice"><svrl:text>Validator warning.</svrl:text></svrl:successful-report>
</svrl:schematron-output>"""
    result = parse_svrl_output(warning_svrl, _fixture_config("EN16931 validation", "en16931", _write_svrl(tmp_path, "warning.svrl", warning_svrl)))

    assert result.status == "warning"
    assert result.warnings[0].message == "Validator warning."


async def test_pipeline_evidence_includes_configured_validator_reports_and_raw_svrl(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_einvoicebe_env(monkeypatch)
    en16931_svrl = _write_svrl(tmp_path, "en16931_pass.svrl", SVRL_PASS)
    peppol_svrl = _write_svrl(tmp_path, "peppol_pass.svrl", SVRL_PASS)
    monkeypatch.setenv("EINVOICING_EN16931_VALIDATOR_MODE", "svrl_fixture")
    monkeypatch.setenv("EINVOICING_EN16931_VALIDATOR_ARTEFACT", str(en16931_svrl))
    monkeypatch.setenv("EINVOICING_EN16931_VALIDATOR_VERSION", "test-en16931-fixture")
    monkeypatch.setenv("EINVOICING_PEPPOL_VALIDATOR_MODE", "svrl_fixture")
    monkeypatch.setenv("EINVOICING_PEPPOL_VALIDATOR_ARTEFACT", str(peppol_svrl))
    monkeypatch.setenv("EINVOICING_PEPPOL_VALIDATOR_VERSION", "test-peppol-fixture")
    payload = await _upload_belgium_workbook(client)

    response = await client.post(f"/api/uploads/{payload['upload_id']}/validate-pipeline")

    assert response.status_code == 200
    record = response.json()
    statuses = {result["validator_type"]: result for result in record["xml_validation_report"]["results"]}
    assert statuses["en16931"]["status"] == "passed"
    assert statuses["en16931"]["validator_executed"] is True
    assert statuses["peppol_schematron"]["status"] == "passed"
    assert statuses["peppol_schematron"]["validator_executed"] is True

    bundle_response = await client.get(f"/api/uploads/{payload['upload_id']}/evidence-bundle/download")
    assert bundle_response.status_code == 200
    with ZipFile(BytesIO(bundle_response.content)) as archive:
        names = set(archive.namelist())
        assert "xml_validation_report.json" in names
        assert "en16931_validation_report.json" in names
        assert "peppol_schematron_validation_report.json" in names
        assert "en16931_validation_raw.svrl" in names
        assert "peppol_schematron_validation_raw.svrl" in names
        evidence = json.loads(archive.read("evidence_metadata.json"))
        assert evidence["official_xml_validator_status"]["en16931_validation_status"] == "passed"
        assert evidence["official_xml_validator_status"]["en16931_validation_ran"] is True
        assert evidence["official_xml_validator_status"]["peppol_schematron_validation_status"] == "passed"
        assert evidence["official_xml_validator_status"]["peppol_schematron_validation_ran"] is True
        assert evidence["official_xml_validator_status"]["ubl_xsd_validation_status"] == "not_configured"
        assert evidence["official_xml_validator_status"]["ubl_xsd_validation_ran"] is False
        assert "No Peppol delivery" in evidence["official_xml_validator_status"]["note"]


async def _upload_belgium_workbook(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/uploads",
        data={"selected_country_pack": "belgium_peppol"},
        files={
            "file": (
                "BE-VALID-001.xlsx",
                belgium_valid_workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _xml_for_payload(payload: dict) -> bytes:
    canonical = CanonicalInvoice.model_validate(payload["canonical_invoice"])
    return generate_belgium_ubl_invoice_xml(canonical)


def _fixture_config(name: str, validator_type: str, svrl_path: Path) -> SchematronValidatorConfig:
    return SchematronValidatorConfig(
        validator_name=name,
        validator_type=validator_type,
        artefact_path=str(svrl_path),
        mode="svrl_fixture",
        raw_report_filename=f"{validator_type}_raw.svrl",
    )


def _write_svrl(tmp_path: Path, filename: str, content: bytes) -> Path:
    path = tmp_path / filename
    path.write_bytes(content)
    return path


def _clear_einvoicebe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "EINVOICEBE_ENABLED",
        "EINVOICEBE_API_BASE_URL",
        "EINVOICEBE_API_KEY",
        "EINVOICEBE_SANDBOX_COMPANY_NUMBER",
        "EINVOICEBE_SANDBOX_PEPPOL_ID",
    ):
        monkeypatch.delenv(name, raising=False)

