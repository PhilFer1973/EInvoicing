from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
from typing import Any

from playwright.sync_api import Error as PlaywrightError, sync_playwright

from app.models.canonical import CanonicalInvoice


SAUDI_LABELS = {
    "title": "فاتورة ضريبية / Tax Invoice",
    "invoice_number": "رقم الفاتورة / Invoice Number",
    "issue_date": "تاريخ الإصدار / Issue Date",
    "issue_time": "وقت الإصدار / Issue Time",
    "currency": "العملة / Currency",
    "seller": "البائع / Seller",
    "buyer": "المشتري / Buyer",
    "vat_number": "الرقم الضريبي / VAT Registration Number",
    "description": "الوصف / Description",
    "quantity": "الكمية / Quantity",
    "unit_price": "سعر الوحدة / Unit Price",
    "net": "الصافي / Net",
    "tax": "الضريبة / Tax",
    "gross": "الإجمالي / Gross",
    "total_including_vat": "الإجمالي شامل ضريبة القيمة المضافة / Total Including VAT",
    "qr_code": "رمز الاستجابة السريعة / QR Code",
}

OFFLINE_BOUNDARY_FOOTER = (
    "Generated in offline demo mode. Not submitted to ZATCA/FATOORA. "
    "No ZATCA clearance stamp. Not production-signed."
)


class SaudiVisualPdfError(RuntimeError):
    """Raised when local Chromium is not available for deterministic PDF rendering."""


def generate_saudi_visual_invoice_pdf(canonical: CanonicalInvoice, qr_png: bytes) -> bytes:
    """Render a deterministic visual PDF; it is deliberately not a PDF/A-3 e-invoice."""
    qr_data_url = f"data:image/png;base64,{base64.b64encode(qr_png).decode('ascii')}"
    html = _render_html(canonical, qr_data_url)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1240, "height": 1754})
                page.set_content(html, wait_until="load")
                return page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "14mm", "right": "14mm", "bottom": "18mm", "left": "14mm"},
                )
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise SaudiVisualPdfError(
            "Saudi visual PDF rendering is not configured. Run 'python -m playwright install chromium' in server/.venv."
        ) from exc


def _render_html(canonical: CanonicalInvoice, qr_data_url: str) -> str:
    invoice = canonical.invoice
    seller = canonical.seller
    buyer = canonical.buyer
    totals = canonical.totals
    currency = _text(invoice.get("invoice_currency_code") or "SAR")

    line_rows = "".join(
        "<tr>"
        f"<td>{_line_description(line)}</td>"
        f"<td class=\"number\">{escape(_quantity(line.get('quantity')))}</td>"
        f"<td class=\"number\">{escape(_money(line.get('unit_price')))}</td>"
        f"<td class=\"number\">{escape(_money(line.get('line_net_amount')))}</td>"
        "</tr>"
        for line in canonical.lines
    ) or "<tr><td colspan=\"4\">No invoice lines</td></tr>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <style>
    @page {{ size: A4; margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{ color: #15182A; font-family: Arial, Tahoma, sans-serif; font-size: 11px; margin: 0; }}
    .page {{ min-height: 100%; padding: 0; }}
    .header {{ align-items: flex-start; border-bottom: 2px solid #46D8E0; display: flex; justify-content: space-between; padding-bottom: 14px; }}
    .title {{ color: #174D96; font-size: 24px; font-weight: 700; margin: 0 0 5px; }}
    .subtitle {{ color: #5E6378; margin: 0; }}
    .qr {{ text-align: center; width: 128px; }}
    .qr img {{ display: block; height: 104px; margin: 0 auto 5px; width: 104px; }}
    .qr span {{ color: #33384C; font-size: 9px; font-weight: 700; }}
    .metadata {{ display: grid; gap: 8px; grid-template-columns: 1.7fr 1fr 1fr 0.75fr; margin: 16px 0; }}
    .field {{ background: #F6F5FF; border: 1px solid #DDD9F4; border-radius: 6px; min-height: 53px; padding: 8px 10px; }}
    .label {{ color: #5E6378; display: block; font-size: 9px; margin-bottom: 5px; }}
    .value {{ color: #15182A; display: block; font-size: 12px; font-weight: 700; }}
    .parties {{ display: grid; gap: 12px; grid-template-columns: 1fr 1fr; margin: 14px 0 18px; }}
    .party {{ border: 1px solid #DDD9F4; border-radius: 6px; min-height: 120px; padding: 12px; }}
    .party h2 {{ color: #174D96; font-size: 13px; margin: 0 0 9px; }}
    .party p {{ line-height: 1.45; margin: 2px 0; }}
    table {{ border-collapse: collapse; margin-top: 8px; width: 100%; }}
    th {{ background: #EDEAFB; color: #33384C; font-size: 9px; font-weight: 700; padding: 8px; text-align: left; }}
    td {{ border-bottom: 1px solid #E5E3EF; padding: 9px 8px; vertical-align: top; }}
    .number {{ text-align: right; white-space: nowrap; }}
    .line-description-bilingual {{ align-items: baseline; display: grid; gap: 8px; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
    .line-description-ar {{ direction: rtl; font-weight: 700; text-align: right; }}
    .line-description-en {{ color: #5E6378; text-align: left; }}
    .totals {{ margin-left: auto; margin-top: 16px; width: 48%; }}
    .total {{ border-bottom: 1px solid #E5E3EF; display: flex; justify-content: space-between; padding: 8px 4px; }}
    .total strong {{ color: #174D96; }}
    .total.gross {{ background: #E5F8F7; border: 1px solid #A9E7E4; border-radius: 6px; margin-top: 6px; padding: 10px 9px; }}
    .footer {{ border-top: 1px solid #E5E3EF; color: #5E6378; font-size: 9px; line-height: 1.4; margin-top: 30px; padding-top: 10px; }}
  </style>
</head>
<body>
  <main class=\"page\">
    <section class=\"header\">
      <div>
        <h1 class=\"title\">{SAUDI_LABELS['title']}</h1>
        <p class=\"subtitle\">Offline demo visual invoice - not a formal PDF/A-3 e-invoice</p>
      </div>
      <div class=\"qr\"><img alt=\"QR Code\" src=\"{qr_data_url}\"><span>{SAUDI_LABELS['qr_code']}</span></div>
    </section>
    <section class=\"metadata\">
      {_field(SAUDI_LABELS['invoice_number'], invoice.get('invoice_number'))}
      {_field(SAUDI_LABELS['issue_date'], invoice.get('invoice_date'))}
      {_field(SAUDI_LABELS['issue_time'], invoice.get('invoice_time'))}
      {_field(SAUDI_LABELS['currency'], currency)}
    </section>
    <section class=\"parties\">
      {_party(SAUDI_LABELS['seller'], seller)}
      {_party(SAUDI_LABELS['buyer'], buyer)}
    </section>
    <table>
      <thead><tr>
        <th>{SAUDI_LABELS['description']}</th>
        <th class=\"number\">{SAUDI_LABELS['quantity']}</th>
        <th class=\"number\">{SAUDI_LABELS['unit_price']}</th>
        <th class=\"number\">{SAUDI_LABELS['net']}</th>
      </tr></thead>
      <tbody>{line_rows}</tbody>
    </table>
    <section class=\"totals\">
      <div class=\"total\"><span>{SAUDI_LABELS['net']}</span><strong>{_money(totals.get('net_total'))} {currency}</strong></div>
      <div class=\"total\"><span>{SAUDI_LABELS['tax']}</span><strong>{_money(totals.get('tax_total'))} {currency}</strong></div>
      <div class=\"total gross\"><span>{SAUDI_LABELS['total_including_vat']} / Gross</span><strong>{_money(totals.get('gross_total'))} {currency}</strong></div>
    </section>
    <footer class=\"footer\">{OFFLINE_BOUNDARY_FOOTER}</footer>
  </main>
</body>
</html>"""


def _field(label: str, value: Any) -> str:
    return f'<div class="field"><span class="label">{label}</span><span class="value">{escape(_text(value))}</span></div>'


def _line_description(line: dict[str, Any]) -> str:
    english = _text(line.get("description") or line.get("item_name"))
    arabic = _text(line.get("description_ar") or line.get("description_arabic")).strip()
    if not arabic:
        return escape(english)
    return (
        '<div class="line-description-bilingual">'
        f'<span class="line-description-en">{escape(english)}</span>'
        f'<span class="line-description-ar" dir="rtl" lang="ar">{escape(arabic)}</span>'
        "</div>"
    )


def _party(label: str, party: dict[str, Any]) -> str:
    address_parts = [party.get("address_line_1"), party.get("city"), party.get("postal_code"), party.get("country_name")]
    address = ", ".join(_text(part) for part in address_parts if _text(part))
    return (
        '<article class="party">'
        f"<h2>{label}</h2>"
        f"<p><strong>{escape(_text(party.get('legal_name')))}</strong></p>"
        f"<p>{escape(SAUDI_LABELS['vat_number'])}: {escape(_text(party.get('tax_registration_number')))}</p>"
        f"<p>{escape(address)}</p>"
        "</article>"
    )


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _quantity(value: Any) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return _text(value)
    if amount == amount.to_integral():
        return str(amount.quantize(Decimal("1")))
    return str(amount.normalize())


def _money(value: Any) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "0.00"
    return f"{amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"
