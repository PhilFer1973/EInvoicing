from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[3]

ValidatorMode = Literal["external_xslt", "svrl_fixture"]


class SchematronValidatorConfig(BaseModel):
    validator_name: str
    validator_type: str
    artefact_path: str
    mode: ValidatorMode = "external_xslt"
    engine_command: str | None = None
    artefact_version: str | None = None
    raw_report_filename: str

    @property
    def resolved_artefact_path(self) -> Path:
        path = Path(self.artefact_path)
        if path.is_absolute():
            return path
        return (REPO_ROOT / path).resolve()


def load_belgium_schematron_validator_configs() -> list[SchematronValidatorConfig]:
    return [
        SchematronValidatorConfig(
            validator_name="EN16931 validation",
            validator_type="en16931",
            artefact_path=os.getenv(
                "EINVOICING_EN16931_VALIDATOR_ARTEFACT",
                "validators/belgium_peppol/en16931/CEN-EN16931-UBL.xslt",
            ),
            mode=_validator_mode("EINVOICING_EN16931_VALIDATOR_MODE"),
            engine_command=os.getenv("EINVOICING_SCHEMATRON_ENGINE_COMMAND") or None,
            artefact_version=os.getenv("EINVOICING_EN16931_VALIDATOR_VERSION") or None,
            raw_report_filename="en16931_validation_raw.svrl",
        ),
        SchematronValidatorConfig(
            validator_name="Peppol Schematron validation",
            validator_type="peppol_schematron",
            artefact_path=os.getenv(
                "EINVOICING_PEPPOL_VALIDATOR_ARTEFACT",
                "validators/belgium_peppol/peppol/PEPPOL-EN16931-UBL.xslt",
            ),
            mode=_validator_mode("EINVOICING_PEPPOL_VALIDATOR_MODE"),
            engine_command=os.getenv("EINVOICING_SCHEMATRON_ENGINE_COMMAND") or None,
            artefact_version=os.getenv("EINVOICING_PEPPOL_VALIDATOR_VERSION") or None,
            raw_report_filename="peppol_schematron_validation_raw.svrl",
        ),
    ]


def _validator_mode(env_name: str) -> ValidatorMode:
    value = os.getenv(env_name, "external_xslt").strip()
    if value == "svrl_fixture":
        return "svrl_fixture"
    return "external_xslt"

