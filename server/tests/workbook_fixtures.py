from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook


def belgium_valid_workbook_bytes(**overrides: Any) -> bytes:
    workbook = belgium_valid_workbook(**overrides)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def belgium_valid_workbook(
    *,
    remove_sheet: str | None = None,
    invoice_number: str | None = "INV-BE-2026-001",
    buyer_reference: str | None = "BE-BUYER-REF-001",
    purchase_order_reference: str | None = "",
    tax_total: float = 210.00,
    seller_peppol_id: str | None = "0208:0123456789",
    buyer_peppol_id: str | None = "0208:0987654321",
    duplicate_invoice_number: bool = False,
    remove_column: tuple[str, str] | None = None,
) -> Workbook:
    workbook = Workbook()
    workbook.remove(workbook.active)

    entities = workbook.create_sheet("entities")
    entities.append(
        [
            "entity_id",
            "legal_name",
            "trading_name",
            "country_code",
            "tax_registration_number",
            "legal_registration_number",
            "legal_registration_scheme_id",
            "address_line_1",
            "address_line_2",
            "city",
            "postal_code",
            "country_name",
            "email",
            "phone",
            "iban",
            "bic",
            "payment_account_name",
            "peppol_id",
            "peppol_scheme_id",
        ]
    )
    entities.append(
        [
            "SELLER-BE-1",
            "Demo Belgium Services BV",
            "",
            "BE",
            "BE0123456789",
            "0123456789",
            "0208",
            "Rue Demo 1",
            "",
            "Brussels",
            "1000",
            "Belgium",
            "billing@example.test",
            "",
            "BE68539007547034",
            "BBRUBEBB",
            "Demo Belgium Services BV",
            seller_peppol_id,
            "0208" if seller_peppol_id else "",
        ]
    )

    customers = workbook.create_sheet("customers")
    customers.append(
        [
            "customer_id",
            "legal_name",
            "buyer_type",
            "country_code",
            "tax_registration_number",
            "legal_registration_number",
            "legal_registration_scheme_id",
            "address_line_1",
            "address_line_2",
            "city",
            "postal_code",
            "country_name",
            "email",
            "peppol_id",
            "peppol_scheme_id",
        ]
    )
    customers.append(
        [
            "BUYER-BE-1",
            "Demo Belgium Buyer NV",
            "business",
            "BE",
            "BE0987654321",
            "0987654321",
            "0208",
            "Buyer Street 10",
            "",
            "Antwerp",
            "2000",
            "Belgium",
            "ap@example.test",
            buyer_peppol_id,
            "0208" if buyer_peppol_id else "",
        ]
    )

    header = workbook.create_sheet("invoice_header")
    header.append(
        [
            "invoice_id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "tax_point_date",
            "entity_id",
            "customer_id",
            "invoice_type",
            "invoice_type_code",
            "supply_type",
            "transaction_type",
            "selected_country_pack",
            "selected_output_profile",
            "invoice_currency_code",
            "tax_currency_code",
            "net_total",
            "tax_total",
            "gross_total",
            "buyer_reference",
            "purchase_order_reference",
            "payment_means_code",
            "payment_id",
            "payment_terms_note",
            "erp_source_system",
            "erp_document_reference",
            "notes",
        ]
    )
    header_row = [
        "INV-BE-1",
        invoice_number,
        "2026-06-24",
        "2026-07-24",
        "2026-06-24",
        "SELLER-BE-1",
        "BUYER-BE-1",
        "standard_sales_invoice",
        "380",
        "services",
        "domestic_b2b",
        "belgium_peppol",
        "peppol_bis_billing_3_0_ubl_invoice",
        "EUR",
        "EUR",
        1000.00,
        tax_total,
        1210.00,
        buyer_reference,
        purchase_order_reference,
        "30",
        "INV-BE-2026-001",
        "Payment due within 30 days.",
        "Demo ERP",
        "ERP-BE-001",
        "Belgium V1 domestic B2B services invoice.",
    ]
    header.append(header_row)
    if duplicate_invoice_number:
        second_row = header_row.copy()
        second_row[0] = "INV-BE-2"
        header.append(second_row)

    lines = workbook.create_sheet("invoice_lines")
    lines.append(
        [
            "invoice_id",
            "line_number",
            "description",
            "item_name",
            "quantity",
            "unit_code",
            "unit_price",
            "line_net_amount",
            "tax_category_code",
            "tax_rate",
            "tax_amount",
            "line_gross_amount",
        ]
    )
    lines.append(["INV-BE-1", 1, "Consulting services", "Consulting services", 10, "HUR", 100.00, 1000.00, "S", 21, 210.00, 1210.00])

    if remove_sheet:
        del workbook[remove_sheet]
    if remove_column and remove_column[0] in workbook.sheetnames:
        sheet_name, column_name = remove_column
        sheet = workbook[sheet_name]
        headers = [cell.value for cell in sheet[1]]
        if column_name in headers:
            sheet.delete_cols(headers.index(column_name) + 1)

    return workbook
