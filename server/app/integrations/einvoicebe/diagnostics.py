from __future__ import annotations

from xml.etree import ElementTree as ET


NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def build_sender_identity_check(
    *,
    tenant_peppol_id: str,
    xml_bytes: bytes | None,
    send_request_sender_peppol_id: str | None = None,
) -> dict:
    tenant_scheme, tenant_id = split_peppol_id(tenant_peppol_id)
    sender_scheme, sender_id = split_peppol_id(send_request_sender_peppol_id)
    xml_identity = extract_xml_seller_identity(xml_bytes)

    return {
        "tenant_owned_sender_peppol_id": tenant_peppol_id,
        "tenant_sender_scheme": tenant_scheme,
        "tenant_sender_id": tenant_id,
        "xml_seller_endpoint_scheme": xml_identity["endpoint_scheme"],
        "xml_seller_endpoint_id": xml_identity["endpoint_id"],
        "xml_seller_party_legal_company_id": xml_identity["legal_company_id"],
        "xml_seller_tax_scheme_company_id": xml_identity["tax_company_id"],
        "send_request_sender_source": "explicit_query_parameter" if send_request_sender_peppol_id else "omitted_provider_tenant_inferred",
        "send_request_sender_scheme": sender_scheme,
        "send_request_sender_id": sender_id,
        "xml_sender_matches_tenant": _matches(tenant_scheme, tenant_id, xml_identity["endpoint_scheme"], xml_identity["endpoint_id"]),
        "send_request_sender_matches_tenant": (
            _matches(tenant_scheme, tenant_id, sender_scheme, sender_id)
            if sender_scheme is not None or sender_id is not None
            else None
        ),
    }


def extract_xml_seller_identity(xml_bytes: bytes | None) -> dict[str, str | None]:
    if not xml_bytes:
        return {
            "endpoint_scheme": None,
            "endpoint_id": None,
            "legal_company_id": None,
            "tax_company_id": None,
        }

    root = ET.fromstring(xml_bytes)
    party = root.find("./cac:AccountingSupplierParty/cac:Party", NS)
    if party is None:
        return {
            "endpoint_scheme": None,
            "endpoint_id": None,
            "legal_company_id": None,
            "tax_company_id": None,
        }

    endpoint = party.find("./cbc:EndpointID", NS)
    legal_company = party.find("./cac:PartyLegalEntity/cbc:CompanyID", NS)
    tax_company = party.find("./cac:PartyTaxScheme/cbc:CompanyID", NS)
    return {
        "endpoint_scheme": endpoint.attrib.get("schemeID") if endpoint is not None else None,
        "endpoint_id": _text(endpoint),
        "legal_company_id": _text(legal_company),
        "tax_company_id": _text(tax_company),
    }


def split_peppol_id(peppol_id: str | None) -> tuple[str | None, str | None]:
    if not peppol_id or ":" not in peppol_id:
        return None, None
    scheme, identifier = peppol_id.split(":", 1)
    scheme = scheme.strip()
    identifier = identifier.strip()
    return (scheme or None), (identifier or None)


def _matches(
    expected_scheme: str | None,
    expected_id: str | None,
    actual_scheme: str | None,
    actual_id: str | None,
) -> bool:
    return bool(expected_scheme and expected_id and actual_scheme == expected_scheme and actual_id == expected_id)


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None
