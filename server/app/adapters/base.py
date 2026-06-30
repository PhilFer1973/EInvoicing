from __future__ import annotations

from app.models.canonical import CanonicalInvoice
from app.models.country_pack import CountryPack
from app.models.upload import EvidenceBundlePreview, EvidenceFile
from app.models.validation import ValidationResult


class CountryAdapter:
    def __init__(self, pack: CountryPack) -> None:
        self.pack = pack

    def get_pack_manifest(self) -> CountryPack:
        return self.pack

    def get_output_profiles(self) -> list[str]:
        return self.pack.output_profiles

    def preflight_validate(self, canonical_invoice: CanonicalInvoice | None) -> list[ValidationResult]:
        if self.pack.support_level == "info_only":
            return [
                ValidationResult(
                    rule_id="PACK-INFO-ONLY",
                    layer="country_preflight",
                    severity="error",
                    status="failed",
                    message="This country pack is information-only in V1 and cannot generate outputs.",
                    field_path="invoice.selected_country_pack",
                    country_pack_id=self.pack.country_pack_id,
                    country_pack_version=self.pack.pack_version,
                    corrective_action="Select a generator country pack before requesting output generation.",
                )
            ]
        return []

    def build_output_placeholder(self, canonical_invoice: CanonicalInvoice | None) -> EvidenceBundlePreview:
        files = [
            EvidenceFile(filename="canonical_invoice.json", status="preview_available" if canonical_invoice else "pending"),
            EvidenceFile(filename="validation_report.json", status="preview_available"),
            EvidenceFile(filename="evidence.json", status="preview_available"),
            EvidenceFile(filename="source_upload_snapshot.xlsx", status="pending_storage"),
            EvidenceFile(filename="country_pack_manifest.json", status="preview_available"),
            EvidenceFile(filename="hashes.txt", status="pending_generation"),
        ]
        if self.pack.country_pack_id in {"belgium_peppol", "saudi_zatca"}:
            files.insert(0, EvidenceFile(filename="invoice.xml", status="pending_generation"))
        if self.pack.country_pack_id == "belgium_peppol":
            files.extend(
                [
                    EvidenceFile(filename="xml_validation_report.json", status="pending_xml_validation"),
                    EvidenceFile(filename="einvoicebe_validation_request.json", status="pending_external_validation"),
                    EvidenceFile(filename="einvoicebe_validation_response.json", status="pending_external_validation"),
                    EvidenceFile(filename="external_validation_status.json", status="pending_external_validation"),
                    EvidenceFile(filename="einvoicebe_send_request.json", status="pending_sandbox_send"),
                    EvidenceFile(filename="einvoicebe_send_response.json", status="pending_sandbox_send"),
                    EvidenceFile(filename="external_sandbox_send_status.json", status="pending_sandbox_send"),
                    EvidenceFile(filename="einvoicebe_send_provider_reference.txt", status="pending_sandbox_send"),
                ]
            )
        if self.pack.requires_pdf:
            files.insert(1, EvidenceFile(filename="saudi_visual_invoice.pdf", status="pending_generation"))
        if self.pack.requires_qr:
            files.insert(2, EvidenceFile(filename="qr.png", status="pending_generation"))
            files.insert(3, EvidenceFile(filename="qr_payload_base64.txt", status="pending_generation"))
            files.insert(4, EvidenceFile(filename="qr_payload_decoded.json", status="pending_generation"))
        if self.pack.country_pack_id == "uk_info":
            files.extend(
                [
                    EvidenceFile(filename="storecove_request.json", status="pending_sandbox_test"),
                    EvidenceFile(filename="storecove_response.json", status="pending_sandbox_test"),
                    EvidenceFile(filename="storecove_status.json", status="pending_sandbox_test"),
                    EvidenceFile(filename="provider_reference.txt", status="pending_sandbox_test"),
                    EvidenceFile(filename="README_sandbox_only.txt", status="preview_available"),
                ]
            )

        return EvidenceBundlePreview(
            generation_id="GEN-PREVIEW",
            country_pack_id=self.pack.country_pack_id,
            country_pack_version=self.pack.pack_version,
            output_profile_id=self.pack.default_output_profile,
            status="skeleton_only_milestone_1",
            files=files,
            v1_boundary=self.pack.v1_boundary,
        )

    def generate_output(self, canonical_invoice: CanonicalInvoice) -> None:
        raise NotImplementedError("Country output generation is outside Milestone 1.")
