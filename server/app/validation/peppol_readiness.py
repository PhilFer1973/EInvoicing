from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from app.validation.xml_models import XMLValidationMessage, XMLValidatorResult


UBL_INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CAC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC_NS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

NS = {
    "ubl": UBL_INVOICE_NS,
    "cac": CAC_NS,
    "cbc": CBC_NS,
}


def validate_basic_ubl_structure(root: ET.Element) -> XMLValidatorResult:
    checks = [
        ("UBL-ROOT-001", "Invoice root", ".", lambda: root.tag == _qname(UBL_INVOICE_NS, "Invoice")),
        ("UBL-NS-001", "Expected UBL invoice namespace", ".", lambda: root.tag.startswith(f"{{{UBL_INVOICE_NS}}}")),
        ("UBL-NS-002", "CommonBasicComponents namespace usage", ".//cbc:*", lambda: _has_namespace(root, CBC_NS)),
        ("UBL-NS-003", "CommonAggregateComponents namespace usage", ".//cac:*", lambda: _has_namespace(root, CAC_NS)),
        ("UBL-CUSTOMIZATION-001", "CustomizationID", "./cbc:CustomizationID", lambda: _has_text(root, "./cbc:CustomizationID")),
        ("UBL-PROFILE-001", "ProfileID", "./cbc:ProfileID", lambda: _has_text(root, "./cbc:ProfileID")),
        ("UBL-ID-001", "Invoice ID", "./cbc:ID", lambda: _has_text(root, "./cbc:ID")),
        ("UBL-DATE-001", "Issue date", "./cbc:IssueDate", lambda: _has_text(root, "./cbc:IssueDate")),
        ("UBL-CURRENCY-001", "Document currency code", "./cbc:DocumentCurrencyCode", lambda: _has_text(root, "./cbc:DocumentCurrencyCode")),
        ("UBL-SUPPLIER-001", "Accounting supplier party", "./cac:AccountingSupplierParty", lambda: _exists(root, "./cac:AccountingSupplierParty/cac:Party")),
        ("UBL-CUSTOMER-001", "Accounting customer party", "./cac:AccountingCustomerParty", lambda: _exists(root, "./cac:AccountingCustomerParty/cac:Party")),
        ("UBL-TAX-001", "Tax total", "./cac:TaxTotal", lambda: _exists(root, "./cac:TaxTotal")),
        ("UBL-TOTAL-001", "Legal monetary total", "./cac:LegalMonetaryTotal", lambda: _exists(root, "./cac:LegalMonetaryTotal")),
        ("UBL-LINE-001", "At least one invoice line", "./cac:InvoiceLine", lambda: bool(root.findall("./cac:InvoiceLine", NS))),
    ]
    return _result_from_checks("Basic UBL invoice structure checks", "ubl_structure", checks)


def validate_peppol_readiness(root: ET.Element) -> XMLValidatorResult:
    checks = [
        (
            "PEPPOL-ENDPOINT-001",
            "Seller EndpointID",
            "./cac:AccountingSupplierParty/cac:Party/cbc:EndpointID",
            lambda: _has_text(root, "./cac:AccountingSupplierParty/cac:Party/cbc:EndpointID"),
        ),
        (
            "PEPPOL-ENDPOINT-002",
            "Buyer EndpointID",
            "./cac:AccountingCustomerParty/cac:Party/cbc:EndpointID",
            lambda: _has_text(root, "./cac:AccountingCustomerParty/cac:Party/cbc:EndpointID"),
        ),
        (
            "PEPPOL-ENDPOINT-003",
            "Seller EndpointID schemeID",
            "./cac:AccountingSupplierParty/cac:Party/cbc:EndpointID/@schemeID",
            lambda: _has_attribute(root, "./cac:AccountingSupplierParty/cac:Party/cbc:EndpointID", "schemeID"),
        ),
        (
            "PEPPOL-ENDPOINT-004",
            "Buyer EndpointID schemeID",
            "./cac:AccountingCustomerParty/cac:Party/cbc:EndpointID/@schemeID",
            lambda: _has_attribute(root, "./cac:AccountingCustomerParty/cac:Party/cbc:EndpointID", "schemeID"),
        ),
        (
            "PEPPOL-REFERENCE-001",
            "Buyer reference or purchase order reference",
            "./cbc:BuyerReference | ./cac:OrderReference/cbc:ID",
            lambda: _has_text(root, "./cbc:BuyerReference") or _has_text(root, "./cac:OrderReference/cbc:ID"),
        ),
        (
            "PEPPOL-VAT-001",
            "VAT category information",
            ".//cac:ClassifiedTaxCategory/cbc:ID",
            lambda: _has_text(root, ".//cac:ClassifiedTaxCategory/cbc:ID") or _has_text(root, ".//cac:TaxCategory/cbc:ID"),
        ),
        (
            "PEPPOL-VAT-002",
            "VAT rate information",
            ".//cac:ClassifiedTaxCategory/cbc:Percent",
            lambda: _has_text(root, ".//cac:ClassifiedTaxCategory/cbc:Percent") or _has_text(root, ".//cac:TaxCategory/cbc:Percent"),
        ),
        (
            "PEPPOL-PAYABLE-001",
            "Payable amount",
            "./cac:LegalMonetaryTotal/cbc:PayableAmount",
            lambda: _has_text(root, "./cac:LegalMonetaryTotal/cbc:PayableAmount"),
        ),
    ]
    return _result_from_checks("Peppol readiness checks", "peppol_readiness", checks)


def _result_from_checks(
    validator_name: str,
    validator_type: str,
    checks: list[tuple[str, str, str, Callable[[], bool]]],
) -> XMLValidatorResult:
    errors: list[XMLValidationMessage] = []
    for code, label, location, predicate in checks:
        if not predicate():
            errors.append(
                XMLValidationMessage(
                    code=code,
                    message=f"Missing or invalid {label}.",
                    location=location,
                )
            )

    return XMLValidatorResult(
        validator_name=validator_name,
        validator_type=validator_type,
        status="failed" if errors else "passed",
        errors=errors,
        informational_messages=[f"{validator_name} passed."] if not errors else [],
        executed_at=_now(),
        artefact_version="Milestone 6A local readiness checks",
    )


def _exists(root: ET.Element, path: str) -> bool:
    return root.find(path, NS) is not None


def _has_text(root: ET.Element, path: str) -> bool:
    element = root.find(path, NS)
    return element is not None and element.text is not None and element.text.strip() != ""


def _has_attribute(root: ET.Element, path: str, attribute: str) -> bool:
    element = root.find(path, NS)
    return element is not None and element.attrib.get(attribute, "").strip() != ""


def _has_namespace(root: ET.Element, namespace: str) -> bool:
    prefix = f"{{{namespace}}}"
    return any(element.tag.startswith(prefix) for element in root.iter())


def _qname(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
