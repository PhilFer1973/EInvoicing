# 07 — Saudi Arabia / ZATCA Pack Spec

## Pack summary

| Item | Decision |
|---|---|
| Pack ID | `saudi_zatca` |
| Display name | Saudi Arabia / ZATCA |
| Country code | `SA` |
| V1 support level | `generator_basic` |
| Target V1 scenario | Saudi standard B2B tax invoice |
| Main output | ZATCA-style UBL XML |
| Visual output | Arabic/bilingual visual PDF with QR |
| QR | Phase-1-style QR tags 1–5 in V1 |
| Live clearance | Out of scope |
| Reporting | Out of scope |
| Production signing | Out of scope |

## V1 boundary

Saudi V1 generates ZATCA-style XML, Arabic/bilingual visual PDF, Phase-1-style QR and evidence bundle only.

It does not:

- submit to FATOORA;
- obtain clearance;
- obtain or apply ZATCA clearance stamp;
- create production CSID;
- create production cryptographic stamp;
- maintain production previous-invoice-hash chain;
- produce a live-valid Saudi B2B tax invoice.

## Status

```json
{
  "country_pack_id": "saudi_zatca",
  "pack_version": "0.3.0",
  "support_level": "generator_basic_ready_for_build",
  "xml_implementation_standard_status": "uploaded",
  "data_dictionary_status": "uploaded",
  "qr_specification_status": "uploaded",
  "security_features_status": "uploaded",
  "example_xml_status": "uploaded_for_reference_and_tests",
  "arabic_visual_pdf_status": "approved_for_v1",
  "live_clearance_status": "out_of_scope_v1",
  "production_signing_status": "out_of_scope_v1"
}
```

## Source materials

Use the following uploaded source files as implementation references:

- `20230519_ZATCA_Electronic_Invoice_XML_Implementation_Standard_ vF.pdf`
- `20230519_EInvoice_Data_Dictionary vF.xlsx`
- `EInvoice_Data_Dictionary.xlsx`
- `QRCodeCreation.pdf`
- `E-invoicing-Detailed-Technical-Guideline.pdf`
- `20220624_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards.pdf`
- `Standard_Invoice.xml`
- `Exempt Tax Invoice.xml`
- `Export invoice.xml`
- `Out of Scope Standard Tax Invoice.xml`
- `Third party billing.xml`

## Output profile

```json
{
  "profile_id": "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
  "outputs": [
    "invoice.xml",
    "invoice_arabic_bilingual_visual.pdf",
    "qr.png",
    "canonical_invoice.json",
    "translation_audit.json",
    "validation_report.json",
    "evidence_bundle.zip"
  ],
  "live_clearance": false,
  "production_signature": false,
  "zatca_clearance_stamp": false
}
```

## V1 scenario

Saudi supplier to Saudi VAT-registered business customer:

- standard tax invoice;
- B2B;
- services;
- SAR;
- 15% standard VAT;
- one invoice line;
- XML generated;
- Arabic/bilingual visual PDF generated;
- QR tags 1–5 generated;
- warnings acknowledged for non-clearance and non-production signing.

## Saudi-specific workbook requirements

### `invoice_header`

- `invoice_time` required.
- `uuid` required; app may generate if blank.
- `invoice_type_code` should be `388` for standard tax invoice.
- `invoice_type_transaction_code` should default to standard tax invoice, e.g. `0100000` depending mapping.
- `invoice_counter_value` scaffold field.
- `previous_invoice_hash` scaffold field.
- `tax_currency_code` should be `SAR` where required.

### `entities`

Saudi seller should include:

- legal name;
- VAT/TIN;
- Saudi address elements where available: building number, district, city, postal code, province/state, country code.

### `customers`

Saudi V1 B2B buyer should include:

- legal name;
- VAT/TIN;
- address elements.

### `invoice_lines`

- category `S` at 15% for V1 golden sample;
- exemption fields are reserved for future non-standard tests.

## XML structural items

Saudi examples show these important elements:

```text
ext:UBLExtensions
cbc:ProfileID
cbc:ID
cbc:UUID
cbc:IssueDate
cbc:IssueTime
cbc:InvoiceTypeCode
cbc:DocumentCurrencyCode
cbc:TaxCurrencyCode
cac:AdditionalDocumentReference[ICV]
cac:AdditionalDocumentReference[PIH]
cac:AdditionalDocumentReference[QR]
cac:Signature
cac:AccountingSupplierParty
cac:AccountingCustomerParty
cac:TaxTotal
cac:LegalMonetaryTotal
cac:InvoiceLine
```

V1 can generate scaffold/demo values for ICV/PIH/QR but must not claim production chain validity.

## QR V1

The V1 PDF and bundle should generate QR using TLV/Base64 with tags 1–5:

| Tag | Field |
|---:|---|
| 1 | Seller name |
| 2 | Seller VAT registration number |
| 3 | Invoice timestamp |
| 4 | Invoice total including VAT |
| 5 | VAT total |

Phase 2 fields are out of scope for production use:

| Tag | Field | V1 treatment |
|---:|---|---|
| 6 | XML invoice hash | Future / not production |
| 7 | ECDSA signature | Future / not production |
| 8 | ECDSA public key | Future / not production |
| 9 | ZATCA technical CA signature for simplified invoices | Future / not production |

## QR generation algorithm

```text
Start with empty byte array.
For each tag in order:
  tag byte = unsigned one-byte integer
  value bytes = UTF-8 encoded field value
  length byte = length of value bytes as unsigned one-byte integer
  append tag byte + length byte + value bytes
Base64 encode final byte array.
Generate QR image from Base64 string.
```

## Arabic/bilingual PDF

### Output

`invoice_arabic_bilingual_visual.pdf`

### Rendering method

Use HTML/CSS rendered through Playwright/Chromium. Do not use low-level PDF drawing for Arabic text unless Arabic shaping and right-to-left layout are explicitly handled.

### Layout

- Title: `فاتورة ضريبية / Tax Invoice`
- QR code top-right.
- Seller and buyer blocks.
- Invoice number, date and time.
- Bilingual line table.
- Totals block.
- Strong footer disclaimer.

### Fixed Arabic labels

Use deterministic dictionary for fixed labels, not AI translation.

```json
{
  "Tax Invoice": "فاتورة ضريبية",
  "Invoice Number": "رقم الفاتورة",
  "Issue Date": "تاريخ الإصدار",
  "Seller": "البائع",
  "Buyer": "المشتري",
  "VAT Registration Number": "الرقم الضريبي",
  "VAT": "ضريبة القيمة المضافة",
  "Total Including VAT": "الإجمالي شامل ضريبة القيمة المضافة",
  "QR Code": "رمز الاستجابة السريعة"
}
```

### AI translation boundary

OpenAI API may be used only for variable narrative text:

- invoice notes;
- line descriptions;
- payment terms;
- exemption explanation.

Store `translation_audit.json` containing source text, translated text, model, timestamp and review status.

## Saudi legal invoice rules

- Standard tax invoice only for V1.
- Issue date required.
- Issue time required.
- Invoice number required and unique.
- Supplier legal name required.
- Supplier VAT/TIN required.
- Supplier address required.
- Buyer legal name required for V1.
- Buyer VAT/TIN required for V1 B2B.
- Buyer address required for V1.
- Line description, quantity, unit price and net amount required.
- VAT category/rate/amount required.
- Total including VAT required.
- Arabic production compliance is not claimed in V1.

## Saudi VAT and rounding

```json
{
  "rounding_method": "half_up",
  "amount_decimals": 2,
  "vat_rounding_level": "vat_category_document_level",
  "line_vat_summation_is_not_sufficient": true,
  "tax_currency_default": "SAR"
}
```

## Code lists

V1 standard sample uses:

```json
{
  "invoice_type_code": "388",
  "vat_category_code": "S",
  "vat_rate": "15",
  "document_currency_code": "SAR",
  "tax_currency_code": "SAR"
}
```

Future supported VAT categories:

```json
{
  "vat_category_codes": ["S", "E", "Z", "O"],
  "saudi_exemption_reason_codes": [
    "VATEX-SA-29",
    "VATEX-SA-29-7",
    "VATEX-SA-30",
    "VATEX-SA-32",
    "VATEX-SA-33",
    "VATEX-SA-34-1",
    "VATEX-SA-34-2",
    "VATEX-SA-34-3",
    "VATEX-SA-34-4",
    "VATEX-SA-34-5",
    "VATEX-SA-35",
    "VATEX-SA-36",
    "VATEX-SA-EDU",
    "VATEX-SA-HEA",
    "VATEX-SA-MLTRY",
    "VATEX-SA-OOS"
  ]
}
```

## Security boundary

V1 does not implement production signing. However, the architecture should reserve support for:

- SHA-256 invoice hash;
- XAdES for XML;
- PAdES for PDF/A-3;
- previous invoice hash;
- CSID;
- FATOORA authentication.

These must be `out_of_scope_v1`.

## Golden sample: `SA-VALID-001`

- Seller: Demo Saudi Services LLC
- Seller VAT/TIN: `300000000000003`
- Buyer: Demo Saudi Buyer LLC
- Buyer VAT/TIN: `300000000000004`
- Invoice number: `INV-SA-2026-001`
- Invoice date: `2026-06-24`
- Invoice time: `10:30:00`
- Currency: SAR
- Tax currency: SAR
- Invoice type: Standard tax invoice
- Supply type: Services
- Quantity: 10
- Unit code: `HUR`
- Unit price: 1000.00
- Net: 10000.00
- VAT: 1500.00
- Gross: 11500.00

Expected:

- workbook validation passes;
- internal arithmetic passes;
- Saudi preflight passes;
- XML generated;
- QR generated with tags 1–5;
- Arabic/bilingual visual PDF generated;
- warning acknowledgement required;
- evidence bundle generated.

## Failure tests

- Missing invoice number.
- Missing invoice time.
- Missing supplier VAT/TIN.
- Missing buyer VAT/TIN.
- Invalid VAT rate.
- VAT totals mismatch.
- User selects production compliance mode.
- User attempts FATOORA submission.
- QR generation fails.
- Warning acknowledgement missing.

## Required UI warning

> This file has not been submitted to ZATCA/FATOORA and is not a cleared Saudi tax invoice. No ZATCA clearance stamp or production cryptographic stamp has been applied.
