from __future__ import annotations

import hashlib
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any
from uuid import uuid4

from openpyxl import load_workbook

from app.adapters.registry import get_adapter
from app.models.canonical import CanonicalInvoice, TaxSummaryLine
from app.models.country_pack import CountryPack
from app.models.upload import UploadRecord
from app.models.validation import ValidationResult
from app.services.validation import boundary_results_for_pack, build_validation_report


REQUIRED_SHEETS = ["entities", "customers", "invoice_header", "invoice_lines"]

REQUIRED_COLUMNS = {
    "entities": [
        "entity_id",
        "legal_name",
        "country_code",
        "tax_registration_number",
        "address_line_1",
        "city",
    ],
    "customers": [
        "customer_id",
        "legal_name",
        "buyer_type",
        "country_code",
        "address_line_1",
        "city",
    ],
    "invoice_header": [
        "invoice_id",
        "invoice_number",
        "invoice_date",
        "entity_id",
        "customer_id",
        "invoice_type",
        "supply_type",
        "transaction_type",
        "selected_country_pack",
        "selected_output_profile",
        "invoice_currency_code",
        "net_total",
        "tax_total",
        "gross_total",
    ],
    "invoice_lines": [
        "invoice_id",
        "line_number",
        "description",
        "quantity",
        "unit_code",
        "unit_price",
        "line_net_amount",
        "tax_category_code",
        "tax_amount",
    ],
}


def parse_workbook_upload(content: bytes, filename: str, pack: CountryPack) -> UploadRecord:
    upload_id = f"UP-{uuid4().hex[:10].upper()}"
    workbook_hash = hashlib.sha256(content).hexdigest()
    results: list[ValidationResult] = []
    canonical_invoice: CanonicalInvoice | None = None

    try:
        workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
    except Exception as exc:
        results.append(
            ValidationResult(
                rule_id="WB-OPEN-001",
                layer="workbook_structure",
                severity="error",
                status="failed",
                message="The uploaded file could not be opened as an .xlsx workbook.",
                field_path="workbook",
                corrective_action="Upload a valid Excel .xlsx workbook using the V1 template structure.",
                technical_detail=str(exc),
            )
        )
        report = build_validation_report(results)
        evidence = get_adapter(pack.country_pack_id).build_output_placeholder(None)
        return UploadRecord(
            upload_id=upload_id,
            original_filename=filename,
            selected_country_pack=pack.country_pack_id,
            selected_output_profile=pack.default_output_profile,
            workbook_sha256_hash=workbook_hash,
            status="parse_failed",
            canonical_invoice=None,
            validation_report=report,
            evidence_bundle_preview=evidence,
        )

    missing_sheets = [sheet for sheet in REQUIRED_SHEETS if sheet not in workbook.sheetnames]
    if missing_sheets:
        for sheet_name in missing_sheets:
            results.append(
                ValidationResult(
                    rule_id="WB-SHEET-001",
                    layer="workbook_structure",
                    severity="error",
                    status="failed",
                    message=f"Missing required workbook sheet: {sheet_name}.",
                    field_path=f"workbook.{sheet_name}",
                    corrective_action="Add the required sheet and upload the workbook again.",
                )
            )
    else:
        results.append(
            ValidationResult(
                rule_id="WB-SHEET-000",
                layer="workbook_structure",
                severity="info",
                status="passed",
                message="Workbook contains the required V1 sheets.",
                field_path="workbook",
            )
        )

    records: dict[str, list[dict[str, Any]]] = {}
    if not missing_sheets:
        for sheet_name in REQUIRED_SHEETS:
            sheet_records, missing_columns = _sheet_records(workbook[sheet_name], sheet_name)
            records[sheet_name] = sheet_records
            for column in missing_columns:
                results.append(
                    ValidationResult(
                        rule_id="WB-COLUMN-001",
                        layer="workbook_structure",
                        severity="error",
                        status="failed",
                        message=f"Missing required column '{column}' on sheet '{sheet_name}'.",
                        field_path=f"{sheet_name}.{column}",
                        corrective_action="Add the required column and upload the workbook again.",
                    )
                )

    if not any(result.severity == "error" and result.status == "failed" for result in results):
        canonical_invoice = _build_canonical_invoice(records, filename, workbook_hash, pack)
        results.append(
            ValidationResult(
                rule_id="CANONICAL-001",
                layer="canonical_construction",
                severity="info",
                status="passed",
                message="Canonical invoice JSON scaffold was constructed from workbook rows.",
                field_path="canonical_invoice",
                country_pack_id=pack.country_pack_id,
                country_pack_version=pack.pack_version,
            )
        )
        results.extend(_basic_required_value_results(canonical_invoice, pack))
        results.extend(boundary_results_for_pack(pack))

    report = build_validation_report(results)
    evidence = get_adapter(pack.country_pack_id).build_output_placeholder(canonical_invoice)
    evidence.generation_id = f"GEN-PREVIEW-{upload_id.replace('UP-', '')}"
    status = "validated" if report.summary.blocking_errors == 0 else "validation_failed"

    return UploadRecord(
        upload_id=upload_id,
        original_filename=filename,
        selected_country_pack=pack.country_pack_id,
        selected_output_profile=pack.default_output_profile,
        workbook_sha256_hash=workbook_hash,
        status=status,
        canonical_invoice=canonical_invoice,
        validation_report=report,
        evidence_bundle_preview=evidence,
    )


def _sheet_records(sheet: Any, sheet_name: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return [], REQUIRED_COLUMNS[sheet_name]

    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    header_set = set(headers)
    missing_columns = [column for column in REQUIRED_COLUMNS[sheet_name] if column not in header_set]
    records: list[dict[str, Any]] = []

    for row in rows[1:]:
        values = dict(zip(headers, row, strict=False))
        if any(value not in (None, "") for value in values.values()):
            records.append({key: _normalise_cell(value) for key, value in values.items() if key})

    return records, missing_columns


def _build_canonical_invoice(
    records: dict[str, list[dict[str, Any]]],
    filename: str,
    workbook_hash: str,
    pack: CountryPack,
) -> CanonicalInvoice:
    seller = records["entities"][0] if records["entities"] else {}
    buyer = records["customers"][0] if records["customers"] else {}
    invoice = records["invoice_header"][0] if records["invoice_header"] else {}
    invoice_id = invoice.get("invoice_id")
    lines = [
        line
        for line in records["invoice_lines"]
        if not invoice_id or line.get("invoice_id") == invoice_id
    ]

    return CanonicalInvoice(
        invoice=invoice,
        seller=seller,
        buyer=buyer,
        lines=lines,
        tax_summary=_derive_tax_summary(lines),
        totals={
            "net_total": invoice.get("net_total"),
            "tax_total": invoice.get("tax_total"),
            "gross_total": invoice.get("gross_total"),
            "line_extension_total": invoice.get("line_extension_total") or invoice.get("net_total"),
            "tax_exclusive_total": invoice.get("tax_exclusive_total") or invoice.get("net_total"),
            "tax_inclusive_total": invoice.get("tax_inclusive_total") or invoice.get("gross_total"),
            "payable_amount": invoice.get("payable_amount") or invoice.get("gross_total"),
        },
        source={
            "original_filename": filename,
            "workbook_sha256_hash": workbook_hash,
        },
        metadata={
            "country_pack_id": pack.country_pack_id,
            "country_pack_version": pack.pack_version,
            "support_level": pack.support_level,
            "selected_output_profile": invoice.get("selected_output_profile") or pack.default_output_profile,
            "official_artefact_validation": "not_configured",
        },
    )


def _derive_tax_summary(lines: list[dict[str, Any]]) -> list[TaxSummaryLine]:
    grouped: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(lambda: {"base": Decimal("0"), "tax": Decimal("0")})
    for line in lines:
        category = str(line.get("tax_category_code") or "").strip()
        rate = str(line.get("tax_rate") or "0").strip()
        key = (category, rate)
        grouped[key]["base"] += _decimal(line.get("line_net_amount"))
        grouped[key]["tax"] += _decimal(line.get("tax_amount"))

    return [
        TaxSummaryLine(
            tax_category_code=category,
            tax_rate=rate,
            taxable_amount=f"{amounts['base']:.2f}",
            tax_amount=f"{amounts['tax']:.2f}",
        )
        for (category, rate), amounts in sorted(grouped.items())
        if category
    ]


def _basic_required_value_results(canonical: CanonicalInvoice, pack: CountryPack) -> list[ValidationResult]:
    checks = [
        ("GEN-INV-001", "invoice.invoice_number", canonical.invoice.get("invoice_number"), "Invoice number is required."),
        ("GEN-SELLER-001", "seller.legal_name", canonical.seller.get("legal_name"), "Seller legal name is required."),
        (
            "GEN-SELLER-002",
            "seller.tax_registration_number",
            canonical.seller.get("tax_registration_number"),
            "Seller tax registration number is required.",
        ),
        ("GEN-BUYER-001", "buyer.legal_name", canonical.buyer.get("legal_name"), "Buyer legal name is required."),
        ("GEN-DATE-001", "invoice.invoice_date", canonical.invoice.get("invoice_date"), "Invoice date is required."),
    ]
    results: list[ValidationResult] = []
    for rule_id, field_path, value, message in checks:
        failed = value in (None, "")
        results.append(
            ValidationResult(
                rule_id=rule_id,
                layer="legal_invoice_requirements",
                severity="error" if failed else "info",
                status="failed" if failed else "passed",
                message=message if failed else f"{field_path} is present.",
                field_path=field_path,
                country_pack_id=pack.country_pack_id,
                country_pack_version=pack.pack_version,
                corrective_action="Correct the Excel workbook and upload it again." if failed else None,
            )
        )

    if pack.country_pack_id == "saudi_zatca":
        failed = canonical.invoice.get("invoice_time") in (None, "")
        results.append(
            ValidationResult(
                rule_id="SA-INV-001",
                layer="country_preflight",
                severity="error" if failed else "info",
                status="failed" if failed else "passed",
                message="Saudi V1 requires invoice issue time." if failed else "Saudi invoice issue time is present.",
                field_path="invoice.invoice_time",
                country_pack_id=pack.country_pack_id,
                country_pack_version=pack.pack_version,
                corrective_action="Add invoice_time to the invoice_header sheet." if failed else None,
            )
        )

    return results


def _normalise_cell(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")

