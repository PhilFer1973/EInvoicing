from __future__ import annotations

from typing import Any

from app.integrations.storecove.schemas import StorecoveConfig, StorecoveLine, StorecoveParty, StorecoveSandboxRequest
from app.models.canonical import CanonicalInvoice


def map_canonical_to_storecove_request(
    canonical: CanonicalInvoice,
    config: StorecoveConfig,
) -> StorecoveSandboxRequest:
    invoice = canonical.invoice
    seller = canonical.seller
    buyer = canonical.buyer

    return StorecoveSandboxRequest(
        external_id=_as_text(invoice.get("invoice_number")),
        sender=_party_from_canonical(seller, config.sender_legal_entity_id),
        receiver=_party_from_canonical(buyer, config.receiver_legal_entity_id),
        invoice={
            "invoice_number": _as_text(invoice.get("invoice_number")),
            "invoice_date": _as_text(invoice.get("invoice_date")),
            "due_date": _as_text(invoice.get("due_date")),
            "invoice_type": _as_text(invoice.get("invoice_type")),
            "invoice_type_code": _as_text(invoice.get("invoice_type_code") or "380"),
            "currency": _as_text(invoice.get("invoice_currency_code")),
            "buyer_reference": _as_text(invoice.get("buyer_reference")),
            "purchase_order_reference": _as_text(invoice.get("purchase_order_reference")),
        },
        totals={
            "net_total": _money(canonical.totals.get("net_total")),
            "tax_total": _money(canonical.totals.get("tax_total")),
            "gross_total": _money(canonical.totals.get("gross_total")),
            "payable_amount": _money(canonical.totals.get("payable_amount") or canonical.totals.get("gross_total")),
        },
        tax_summary=[
            {
                "tax_category_code": summary.tax_category_code,
                "tax_rate": summary.tax_rate,
                "taxable_amount": summary.taxable_amount,
                "tax_amount": summary.tax_amount,
            }
            for summary in canonical.tax_summary
        ],
        lines=[
            StorecoveLine(
                line_number=_as_text(line.get("line_number")),
                description=_as_text(line.get("description") or line.get("item_name")),
                quantity=_as_text(line.get("quantity")),
                unit_code=_as_text(line.get("unit_code")),
                unit_price=_money(line.get("unit_price")),
                net_amount=_money(line.get("line_net_amount")),
                tax_category_code=_as_text(line.get("tax_category_code")),
                tax_rate=_as_text(line.get("tax_rate")),
                tax_amount=_money(line.get("tax_amount")),
            )
            for line in canonical.lines
        ],
    )


def _party_from_canonical(party: dict[str, Any], legal_entity_id: str) -> StorecoveParty:
    return StorecoveParty(
        legal_entity_id=legal_entity_id,
        name=_as_text(party.get("legal_name")),
        country_code=_as_text(party.get("country_code")),
        tax_registration_number=_as_text(party.get("tax_registration_number")),
    )


def _money(value: Any) -> str:
    if value in (None, ""):
        return "0.00"
    return f"{float(value):.2f}"


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)

