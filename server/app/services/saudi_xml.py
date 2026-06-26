from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET

from app.models.canonical import CanonicalInvoice


UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

SAUDI_PROFILE_ID = "reporting:1.0"
OFFLINE_BOUNDARY_NOTE = (
    "Offline demo Saudi XML generated from canonical invoice JSON only. "
    "No FATOORA submission, ZATCA clearance stamp, production cryptographic signature or authority approval."
)

ET.register_namespace("", UBL_INVOICE_NS)
ET.register_namespace("cac", CAC_NS)
ET.register_namespace("cbc", CBC_NS)


def generate_saudi_zatca_invoice_xml(canonical: CanonicalInvoice) -> bytes:
    invoice = canonical.invoice
    currency = str(invoice.get("invoice_currency_code") or "SAR")
    tax_currency = str(invoice.get("tax_currency_code") or currency)
    root = ET.Element(_ubl("Invoice"))

    _text(root, "cbc", "ProfileID", SAUDI_PROFILE_ID)
    _text(root, "cbc", "ID", invoice.get("invoice_number"))
    _text(root, "cbc", "UUID", _invoice_uuid(canonical))
    _text(root, "cbc", "IssueDate", invoice.get("invoice_date"))
    _text(root, "cbc", "IssueTime", invoice.get("invoice_time"))
    invoice_type_code = _text(root, "cbc", "InvoiceTypeCode", invoice.get("invoice_type_code") or "388")
    invoice_type_code.set("name", "0100000")
    _text(root, "cbc", "DocumentCurrencyCode", currency)
    _text(root, "cbc", "TaxCurrencyCode", tax_currency)
    _text(root, "cbc", "Note", OFFLINE_BOUNDARY_NOTE)

    _optional_additional_document_reference(root, "ICV", invoice.get("invoice_counter_value"))
    _optional_additional_document_reference(root, "PIH", invoice.get("previous_invoice_hash"))
    _delivery(root, invoice)
    _party(root, "AccountingSupplierParty", canonical.seller)
    _party(root, "AccountingCustomerParty", canonical.buyer)
    _payment_means(root, canonical)
    _tax_total(root, canonical, tax_currency)
    _legal_monetary_total(root, canonical, currency)
    for line in canonical.lines:
        _invoice_line(root, line, currency)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _party(parent: ET.Element, wrapper_name: str, party_data: dict[str, Any]) -> None:
    wrapper = _child(parent, "cac", wrapper_name)
    party = _child(wrapper, "cac", "Party")

    legal_registration = party_data.get("legal_registration_number")
    if _has_value(legal_registration):
        identification = _child(party, "cac", "PartyIdentification")
        _text(identification, "cbc", "ID", legal_registration)

    address = _child(party, "cac", "PostalAddress")
    _text(address, "cbc", "StreetName", party_data.get("address_line_1"))
    _optional_text(address, "cbc", "AdditionalStreetName", party_data.get("address_line_2"))
    _text(address, "cbc", "CityName", party_data.get("city"))
    _optional_text(address, "cbc", "PostalZone", party_data.get("postal_code"))
    country = _child(address, "cac", "Country")
    _text(country, "cbc", "IdentificationCode", party_data.get("country_code") or "SA")

    tax_scheme = _child(party, "cac", "PartyTaxScheme")
    _text(tax_scheme, "cbc", "CompanyID", party_data.get("tax_registration_number"))
    tax_scheme_id = _child(tax_scheme, "cac", "TaxScheme")
    _text(tax_scheme_id, "cbc", "ID", "VAT")

    legal_entity = _child(party, "cac", "PartyLegalEntity")
    _text(legal_entity, "cbc", "RegistrationName", party_data.get("legal_name"))
    if _has_value(legal_registration):
        _text(legal_entity, "cbc", "CompanyID", legal_registration)


def _delivery(parent: ET.Element, invoice: dict[str, Any]) -> None:
    supply_date = invoice.get("supply_date") or invoice.get("tax_point_date")
    if not _has_value(supply_date):
        return
    delivery = _child(parent, "cac", "Delivery")
    _text(delivery, "cbc", "ActualDeliveryDate", supply_date)


def _payment_means(parent: ET.Element, canonical: CanonicalInvoice) -> None:
    payment_means_code = canonical.invoice.get("payment_means_code")
    if not _has_value(payment_means_code):
        return
    payment_means = _child(parent, "cac", "PaymentMeans")
    _text(payment_means, "cbc", "PaymentMeansCode", payment_means_code)
    _text(payment_means, "cbc", "PaymentID", canonical.invoice.get("payment_id") or canonical.invoice.get("invoice_number"))


def _tax_total(parent: ET.Element, canonical: CanonicalInvoice, currency: str) -> None:
    tax_total = _child(parent, "cac", "TaxTotal")
    _amount(tax_total, "TaxAmount", canonical.totals.get("tax_total"), currency)

    for summary in canonical.tax_summary:
        subtotal = _child(tax_total, "cac", "TaxSubtotal")
        _amount(subtotal, "TaxableAmount", summary.taxable_amount, currency)
        _amount(subtotal, "TaxAmount", summary.tax_amount, currency)
        category = _child(subtotal, "cac", "TaxCategory")
        _text(category, "cbc", "ID", summary.tax_category_code)
        _text(category, "cbc", "Percent", _percent(summary.tax_rate))
        tax_scheme = _child(category, "cac", "TaxScheme")
        _text(tax_scheme, "cbc", "ID", "VAT")


def _legal_monetary_total(parent: ET.Element, canonical: CanonicalInvoice, currency: str) -> None:
    totals = canonical.totals
    monetary_total = _child(parent, "cac", "LegalMonetaryTotal")
    _amount(monetary_total, "LineExtensionAmount", totals.get("line_extension_total") or totals.get("net_total"), currency)
    _amount(monetary_total, "TaxExclusiveAmount", totals.get("tax_exclusive_total") or totals.get("net_total"), currency)
    _amount(monetary_total, "TaxInclusiveAmount", totals.get("tax_inclusive_total") or totals.get("gross_total"), currency)
    _amount(monetary_total, "PayableAmount", totals.get("payable_amount") or totals.get("gross_total"), currency)


def _invoice_line(parent: ET.Element, line: dict[str, Any], currency: str) -> None:
    invoice_line = _child(parent, "cac", "InvoiceLine")
    _text(invoice_line, "cbc", "ID", line.get("line_number"))
    quantity = _text(invoice_line, "cbc", "InvoicedQuantity", _quantity(line.get("quantity")))
    unit_code = line.get("unit_code")
    if _has_value(unit_code):
        quantity.set("unitCode", str(unit_code))
    _amount(invoice_line, "LineExtensionAmount", line.get("line_net_amount"), currency)

    item = _child(invoice_line, "cac", "Item")
    _text(item, "cbc", "Name", line.get("item_name") or line.get("description"))
    tax_category = _child(item, "cac", "ClassifiedTaxCategory")
    _text(tax_category, "cbc", "ID", line.get("tax_category_code"))
    _text(tax_category, "cbc", "Percent", _percent(line.get("tax_rate")))
    tax_scheme = _child(tax_category, "cac", "TaxScheme")
    _text(tax_scheme, "cbc", "ID", "VAT")

    price = _child(invoice_line, "cac", "Price")
    _amount(price, "PriceAmount", line.get("unit_price"), currency)


def _optional_additional_document_reference(parent: ET.Element, reference_id: str, value: Any) -> None:
    if not _has_value(value):
        return
    reference = _child(parent, "cac", "AdditionalDocumentReference")
    _text(reference, "cbc", "ID", reference_id)
    _text(reference, "cbc", "UUID", value)


def _invoice_uuid(canonical: CanonicalInvoice) -> str:
    invoice = canonical.invoice
    explicit_uuid = invoice.get("uuid") or invoice.get("invoice_uuid") or canonical.metadata.get("uuid")
    if _has_value(explicit_uuid):
        return str(explicit_uuid)
    seed = "|".join(
        [
            str(canonical.metadata.get("country_pack_id") or "saudi_zatca"),
            str(invoice.get("invoice_number") or ""),
            str(invoice.get("invoice_date") or ""),
            str(invoice.get("invoice_time") or ""),
            str(canonical.source.get("workbook_sha256_hash") or ""),
        ]
    )
    return str(uuid5(NAMESPACE_URL, seed))


def _amount(parent: ET.Element, name: str, value: Any, currency: str) -> ET.Element:
    element = _text(parent, "cbc", name, _money(value))
    element.set("currencyID", currency)
    return element


def _child(parent: ET.Element, namespace: str, name: str) -> ET.Element:
    return ET.SubElement(parent, _qname(namespace, name))


def _text(parent: ET.Element, namespace: str, name: str, value: Any) -> ET.Element:
    element = _child(parent, namespace, name)
    element.text = "" if value is None else str(value)
    return element


def _optional_text(parent: ET.Element, namespace: str, name: str, value: Any) -> ET.Element | None:
    if not _has_value(value):
        return None
    return _text(parent, namespace, name, value)


def _qname(namespace: str, name: str) -> str:
    if namespace == "cbc":
        uri = CBC_NS
    elif namespace == "cac":
        uri = CAC_NS
    elif namespace == "ubl":
        uri = UBL_INVOICE_NS
    else:
        raise ValueError(f"Unknown XML namespace prefix: {namespace}")
    return f"{{{uri}}}{name}"


def _ubl(name: str) -> str:
    return _qname("ubl", name)


def _money(value: Any) -> str:
    return str(_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _quantity(value: Any) -> str:
    amount = _decimal(value)
    if amount == amount.to_integral():
        return str(amount.quantize(Decimal("1")))
    return str(amount.normalize())


def _percent(value: Any) -> str:
    amount = _decimal(value)
    if amount == amount.to_integral():
        return str(amount.quantize(Decimal("1")))
    return str(amount.normalize())


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""
