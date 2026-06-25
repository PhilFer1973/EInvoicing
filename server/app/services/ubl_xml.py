from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from xml.etree import ElementTree as ET

from app.models.canonical import CanonicalInvoice


UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
PROFILE_ID = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

ET.register_namespace("", UBL_INVOICE_NS)
ET.register_namespace("cac", CAC_NS)
ET.register_namespace("cbc", CBC_NS)


def generate_belgium_ubl_invoice_xml(canonical: CanonicalInvoice) -> bytes:
    invoice = canonical.invoice
    currency = str(invoice.get("invoice_currency_code") or "EUR")
    root = ET.Element(_ubl("Invoice"))

    _text(root, "cbc", "CustomizationID", CUSTOMIZATION_ID)
    _text(root, "cbc", "ProfileID", PROFILE_ID)
    _text(root, "cbc", "ID", invoice.get("invoice_number"))
    _text(root, "cbc", "IssueDate", invoice.get("invoice_date"))
    _optional_text(root, "cbc", "DueDate", invoice.get("due_date"))
    _text(root, "cbc", "InvoiceTypeCode", invoice.get("invoice_type_code") or "380")
    _text(root, "cbc", "DocumentCurrencyCode", currency)

    buyer_reference = invoice.get("buyer_reference")
    purchase_order_reference = invoice.get("purchase_order_reference")
    if _has_value(buyer_reference):
        _text(root, "cbc", "BuyerReference", buyer_reference)
    if _has_value(purchase_order_reference):
        order_reference = _child(root, "cac", "OrderReference")
        _text(order_reference, "cbc", "ID", purchase_order_reference)

    _party(root, "AccountingSupplierParty", canonical.seller)
    _party(root, "AccountingCustomerParty", canonical.buyer)
    _payment_means(root, canonical, currency)
    _tax_total(root, canonical, currency)
    _legal_monetary_total(root, canonical, currency)
    for line in canonical.lines:
        _invoice_line(root, line, currency)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _party(parent: ET.Element, wrapper_name: str, party_data: dict[str, Any]) -> None:
    wrapper = _child(parent, "cac", wrapper_name)
    party = _child(wrapper, "cac", "Party")

    endpoint_id = party_data.get("peppol_id")
    endpoint_scheme = party_data.get("peppol_scheme_id")
    endpoint_value = _identifier_value(endpoint_id, endpoint_scheme)
    if _has_value(endpoint_value):
        element = _text(party, "cbc", "EndpointID", endpoint_value)
        if _has_value(endpoint_scheme):
            element.set("schemeID", str(endpoint_scheme))

    legal_registration = party_data.get("legal_registration_number")
    if _has_value(legal_registration):
        identification = _child(party, "cac", "PartyIdentification")
        identifier = _text(identification, "cbc", "ID", legal_registration)
        scheme = party_data.get("legal_registration_scheme_id")
        if _has_value(scheme):
            identifier.set("schemeID", str(scheme))

    address = _child(party, "cac", "PostalAddress")
    _text(address, "cbc", "StreetName", party_data.get("address_line_1"))
    _optional_text(address, "cbc", "AdditionalStreetName", party_data.get("address_line_2"))
    _text(address, "cbc", "CityName", party_data.get("city"))
    _text(address, "cbc", "PostalZone", party_data.get("postal_code"))
    country = _child(address, "cac", "Country")
    _text(country, "cbc", "IdentificationCode", party_data.get("country_code"))

    tax_scheme = _child(party, "cac", "PartyTaxScheme")
    _text(tax_scheme, "cbc", "CompanyID", party_data.get("tax_registration_number"))
    tax_scheme_id = _child(tax_scheme, "cac", "TaxScheme")
    _text(tax_scheme_id, "cbc", "ID", "VAT")

    legal_entity = _child(party, "cac", "PartyLegalEntity")
    _text(legal_entity, "cbc", "RegistrationName", party_data.get("legal_name"))
    if _has_value(legal_registration):
        company_id = _text(legal_entity, "cbc", "CompanyID", legal_registration)
        scheme = party_data.get("legal_registration_scheme_id")
        if _has_value(scheme):
            company_id.set("schemeID", str(scheme))


def _payment_means(parent: ET.Element, canonical: CanonicalInvoice, currency: str) -> None:
    invoice = canonical.invoice
    seller = canonical.seller
    payment_means_code = invoice.get("payment_means_code")
    if not _has_value(payment_means_code):
        return

    payment_means = _child(parent, "cac", "PaymentMeans")
    _text(payment_means, "cbc", "PaymentMeansCode", payment_means_code)
    _text(payment_means, "cbc", "PaymentID", invoice.get("payment_id") or invoice.get("invoice_number"))

    iban = seller.get("iban")
    if _has_value(iban):
        account = _child(payment_means, "cac", "PayeeFinancialAccount")
        _text(account, "cbc", "ID", iban)
        _text(account, "cbc", "Name", seller.get("payment_account_name") or seller.get("legal_name"))
        bic = seller.get("bic")
        if _has_value(bic):
            branch = _child(account, "cac", "FinancialInstitutionBranch")
            _text(branch, "cbc", "ID", bic)


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


def _identifier_value(identifier: Any, scheme: Any) -> Any:
    if not _has_value(identifier):
        return identifier
    text = str(identifier)
    prefix = f"{scheme}:"
    if _has_value(scheme) and text.startswith(prefix):
        return text[len(prefix):]
    return identifier
