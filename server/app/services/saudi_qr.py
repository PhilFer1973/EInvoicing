from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from typing import Any

import qrcode

from app.models.canonical import CanonicalInvoice


@dataclass(frozen=True)
class SaudiPhaseOneQr:
    payload_base64: str
    png_bytes: bytes
    decoded_payload: dict[str, Any]


QR_TAG_DETAILS = {
    1: ("Seller name", "seller_name"),
    2: ("Seller VAT/TIN", "seller_vat_tin"),
    3: ("Invoice timestamp", "invoice_timestamp"),
    4: ("Invoice total including VAT", "invoice_total_including_vat"),
    5: ("VAT total", "vat_total"),
}


def generate_saudi_phase_one_qr(canonical: CanonicalInvoice) -> SaudiPhaseOneQr:
    """Build the offline Saudi Phase One QR payload from canonical invoice data only."""
    payload = encode_tlv(
        [
            (1, _required_text(canonical.seller.get("legal_name"), "seller legal name")),
            (2, _required_text(canonical.seller.get("tax_registration_number"), "seller VAT/TIN")),
            (3, _invoice_timestamp(canonical.invoice)),
            (4, _money(canonical.totals.get("gross_total"))),
            (5, _money(canonical.totals.get("tax_total"))),
        ]
    )
    payload_base64 = base64.b64encode(payload).decode("ascii")

    image = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    image.add_data(payload_base64)
    image.make(fit=True)
    buffer = BytesIO()
    image.make_image(fill_color="#15182A", back_color="white").save(buffer, format="PNG")

    return SaudiPhaseOneQr(
        payload_base64=payload_base64,
        png_bytes=buffer.getvalue(),
        decoded_payload=validate_saudi_phase_one_qr_payload(canonical, payload_base64),
    )


def encode_tlv(fields: list[tuple[int, str]]) -> bytes:
    encoded = bytearray()
    for tag, value in fields:
        if not 0 < tag < 256:
            raise ValueError("Saudi QR tags must fit in one byte.")
        value_bytes = value.encode("utf-8")
        if len(value_bytes) > 255:
            raise ValueError("Saudi QR field values must fit in a one-byte length.")
        encoded.extend((tag, len(value_bytes)))
        encoded.extend(value_bytes)
    return bytes(encoded)


def decode_tlv_payload(payload_base64: str) -> list[tuple[int, str]]:
    """Decode a generated payload for deterministic tests and evidence inspection."""
    payload = base64.b64decode(payload_base64, validate=True)
    fields: list[tuple[int, str]] = []
    index = 0
    while index < len(payload):
        if index + 2 > len(payload):
            raise ValueError("Saudi QR payload ends before a complete TLV field header.")
        tag = payload[index]
        length = payload[index + 1]
        value_start = index + 2
        value_end = value_start + length
        if value_end > len(payload):
            raise ValueError("Saudi QR payload length exceeds the available bytes.")
        fields.append((tag, payload[value_start:value_end].decode("utf-8")))
        index = value_end
    return fields


def validate_saudi_phase_one_qr_payload(canonical: CanonicalInvoice, payload_base64: str) -> dict[str, Any]:
    """Verify the generated QR is precisely the canonical-data Phase One tag set."""
    fields = decode_tlv_payload(payload_base64)
    tags = [tag for tag, _ in fields]
    expected_tags = list(QR_TAG_DETAILS)
    if tags != expected_tags:
        raise ValueError("Saudi QR must contain Phase One tags 1-5 only, in order.")

    actual = dict(fields)
    expected = {
        1: _required_text(canonical.seller.get("legal_name"), "seller legal name"),
        2: _required_text(canonical.seller.get("tax_registration_number"), "seller VAT/TIN"),
        3: _invoice_timestamp(canonical.invoice),
        4: _money(canonical.totals.get("gross_total")),
        5: _money(canonical.totals.get("tax_total")),
    }
    for tag, expected_value in expected.items():
        if actual[tag] != expected_value:
            label = QR_TAG_DETAILS[tag][0]
            raise ValueError(f"Saudi QR {label} does not match the canonical invoice.")

    return {
        "encoding": "base64_tlv_utf8",
        "phase": "phase_1_tags_1_to_5",
        "phase_two_tags_included": False,
        "tags": [
            {
                "tag": tag,
                "label": QR_TAG_DETAILS[tag][0],
                "field": QR_TAG_DETAILS[tag][1],
                "value": actual[tag],
            }
            for tag in expected_tags
        ],
    }


def _invoice_timestamp(invoice: dict[str, Any]) -> str:
    invoice_date = _required_text(invoice.get("invoice_date"), "invoice date")
    invoice_time = _required_text(invoice.get("invoice_time"), "invoice time")
    return f"{invoice_date}T{invoice_time}"


def _required_text(value: Any, field_name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"Saudi QR requires {field_name}.")
    return text


def _money(value: Any) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Saudi QR requires a valid monetary total.") from exc
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
