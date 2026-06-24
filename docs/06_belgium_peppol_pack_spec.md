# 06 — Belgium / Peppol Pack Spec

## Pack summary

| Item | Decision |
|---|---|
| Pack ID | `belgium_peppol` |
| Display name | Belgium / Peppol BIS Billing 3.0 |
| Country code | `BE` |
| V1 support level | `generator_basic` initially |
| Target V1 scenario | Domestic Belgian B2B services invoice |
| Syntax | UBL Invoice XML |
| Profile | Peppol BIS Billing 3.0 |
| Live delivery | Out of scope |
| PDF | Not required |
| QR | Not required |
| Signature | Not required in V1 |

## V1 boundary

Belgium V1 generates and validates Peppol-style UBL XML only. It does not transmit through Peppol, connect to an access point, submit to Mercurius, check participant registration, or guarantee live acceptance.

## Status

```json
{
  "country_pack_id": "belgium_peppol",
  "pack_version": "0.6.0",
  "support_level": "generator_basic",
  "peppol_xslt_status": "uploaded",
  "cen_en16931_xslt_status": "uploaded",
  "ubl_xsd_status": "partial_inconsistent_bundle_do_not_enable_xsd_validation_yet",
  "legal_invoice_requirements_status": "draft_supported_by_secondary_sources_pending_primary_source"
}
```

## Source material status

Available source materials discussed/collected include:

- OpenPeppol country-specific validation policy PDF.
- `PEPPOL-EN16931-UBL.sch`.
- `PEPPOL-EN16931-UBL.xslt`.
- `CEN-EN16931-UBL.xslt`.
- Partial UBL 2.1 XSD files.
- Belgium e-invoicing portal and EU Digital Building Blocks references.

The UBL XSD bundle must not be treated as clean until a complete single-source UBL 2.1 schema folder is installed and compiles.

## Output profile

```json
{
  "profile_id": "peppol_bis_billing_3_0_ubl_invoice",
  "description": "Peppol BIS Billing 3.0 UBL Invoice XML for Belgium V1 demo",
  "outputs": ["invoice.xml", "canonical_invoice.json", "validation_report.json", "evidence_bundle.zip"],
  "live_delivery": false
}
```

## Required V1 scenario

Belgian supplier to Belgian VAT-registered business customer:

- domestic Belgian B2B;
- services;
- EUR;
- 21% VAT;
- standard invoice;
- one VAT rate;
- buyer reference present;
- Peppol endpoint IDs either present or warning acknowledged.

## Belgium-specific workbook requirements

### `invoice_header`

- `buyer_reference` is required if `purchase_order_reference` is blank.
- `purchase_order_reference` is required if `buyer_reference` is blank.
- `invoice_currency_code` required.
- `tax_currency_code` conditional if VAT accounting currency differs.

### `entities` and `customers`

- `peppol_id` and `peppol_scheme_id` are warning-ack-required in V1 if missing.
- For Belgian enterprise number Peppol endpoints, scheme ID is usually `0208`.

## Mapping highlights

| Canonical field | UBL target |
|---|---|
| `invoice.invoice_number` | `cbc:ID` |
| `invoice.invoice_date` | `cbc:IssueDate` |
| `invoice.due_date` | `cbc:DueDate` |
| `invoice.invoice_type_code` | `cbc:InvoiceTypeCode` |
| `invoice.invoice_currency_code` | `cbc:DocumentCurrencyCode` |
| `invoice.tax_currency_code` | `cbc:TaxCurrencyCode` |
| `invoice.buyer_reference` | `cbc:BuyerReference` |
| `seller.peppol_id` | `cac:AccountingSupplierParty/cac:Party/cbc:EndpointID` |
| `buyer.peppol_id` | `cac:AccountingCustomerParty/cac:Party/cbc:EndpointID` |
| `seller.tax_registration_number` | `cac:PartyTaxScheme/cbc:CompanyID` |
| `buyer.tax_registration_number` | `cac:PartyTaxScheme/cbc:CompanyID` |
| line net amount | `cac:InvoiceLine/cbc:LineExtensionAmount` |
| tax summary | `cac:TaxTotal/cac:TaxSubtotal` |
| totals | `cac:LegalMonetaryTotal` |

## Validation rules

### Legal invoice rules

- Invoice number required and unique within upload.
- Issue date required.
- Supplier legal name/address/VAT ID required.
- Buyer legal name/address/VAT ID required for V1 B2B.
- Line description required.
- Quantity required.
- Unit price excluding VAT required.
- VAT rate and VAT amount required where VAT applies.
- VAT totals must reconcile.
- Exemption/reverse charge text required where applicable.
- If invoice currency is not EUR and Belgian VAT is charged, total VAT in EUR is required.

### Peppol rules

- `CustomizationID` must be Peppol BIS Billing 3.0 compliant.
- `ProfileID` must be Peppol billing process ID.
- Invoice type code must be valid.
- Either buyer reference or PO reference must be present.
- Seller endpoint ID warning in V1 if missing.
- Buyer endpoint ID warning in V1 if missing.
- VAT category codes must be valid.
- Unit codes must be valid.

## Rounding

Belgium must not rely only on line-level VAT summation. VAT should be validated at the total per VAT rate/category level.

```json
{
  "rounding_policy": {
    "tax_rounding_level": "total_per_vat_rate",
    "line_level_vat_rounding_allowed": false
  }
}
```

## Golden sample: `BE-VALID-001`

- Seller: Demo Belgium Services BV
- Seller VAT: `BE0123456789`
- Seller Peppol ID: `0208:0123456789`
- Buyer: Demo Belgium Buyer NV
- Buyer VAT: `BE0987654321`
- Buyer Peppol ID: `0208:0987654321`
- Invoice number: `INV-BE-2026-001`
- Invoice date: `2026-06-24`
- Currency: EUR
- Buyer reference: `BE-BUYER-REF-001`
- Line: Consulting services
- Quantity: 10
- Unit code: `HUR`
- Unit price: 100.00
- Net: 1000.00
- VAT 21%: 210.00
- Gross: 1210.00

## Failure tests

- Missing invoice number.
- Duplicate invoice number.
- Missing seller VAT.
- Missing buyer VAT for Belgian B2B.
- Missing both buyer reference and purchase order reference.
- VAT totals mismatch.
- Invalid VAT category code.
- Missing Peppol IDs should trigger acknowledgement warning, not block V1 generation.
- Attempt live Peppol submission should be unsupported.

## UI warning

> Belgium V1 generates Peppol-style UBL XML only. It does not transmit through Peppol, connect to an access point, submit to Mercurius, or confirm live delivery.
