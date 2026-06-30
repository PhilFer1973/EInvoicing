from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.integrations.einvoicebe.client import (
    EInvoiceBEConfigurationError,
    load_einvoicebe_config,
    load_einvoicebe_configuration_status,
    submit_ubl_sandbox_send,
    submit_ubl_validation,
)
from app.integrations.einvoicebe.diagnostics import build_sender_identity_check
from app.integrations.einvoicebe.mapper import (
    build_external_validation_status,
    build_sandbox_send_status,
    build_ubl_sandbox_send_request_evidence,
    build_ubl_validation_request_evidence,
)
from app.integrations.einvoicebe.redaction import redact_einvoicebe_secrets
from app.integrations.einvoicebe.schemas import (
    EINVOICEBE_SANDBOX_SEND_WORDING,
    EINVOICEBE_SANDBOX_WORDING,
    EInvoiceBEConfigurationStatus,
    EInvoiceBEExternalValidationStatus,
    EInvoiceBESandboxSendStatus,
)
from app.integrations.storecove.client import (
    StorecoveConfigurationError,
    build_storecove_evidence_object,
    load_storecove_config,
    load_storecove_configuration_status,
    redact_secrets,
    submit_storecove_sandbox_mock,
)
from app.integrations.storecove.mapper import map_canonical_to_storecove_request
from app.integrations.storecove.schemas import StorecoveConfigurationStatus, UK_SANDBOX_WORDING
from app.models.canonical import CanonicalInvoice
from app.models.upload import EvidenceBundlePreview, ExternalSandboxSendRecord, ExternalValidationRecord, UploadRecord
from app.models.validation import ValidationReport
from app.services.country_packs import CountryPackNotFound, get_country_pack
from app.services.evidence import build_evidence_metadata
from app.services.saudi_pdf import SaudiVisualPdfError, generate_saudi_visual_invoice_pdf
from app.services.saudi_qr import generate_saudi_phase_one_qr
from app.services.saudi_xml import generate_saudi_zatca_invoice_xml
from app.services.upload_store import get_upload, save_upload
from app.services.ubl_xml import generate_belgium_ubl_invoice_xml
from app.services.workbook import parse_workbook_upload
from app.storage.file_store import relative_storage_path, save_binary, save_json, storage_path_from_relative


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("", response_model=UploadRecord)
async def create_upload(
    selected_country_pack: str = Form(...),
    file: UploadFile = File(...),
) -> UploadRecord:
    try:
        pack = get_country_pack(selected_country_pack)
    except CountryPackNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    record = parse_workbook_upload(content, file.filename or "upload.xlsx", pack)
    return save_upload(record)


@router.get("/storecove-sandbox/configuration", response_model=StorecoveConfigurationStatus)
def read_storecove_sandbox_configuration() -> StorecoveConfigurationStatus:
    return load_storecove_configuration_status()


@router.get("/einvoicebe/configuration", response_model=EInvoiceBEConfigurationStatus)
def read_einvoicebe_configuration() -> EInvoiceBEConfigurationStatus:
    return load_einvoicebe_configuration_status()


@router.get("/{upload_id}", response_model=UploadRecord)
def read_upload(upload_id: str) -> UploadRecord:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record


@router.post("/{upload_id}/validate", response_model=ValidationReport)
def validate_upload(upload_id: str) -> ValidationReport:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if record.selected_country_pack == "belgium_peppol":
        record = save_upload(_run_belgium_validation_pipeline(record))
    return record.validation_report


@router.post("/{upload_id}/validate-pipeline", response_model=UploadRecord)
def validate_upload_pipeline(upload_id: str) -> UploadRecord:
    record = _require_upload(upload_id)
    if record.selected_country_pack == "belgium_peppol":
        record = _run_belgium_validation_pipeline(record)
    return save_upload(record)


@router.get("/{upload_id}/validation-results", response_model=ValidationReport)
def read_validation_results(upload_id: str) -> ValidationReport:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record.validation_report


@router.get("/{upload_id}/canonical-invoice", response_model=CanonicalInvoice)
def read_canonical_invoice(upload_id: str) -> CanonicalInvoice:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.canonical_invoice:
        raise HTTPException(status_code=404, detail="Canonical invoice JSON is not available for this upload.")
    return record.canonical_invoice


@router.get("/{upload_id}/canonical-invoice/download")
def download_canonical_invoice(upload_id: str) -> FileResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.canonical_json_path:
        raise HTTPException(status_code=404, detail="Canonical invoice JSON is not available for this upload.")
    path = storage_path_from_relative(record.canonical_json_path)
    return FileResponse(path, media_type="application/json", filename=f"{upload_id}_canonical_invoice.json")


@router.get("/{upload_id}/evidence-bundle/download")
def download_evidence_bundle(upload_id: str) -> StreamingResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.evidence_bundle_preview:
        raise HTTPException(status_code=404, detail="Evidence bundle skeleton is not available for this upload.")
    if record.status == "generated" and _requires_acknowledgement(record) and not _acknowledgement_complete(record):
        raise HTTPException(
            status_code=409,
            detail="Acknowledge the V1 boundary warnings before exporting this evidence bundle.",
        )

    pack = get_country_pack(record.selected_country_pack)
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        _write_stored_file(archive, "source_upload_snapshot.xlsx", record.stored_workbook_path)
        _write_stored_file(archive, "canonical_invoice.json", record.canonical_json_path)
        _write_stored_file(archive, "validation_report.json", record.validation_report_path)
        _write_stored_file(archive, "invoice.xml", record.generated_xml_path)
        _write_evidence_file(archive, record, "qr_payload_base64.txt")
        _write_evidence_file(archive, record, "qr_payload_decoded.json")
        _write_evidence_file(archive, record, "qr.png")
        _write_evidence_file(archive, record, "saudi_visual_invoice.pdf")
        _write_evidence_file(archive, record, "storecove_request.json")
        _write_evidence_file(archive, record, "storecove_response.json")
        _write_evidence_file(archive, record, "storecove_status.json")
        _write_evidence_file(archive, record, "provider_reference.txt")
        _write_evidence_file(archive, record, "einvoicebe_validation_request.json")
        _write_evidence_file(archive, record, "einvoicebe_validation_response.json")
        _write_evidence_file(archive, record, "external_validation_status.json")
        _write_evidence_file(archive, record, "einvoicebe_send_request.json")
        _write_evidence_file(archive, record, "einvoicebe_send_response.json")
        _write_evidence_file(archive, record, "external_sandbox_send_status.json")
        _write_evidence_file(archive, record, "einvoicebe_send_provider_reference.txt")
        if record.selected_country_pack == "uk_info":
            archive.writestr("README_sandbox_only.txt", _uk_sandbox_readme())
        metadata = build_evidence_metadata(record, pack)
        archive.writestr(
            "evidence.json",
            json.dumps(metadata, indent=2, sort_keys=True),
        )
        archive.writestr("evidence_metadata.json", json.dumps(metadata, indent=2, sort_keys=True))
        archive.writestr("country_pack_manifest.json", json.dumps(pack.model_dump(mode="json"), indent=2, sort_keys=True))
        archive.writestr("hashes.txt", _hash_manifest(record))

    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{upload_id}_evidence_bundle_skeleton.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@router.post("/{upload_id}/acknowledge-boundaries", response_model=UploadRecord)
def acknowledge_boundary_warnings(upload_id: str) -> UploadRecord:
    record = _require_upload(upload_id)
    required_rule_ids = _required_acknowledgement_rule_ids(record)
    if not required_rule_ids:
        return record

    record.acknowledged_warning_rule_ids = required_rule_ids
    record.warning_acknowledged_at = datetime.now(timezone.utc).isoformat()
    return save_upload(record)


@router.post("/{upload_id}/einvoicebe-validation", response_model=UploadRecord)
def validate_with_einvoicebe(upload_id: str) -> UploadRecord:
    record = _require_upload(upload_id)
    if record.selected_country_pack != "belgium_peppol":
        raise HTTPException(status_code=400, detail="e-invoice.be validation is available only for Belgium XML outputs.")
    if not record.generated_xml_path:
        raise HTTPException(status_code=409, detail="Generate Belgium XML before external e-invoice.be validation.")

    try:
        config = load_einvoicebe_config()
    except EInvoiceBEConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _run_einvoicebe_external_validation(record, config)
    record.evidence_bundle_preview.status = "belgium_xml_generated_einvoicebe_validated_milestone_5b"
    return save_upload(record)


@router.post("/{upload_id}/einvoicebe-sandbox-send", response_model=UploadRecord)
def send_to_einvoicebe_sandbox(upload_id: str) -> UploadRecord:
    record = _require_upload(upload_id)
    _ensure_einvoicebe_sandbox_send_allowed(record)

    try:
        config = load_einvoicebe_config()
    except EInvoiceBEConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _run_einvoicebe_sandbox_send(record, config)
    return save_upload(record)


@router.post("/{upload_id}/generate", response_model=EvidenceBundlePreview)
def generate_output(upload_id: str) -> EvidenceBundlePreview:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if record.selected_country_pack not in {"belgium_peppol", "saudi_zatca"}:
        raise HTTPException(
            status_code=400,
            detail="Generation is not configured for the selected country pack.",
        )
    if not record.canonical_invoice:
        raise HTTPException(status_code=400, detail="Canonical invoice JSON is required before XML generation.")
    if record.validation_report.summary.blocking_errors > 0:
        raise HTTPException(status_code=409, detail="Blocking validation errors must be resolved before XML generation.")

    if record.selected_country_pack == "saudi_zatca":
        try:
            xml_content = generate_saudi_zatca_invoice_xml(record.canonical_invoice)
            qr = generate_saudi_phase_one_qr(record.canonical_invoice)
            pdf_content = generate_saudi_visual_invoice_pdf(record.canonical_invoice, qr.png_bytes)
        except SaudiVisualPdfError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Saudi output data is incomplete: {exc}") from exc

        generated_filename = f"{upload_id}_saudi_zatca_offline_invoice.xml"
        qr_payload_base64_filename = f"{upload_id}_saudi_zatca_phase1_qr_payload_base64.txt"
        qr_payload_decoded_filename = f"{upload_id}_saudi_zatca_phase1_qr_payload_decoded.json"
        qr_image_filename = f"{upload_id}_saudi_zatca_phase1_qr.png"
        pdf_filename = f"{upload_id}_saudi_zatca_visual_invoice.pdf"
        evidence_status = "outputs_generated_milestone_3c"
    else:
        _generate_belgium_xml_for_record(record)
        evidence_status = "xml_generated_milestone_2b"
        record.status = "generated"
        record.generated_at = datetime.now(timezone.utc).isoformat()
        record.evidence_bundle_preview.status = evidence_status
        save_upload(record)
        return record.evidence_bundle_preview

    xml_path, xml_hash = save_binary("generated", generated_filename, xml_content)
    record.generated_xml_path = relative_storage_path(xml_path)
    record.generated_xml_sha256_hash = xml_hash
    _mark_generated_file(record, "invoice.xml", record.generated_xml_path, xml_hash)

    if record.selected_country_pack == "saudi_zatca":
        qr_payload_path, qr_payload_hash = save_binary(
            "generated", qr_payload_base64_filename, qr.payload_base64.encode("ascii")
        )
        qr_decoded_path, qr_decoded_hash = save_binary(
            "generated",
            qr_payload_decoded_filename,
            json.dumps(qr.decoded_payload, indent=2, ensure_ascii=False).encode("utf-8"),
        )
        qr_image_path, qr_image_hash = save_binary("generated", qr_image_filename, qr.png_bytes)
        pdf_path, pdf_hash = save_binary("generated", pdf_filename, pdf_content)
        _mark_generated_file(record, "qr_payload_base64.txt", relative_storage_path(qr_payload_path), qr_payload_hash)
        _mark_generated_file(record, "qr_payload_decoded.json", relative_storage_path(qr_decoded_path), qr_decoded_hash)
        _mark_generated_file(record, "qr.png", relative_storage_path(qr_image_path), qr_image_hash)
        _mark_generated_file(record, "saudi_visual_invoice.pdf", relative_storage_path(pdf_path), pdf_hash)

    record.status = "generated"
    record.generated_at = datetime.now(timezone.utc).isoformat()
    record.evidence_bundle_preview.status = evidence_status
    save_upload(record)
    return record.evidence_bundle_preview


@router.post("/{upload_id}/storecove-sandbox", response_model=UploadRecord)
def submit_storecove_sandbox(upload_id: str) -> UploadRecord:
    record = _require_upload(upload_id)
    if record.selected_country_pack != "uk_info":
        raise HTTPException(status_code=400, detail="Storecove sandbox testing is available only for the UK roadmap pack.")
    if not record.canonical_invoice:
        raise HTTPException(status_code=400, detail="Canonical invoice JSON is required before Storecove sandbox testing.")
    if record.validation_report.summary.blocking_errors > 0:
        raise HTTPException(
            status_code=409,
            detail="Blocking validation errors must be resolved before Storecove sandbox testing.",
        )

    try:
        config = load_storecove_config()
    except StorecoveConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    request_payload = map_canonical_to_storecove_request(record.canonical_invoice, config)
    response_payload, status_payload = submit_storecove_sandbox_mock(request_payload)
    build_storecove_evidence_object(
        request_payload,
        response_payload,
        status_payload,
        config.api_key,
    )

    request_path, request_hash = save_json(
        "generated",
        f"{upload_id}_storecove_request_redacted.json",
        redact_secrets(request_payload.model_dump(mode="json"), config.api_key),
    )
    response_path, response_hash = save_json(
        "generated",
        f"{upload_id}_storecove_response.json",
        response_payload.model_dump(mode="json"),
    )
    status_path, status_hash = save_json(
        "generated",
        f"{upload_id}_storecove_status.json",
        status_payload.model_dump(mode="json"),
    )
    provider_path, provider_hash = save_binary(
        "generated",
        f"{upload_id}_storecove_provider_reference.txt",
        response_payload.provider_reference.encode("utf-8"),
    )
    readme_path, readme_hash = save_binary(
        "generated",
        f"{upload_id}_uk_sandbox_readme.txt",
        _uk_sandbox_readme().encode("utf-8"),
    )

    _mark_generated_file(record, "storecove_request.json", relative_storage_path(request_path), request_hash)
    _mark_generated_file(record, "storecove_response.json", relative_storage_path(response_path), response_hash)
    _mark_generated_file(record, "storecove_status.json", relative_storage_path(status_path), status_hash)
    _mark_generated_file(record, "provider_reference.txt", relative_storage_path(provider_path), provider_hash)
    _mark_generated_file(record, "README_sandbox_only.txt", relative_storage_path(readme_path), readme_hash)

    record.storecove_provider_reference = response_payload.provider_reference
    record.storecove_submission_status = response_payload.status
    record.storecove_mocked = response_payload.mocked
    record.status = "storecove_sandbox_mocked"
    record.generated_at = datetime.now(timezone.utc).isoformat()
    record.evidence_bundle_preview.status = "uk_storecove_sandbox_mocked_milestone_5a"
    return save_upload(record)


@router.get("/{upload_id}/generated-xml")
def read_generated_xml(upload_id: str) -> FileResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.generated_xml_path:
        raise HTTPException(status_code=404, detail="Generated XML is not available for this upload.")
    path = storage_path_from_relative(record.generated_xml_path)
    return FileResponse(path, media_type="application/xml")


@router.get("/{upload_id}/generated-xml/download")
def download_generated_xml(upload_id: str) -> FileResponse:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not record.generated_xml_path:
        raise HTTPException(status_code=404, detail="Generated XML is not available for this upload.")
    path = storage_path_from_relative(record.generated_xml_path)
    return FileResponse(path, media_type="application/xml", filename=_generated_xml_filename(record))


@router.get("/{upload_id}/generated-qr")
def read_generated_qr(upload_id: str) -> FileResponse:
    return _generated_evidence_file(upload_id, "qr.png", "image/png", "Saudi QR image")


@router.get("/{upload_id}/generated-qr/download")
def download_generated_qr(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "qr.png",
        "image/png",
        "Saudi QR image",
        filename=f"{record.upload_id}_saudi_zatca_phase1_qr.png",
    )


@router.get("/{upload_id}/generated-pdf")
def read_generated_pdf(upload_id: str) -> FileResponse:
    return _generated_evidence_file(upload_id, "saudi_visual_invoice.pdf", "application/pdf", "Saudi visual PDF")


@router.get("/{upload_id}/generated-pdf/download")
def download_generated_pdf(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "saudi_visual_invoice.pdf",
        "application/pdf",
        "Saudi visual PDF",
        filename=f"{record.upload_id}_saudi_zatca_visual_invoice.pdf",
    )


@router.get("/{upload_id}/generated-qr-payload/download")
def download_generated_qr_payload(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "qr_payload_base64.txt",
        "text/plain",
        "Saudi QR payload",
        filename=f"{record.upload_id}_saudi_zatca_phase1_qr_payload_base64.txt",
    )


@router.get("/{upload_id}/generated-qr-payload-decoded")
def read_generated_qr_payload_decoded(upload_id: str) -> FileResponse:
    return _generated_evidence_file(
        upload_id,
        "qr_payload_decoded.json",
        "application/json",
        "Decoded Saudi QR payload",
    )


@router.get("/{upload_id}/generated-qr-payload-decoded/download")
def download_generated_qr_payload_decoded(upload_id: str) -> FileResponse:
    record = _require_upload(upload_id)
    return _generated_evidence_file(
        upload_id,
        "qr_payload_decoded.json",
        "application/json",
        "Decoded Saudi QR payload",
        filename=f"{record.upload_id}_saudi_zatca_phase1_qr_payload_decoded.json",
    )


def _write_stored_file(archive: ZipFile, archive_name: str, relative_path: str | None) -> None:
    if not relative_path:
        return
    path = storage_path_from_relative(relative_path)
    if path.exists():
        archive.write(path, archive_name)


def _write_evidence_file(archive: ZipFile, record: UploadRecord, filename: str) -> None:
    evidence_file = next((file for file in record.evidence_bundle_preview.files if file.filename == filename), None)
    _write_stored_file(archive, filename, evidence_file.storage_path if evidence_file else None)


def _hash_manifest(record: UploadRecord) -> str:
    lines = ["filename\tsha256\tstatus"]
    for file in record.evidence_bundle_preview.files:
        lines.append(f"{file.filename}\t{file.sha256 or 'not_available'}\t{file.status}")
    return "\n".join(lines) + "\n"


def _required_acknowledgement_rule_ids(record: UploadRecord) -> list[str]:
    return [
        result.rule_id
        for result in record.validation_report.results
        if result.severity == "warning_ack_required" and result.status == "failed"
    ]


def _requires_acknowledgement(record: UploadRecord) -> bool:
    return bool(_required_acknowledgement_rule_ids(record))


def _acknowledgement_complete(record: UploadRecord) -> bool:
    required_rule_ids = _required_acknowledgement_rule_ids(record)
    return all(rule_id in record.acknowledged_warning_rule_ids for rule_id in required_rule_ids)


def _mark_generated_file(record: UploadRecord, filename: str, storage_path: str, sha256: str) -> None:
    for file in record.evidence_bundle_preview.files:
        if file.filename == filename:
            file.status = "stored"
            file.sha256 = sha256
            file.storage_path = storage_path
            return


def _require_upload(upload_id: str) -> UploadRecord:
    record = get_upload(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return record


def _generated_evidence_file(
    upload_id: str,
    evidence_filename: str,
    media_type: str,
    display_name: str,
    filename: str | None = None,
) -> FileResponse:
    record = _require_upload(upload_id)
    evidence_file = next((file for file in record.evidence_bundle_preview.files if file.filename == evidence_filename), None)
    if not evidence_file or not evidence_file.storage_path:
        raise HTTPException(status_code=404, detail=f"{display_name} is not available for this upload.")
    path = storage_path_from_relative(evidence_file.storage_path)
    return FileResponse(path, media_type=media_type, filename=filename)


def _generated_xml_filename(record: UploadRecord) -> str:
    if record.selected_country_pack == "saudi_zatca":
        return f"{record.upload_id}_saudi_zatca_offline_invoice.xml"
    return f"{record.upload_id}_belgium_peppol_invoice.xml"


def _run_belgium_validation_pipeline(record: UploadRecord) -> UploadRecord:
    if record.validation_report.summary.blocking_errors > 0 or not record.canonical_invoice:
        _store_external_validation_status(
            record,
            _external_validation_skipped(
                "External e-invoice.be sandbox validation skipped because internal validation has blocking errors.",
            ),
        )
        return record

    _generate_belgium_xml_for_record(record)
    record.evidence_bundle_preview.status = "belgium_validation_pipeline_milestone_5b"
    config_status = load_einvoicebe_configuration_status()
    if not config_status.configured:
        endpoint = f"{config_status.api_base_url.rstrip('/')}/api/validate/ubl"
        _store_external_validation_status(record, _external_validation_not_configured(endpoint))
        return record

    config = load_einvoicebe_config()
    try:
        _run_einvoicebe_external_validation(record, config)
    except Exception:
        _store_external_validation_status(record, _external_validation_failed(config.validation_url))
    record.evidence_bundle_preview.status = "belgium_validation_pipeline_milestone_5b"
    return record


def _generate_belgium_xml_for_record(record: UploadRecord) -> None:
    if not record.canonical_invoice:
        raise HTTPException(status_code=400, detail="Canonical invoice JSON is required before XML generation.")
    xml_content = generate_belgium_ubl_invoice_xml(record.canonical_invoice)
    xml_path, xml_hash = save_binary("generated", _generated_xml_filename(record), xml_content)
    record.generated_xml_path = relative_storage_path(xml_path)
    record.generated_xml_sha256_hash = xml_hash
    _mark_generated_file(record, "invoice.xml", record.generated_xml_path, xml_hash)
    record.generated_at = datetime.now(timezone.utc).isoformat()


def _run_einvoicebe_external_validation(record: UploadRecord, config) -> None:
    if not record.generated_xml_path:
        raise HTTPException(status_code=409, detail="Generate Belgium XML before external e-invoice.be validation.")

    xml_path = storage_path_from_relative(record.generated_xml_path)
    xml_bytes = xml_path.read_bytes()
    xml_filename = _generated_xml_filename(record)
    request_evidence = build_ubl_validation_request_evidence(
        config=config,
        xml_bytes=xml_bytes,
        filename=xml_filename,
    )
    request_path, request_hash = save_json(
        "generated",
        f"{record.upload_id}_einvoicebe_validation_request.json",
        redact_einvoicebe_secrets(request_evidence.model_dump(mode="json"), config.api_key),
    )
    _mark_generated_file(record, "einvoicebe_validation_request.json", relative_storage_path(request_path), request_hash)
    response_payload = submit_ubl_validation(config=config, xml_bytes=xml_bytes, filename=xml_filename)
    validated_at = datetime.now(timezone.utc).isoformat()
    status_payload = build_external_validation_status(
        response=response_payload,
        endpoint=config.validation_url,
        validated_at=validated_at,
    )
    _append_einvoicebe_sender_identity_hint(status_payload, response_payload, config, xml_bytes)

    response_path, response_hash = save_json(
        "generated",
        f"{record.upload_id}_einvoicebe_validation_response.json",
        redact_einvoicebe_secrets(response_payload.model_dump(mode="json"), config.api_key),
    )
    _mark_generated_file(record, "einvoicebe_validation_response.json", relative_storage_path(response_path), response_hash)
    _store_external_validation_status(record, status_payload)


def _ensure_einvoicebe_sandbox_send_allowed(record: UploadRecord) -> None:
    if record.selected_country_pack != "belgium_peppol":
        raise HTTPException(status_code=400, detail="e-invoice.be sandbox send is available only for Belgium XML outputs.")
    if not record.canonical_invoice:
        raise HTTPException(status_code=400, detail="Canonical invoice JSON is required before sandbox send.")
    if record.validation_report.summary.blocking_errors > 0:
        raise HTTPException(
            status_code=409,
            detail="Internal validation must pass before e-invoice.be sandbox send.",
        )
    if not record.generated_xml_path:
        raise HTTPException(
            status_code=409,
            detail="Belgium XML must be generated before e-invoice.be sandbox send.",
        )
    if not record.external_validation or record.external_validation.status != "passed" or record.external_validation.is_valid is not True:
        raise HTTPException(
            status_code=409,
            detail="External e-invoice.be sandbox validation must pass before sandbox send.",
        )


def _run_einvoicebe_sandbox_send(record: UploadRecord, config) -> None:
    if not record.generated_xml_path:
        raise HTTPException(status_code=409, detail="Generate Belgium XML before e-invoice.be sandbox send.")
    if not record.canonical_invoice:
        raise HTTPException(status_code=400, detail="Canonical invoice JSON is required before e-invoice.be sandbox send.")

    xml_path = storage_path_from_relative(record.generated_xml_path)
    xml_bytes = xml_path.read_bytes()
    xml_filename = _generated_xml_filename(record)
    sender_peppol_id = _einvoicebe_send_request_sender_peppol_id(record.canonical_invoice)
    receiver_peppol_id = _canonical_party_peppol_id(record.canonical_invoice.buyer)
    sender_identity_check = build_sender_identity_check(
        tenant_peppol_id=config.sandbox_peppol_id,
        xml_bytes=xml_bytes,
        send_request_sender_peppol_id=sender_peppol_id,
    )
    request_evidence = build_ubl_sandbox_send_request_evidence(
        config=config,
        xml_bytes=xml_bytes,
        filename=xml_filename,
        sender_peppol_id=sender_peppol_id,
        receiver_peppol_id=receiver_peppol_id,
    )
    _store_einvoicebe_send_request(record, config, request_evidence)

    try:
        response_payload = submit_ubl_sandbox_send(
            config=config,
            xml_bytes=xml_bytes,
            filename=xml_filename,
            sender_peppol_id=sender_peppol_id,
            receiver_peppol_id=receiver_peppol_id,
        )
    except Exception:
        _store_external_sandbox_send_status(
            record,
            _external_sandbox_send_failed(
                endpoint=f"{config.api_base_url.rstrip('/')}/api/documents/{{document_id}}/send",
                message="e-invoice.be sandbox send failed before a provider response was captured.",
            ),
        )
        record.status = "einvoicebe_sandbox_send_failed"
        record.generated_at = datetime.now(timezone.utc).isoformat()
        return

    if response_payload.document_id:
        request_evidence = build_ubl_sandbox_send_request_evidence(
            config=config,
            xml_bytes=xml_bytes,
            filename=xml_filename,
            sender_peppol_id=sender_peppol_id,
            receiver_peppol_id=receiver_peppol_id,
            document_id=response_payload.document_id,
        )
        _store_einvoicebe_send_request(record, config, request_evidence)

    response_path, response_hash = save_json(
        "generated",
        f"{record.upload_id}_einvoicebe_send_response.json",
        redact_einvoicebe_secrets(response_payload.model_dump(mode="json"), config.api_key),
    )
    _mark_generated_file(record, "einvoicebe_send_response.json", relative_storage_path(response_path), response_hash)

    submitted_at = datetime.now(timezone.utc).isoformat()
    send_endpoint = (
        config.document_send_url(response_payload.document_id)
        if response_payload.document_id
        else f"{config.api_base_url.rstrip('/')}/api/documents/{{document_id}}/send"
    )
    status_payload = build_sandbox_send_status(
        response=response_payload,
        endpoint=send_endpoint,
        submitted_at=submitted_at,
        sender_identity_check=sender_identity_check,
    )
    if (
        response_payload.status == "failed"
        and "tenant does not own the sender peppol id" in response_payload.message.lower()
        and sender_identity_check["send_request_sender_source"] == "omitted_provider_tenant_inferred"
    ):
        status_payload.messages = [
            "Sandbox provider rejected the send because the tenant does not own the sender Peppol ID in the generated Belgium XML. This is the known e-invoice.be sandbox identity limitation.",
            response_payload.message,
        ]
    _store_external_sandbox_send_status(record, status_payload)
    if response_payload.provider_reference:
        reference_path, reference_hash = save_binary(
            "generated",
            f"{record.upload_id}_einvoicebe_send_provider_reference.txt",
            response_payload.provider_reference.encode("utf-8"),
        )
        _mark_generated_file(
            record,
            "einvoicebe_send_provider_reference.txt",
            relative_storage_path(reference_path),
            reference_hash,
        )

    record.status = f"einvoicebe_sandbox_send_{response_payload.status}"
    record.generated_at = submitted_at
    record.evidence_bundle_preview.status = "belgium_einvoicebe_sandbox_send_milestone_5c"


def _store_einvoicebe_send_request(record: UploadRecord, config, request_evidence) -> None:
    request_path, request_hash = save_json(
        "generated",
        f"{record.upload_id}_einvoicebe_send_request.json",
        redact_einvoicebe_secrets(request_evidence.model_dump(mode="json"), config.api_key),
    )
    _mark_generated_file(record, "einvoicebe_send_request.json", relative_storage_path(request_path), request_hash)


def _store_external_sandbox_send_status(record: UploadRecord, status_payload: EInvoiceBESandboxSendStatus) -> None:
    status_path, status_hash = save_json(
        "generated",
        f"{record.upload_id}_external_sandbox_send_status.json",
        status_payload.model_dump(mode="json"),
    )
    _mark_generated_file(record, "external_sandbox_send_status.json", relative_storage_path(status_path), status_hash)
    record.external_sandbox_send = ExternalSandboxSendRecord(**status_payload.model_dump(mode="json"))


def _store_external_validation_status(record: UploadRecord, status_payload: EInvoiceBEExternalValidationStatus) -> None:
    status_path, status_hash = save_json(
        "generated",
        f"{record.upload_id}_external_validation_status.json",
        status_payload.model_dump(mode="json"),
    )
    _mark_generated_file(record, "external_validation_status.json", relative_storage_path(status_path), status_hash)
    record.external_validation = ExternalValidationRecord(**status_payload.model_dump(mode="json"))


def _append_einvoicebe_sender_identity_hint(
    status_payload: EInvoiceBEExternalValidationStatus,
    response_payload,
    config,
    xml_bytes: bytes,
) -> None:
    sender_identity_check = build_sender_identity_check(
        tenant_peppol_id=config.sandbox_peppol_id,
        xml_bytes=xml_bytes,
        send_request_sender_peppol_id=None,
    )
    if sender_identity_check["xml_seller_endpoint_scheme"] != "0208":
        return
    if not sender_identity_check["xml_sender_matches_tenant"]:
        return

    has_endpoint_format_error = any(
        issue.rule_id == "PEPPOL-COMMON-R043"
        and "EndpointID" in str(issue.location or "")
        for issue in response_payload.issues
    )
    if not has_endpoint_format_error:
        return

    message = (
        f"Configured e-invoice.be tenant Peppol ID {config.sandbox_peppol_id} is used as the XML seller EndpointID, "
        "but provider rule PEPPOL-COMMON-R043 requires a 10-digit Belgian enterprise number that passes mod97. "
        "Sandbox send cannot proceed until the tenant-owned sender Peppol ID also satisfies external validation."
    )
    if message not in status_payload.messages:
        status_payload.messages.append(message)


def _canonical_party_peppol_id(party: dict) -> str | None:
    value = party.get("peppol_id")
    if not value:
        return None
    return str(value)


def _einvoicebe_send_request_sender_peppol_id(canonical: CanonicalInvoice) -> str | None:
    return None


def _external_validation_not_configured(endpoint: str) -> EInvoiceBEExternalValidationStatus:
    return EInvoiceBEExternalValidationStatus(
        status="not_configured",
        is_valid=None,
        reference=None,
        validated_at=datetime.now(timezone.utc).isoformat(),
        issue_count=0,
        messages=["External e-invoice.be sandbox validation not configured."],
        endpoint=endpoint,
        disclaimer=EINVOICEBE_SANDBOX_WORDING,
    )


def _external_validation_not_run(message: str) -> EInvoiceBEExternalValidationStatus:
    return EInvoiceBEExternalValidationStatus(
        status="not_run",
        is_valid=None,
        reference=None,
        validated_at=datetime.now(timezone.utc).isoformat(),
        issue_count=0,
        messages=[message],
        endpoint="https://api.e-invoice.be/api/validate/ubl",
        disclaimer=EINVOICEBE_SANDBOX_WORDING,
    )


def _external_validation_skipped(message: str) -> EInvoiceBEExternalValidationStatus:
    return EInvoiceBEExternalValidationStatus(
        status="skipped",
        is_valid=None,
        reference=None,
        validated_at=datetime.now(timezone.utc).isoformat(),
        issue_count=0,
        messages=[message],
        endpoint="https://api.e-invoice.be/api/validate/ubl",
        disclaimer=EINVOICEBE_SANDBOX_WORDING,
    )


def _external_validation_failed(endpoint: str) -> EInvoiceBEExternalValidationStatus:
    return EInvoiceBEExternalValidationStatus(
        status="failed",
        is_valid=False,
        reference=None,
        validated_at=datetime.now(timezone.utc).isoformat(),
        issue_count=1,
        messages=["External e-invoice.be sandbox validation failed before a provider response was captured."],
        endpoint=endpoint,
        disclaimer=EINVOICEBE_SANDBOX_WORDING,
    )


def _external_sandbox_send_failed(endpoint: str, message: str) -> EInvoiceBESandboxSendStatus:
    return EInvoiceBESandboxSendStatus(
        status="failed",
        submitted_at=datetime.now(timezone.utc).isoformat(),
        provider_reference=None,
        document_id=None,
        provider_document_state=None,
        endpoint=endpoint,
        messages=[message],
        disclaimer=EINVOICEBE_SANDBOX_SEND_WORDING,
    )


def _uk_sandbox_readme() -> str:
    return (
        f"{UK_SANDBOX_WORDING}\n\n"
        "Milestone 5A does not perform live Storecove API calls. Mocked sandbox responses are test evidence only.\n"
        "No production Peppol transmission, HMRC submission, statutory compliance proof or authority acceptance is included.\n"
        "Storecove API keys and secrets must not appear in this evidence bundle.\n"
    )
