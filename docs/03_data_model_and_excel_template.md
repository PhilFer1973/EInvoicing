# 03 — Data Model and Excel Template

## V1 workbook structure

The V1 upload workbook has exactly four sheets:

```text
entities
customers
invoice_header
invoice_lines
```

No manual invoice editing is supported in V1. If validation fails, the user corrects the Excel file and uploads again.

## Global conventions

- One invoice per workbook in V1.
- Dates use `YYYY-MM-DD`.
- Times use `HH:mm:ss`.
- Currency codes use ISO 4217 alpha-3.
- Country codes use ISO 3166-1 alpha-2.
- Amounts are decimal strings or numeric values with up to two decimals unless the specific field permits more.
- ERP is responsible for tax treatment. The app validates supplied treatment; it does not determine tax.

## Sheet: `entities`

Represents the issuing entity / seller.

| Field | Required globally | Notes |
|---|---:|---|
| `entity_id` | Yes | Stable ID used by invoice header. |
| `legal_name` | Yes | Seller legal name. |
| `trading_name` | No | Optional. |
| `country_code` | Yes | ISO alpha-2. |
| `tax_registration_number` | Yes | VAT/TIN where applicable. |
| `legal_registration_number` | Conditional | Useful for Peppol legal entity and Saudi identity. |
| `legal_registration_scheme_id` | Conditional | Example Belgium Peppol scheme `0208`. |
| `address_line_1` | Yes | Street / address. |
| `address_line_2` | No | Optional. |
| `building_number` | Conditional | Important for Saudi. |
| `district` | Conditional | Important for Saudi. |
| `additional_number` | Conditional | Saudi address support. |
| `city` | Yes | City. |
| `province_or_state` | Conditional | Saudi address support. |
| `postal_code` | Conditional | Required for many packs. |
| `country_name` | No | Display only. |
| `email` | No | Optional. |
| `phone` | No | Optional. |
| `iban` | No | Payment account. |
| `bic` | No | Payment account. |
| `payment_account_name` | No | Name on account. |
| `peppol_id` | Belgium warning | Required for live Peppol delivery, warning in V1. |
| `peppol_scheme_id` | Belgium warning | Belgian enterprise number scheme usually `0208`. |

## Sheet: `customers`

Represents the buyer.

| Field | Required globally | Notes |
|---|---:|---|
| `customer_id` | Yes | Stable ID used by invoice header. |
| `legal_name` | Yes | Buyer legal name. |
| `buyer_type` | Yes | `business`, `government`, `consumer`. V1 supports business/government. |
| `country_code` | Yes | ISO alpha-2. |
| `tax_registration_number` | Conditional | Required for V1 Belgium/Saudi B2B. |
| `legal_registration_number` | Conditional | Peppol/Saudi support. |
| `legal_registration_scheme_id` | Conditional | Scheme for legal registration. |
| `address_line_1` | Yes | Street / address. |
| `address_line_2` | No | Optional. |
| `building_number` | Conditional | Saudi. |
| `district` | Conditional | Saudi. |
| `additional_number` | Conditional | Saudi. |
| `city` | Yes | City. |
| `province_or_state` | Conditional | Saudi. |
| `postal_code` | Conditional | Required by country. |
| `country_name` | No | Display only. |
| `email` | No | Optional. |
| `peppol_id` | Belgium warning | Required for live Peppol delivery, warning in V1. |
| `peppol_scheme_id` | Belgium warning | Belgian enterprise number scheme usually `0208`. |

## Sheet: `invoice_header`

| Field | Required globally | Notes |
|---|---:|---|
| `invoice_id` | Yes | Internal invoice key. |
| `invoice_number` | Yes | Legal invoice number. |
| `invoice_date` | Yes | `YYYY-MM-DD`. |
| `invoice_time` | Conditional | Required for Saudi. |
| `due_date` | Conditional | Peppol requires due date or terms where payable. |
| `tax_point_date` | Conditional | Used for legal/timing checks. |
| `entity_id` | Yes | Links to `entities`. |
| `customer_id` | Yes | Links to `customers`. |
| `invoice_type` | Yes | V1: `standard_sales_invoice`. |
| `invoice_type_code` | Conditional | Peppol often `380`; Saudi standard tax invoice uses `388`. |
| `invoice_type_transaction_code` | Conditional | Saudi `InvoiceTypeCode/@name`; V1 default standard tax invoice. |
| `supply_type` | Yes | V1: `services`. |
| `transaction_type` | Yes | Informational/preflight; app does not infer tax. |
| `selected_country_pack` | Yes | `belgium_peppol`, `saudi_zatca`, `uk_info`. |
| `selected_output_profile` | Yes | Country-specific output profile. |
| `invoice_currency_code` | Yes | Document currency. |
| `tax_currency_code` | Conditional | Saudi tax totals must be SAR; Belgium needs local VAT where applicable. |
| `exchange_rate_to_tax_currency` | Conditional | ERP-supplied if needed. |
| `exchange_rate_date` | Conditional | ERP-supplied. |
| `exchange_rate_source` | Conditional | ERP-supplied source note. |
| `net_total` | Yes | Invoice total excluding VAT. |
| `tax_total` | Yes | Invoice VAT total. |
| `gross_total` | Yes | Total including VAT. |
| `line_extension_total` | Derived/optional | Sum of line net amounts. |
| `tax_exclusive_total` | Derived/optional | Usually net total. |
| `tax_inclusive_total` | Derived/optional | Usually gross total. |
| `payable_amount` | Derived/optional | Usually gross total less prepaid amounts. |
| `net_total_tax_currency` | Conditional | Required if tax currency differs. |
| `tax_total_tax_currency` | Conditional | Required if tax currency differs. |
| `gross_total_tax_currency` | Conditional | Required if tax currency differs. |
| `buyer_reference` | Conditional | Belgium: required if no PO reference. |
| `purchase_order_reference` | Conditional | Belgium: required if no buyer reference. |
| `payment_means_code` | Optional | If PaymentMeans generated. |
| `payment_id` | Optional | Payment reference. |
| `payment_terms_note` | Conditional | If no due date and amount payable positive. |
| `uuid` | Conditional | Saudi; app can generate if blank. |
| `invoice_counter_value` | Saudi scaffold | Required for production Saudi chain, demo placeholder in V1. |
| `previous_invoice_hash` | Saudi scaffold | Production chain value; V1 placeholder/warning. |
| `erp_source_system` | Optional | Audit. |
| `erp_document_reference` | Optional | Audit. |
| `notes` | Optional | Can be translated for Saudi PDF. |

## Sheet: `invoice_lines`

| Field | Required globally | Notes |
|---|---:|---|
| `invoice_id` | Yes | Links to header. |
| `line_number` | Yes | Sequential line number. |
| `description` | Yes | Line description. |
| `item_name` | Conditional | UBL item name; can derive from description if blank. |
| `quantity` | Yes | Decimal quantity. |
| `unit_code` | Yes | Recommended UN/ECE unit code. |
| `unit_price` | Yes | Excluding VAT. |
| `line_net_amount` | Yes | Excluding VAT. |
| `tax_category_code` | Yes | Example `S`, `E`, `Z`, `O`. |
| `tax_rate` | Conditional | Required except where country rules allow omission. |
| `tax_amount` | Yes | ERP-calculated VAT amount. |
| `line_gross_amount` | Conditional | Required for Saudi visual PDF and validation clarity. |
| `line_net_amount_tax_currency` | Conditional | If tax currency differs. |
| `tax_amount_tax_currency` | Conditional | If tax currency differs. |
| `line_gross_amount_tax_currency` | Conditional | If tax currency differs. |
| `discount_amount` | Optional | Line discount already included in line net if used. |
| `discount_reason` | Conditional | Required if discount amount used. |
| `charge_amount` | Optional | Line charge if used. |
| `charge_reason` | Conditional | Required if charge amount used. |
| `exemption_reason_code` | Conditional | Required for Saudi non-standard categories. |
| `exemption_reason_text` | Conditional | Required for exempt/zero/out-of-scope treatment where applicable. |

## Canonical invoice model

The backend must convert workbook data to canonical JSON before country generation.

```json
{
  "invoice": {},
  "seller": {},
  "buyer": {},
  "lines": [],
  "tax_summary": [],
  "totals": {},
  "source": {},
  "metadata": {}
}
```

## Internal tax summary

The app must derive an internal tax summary by grouping lines by:

```text
tax_category_code + normalized_tax_rate
```

The app should not require a separate `tax_summary` sheet in V1, but the canonical model must contain a derived `tax_summary` array.

## Rounding policy

The validation engine must support country-specific rounding. Belgium and Saudi both require VAT validation at VAT category/document level rather than blindly summing rounded line VAT amounts.

## Translation handling for Saudi PDF

The canonical model should include a `translations` object for translated narrative fields.

Fixed statutory labels must come from a deterministic dictionary, not AI. OpenAI API translation may be used only for variable narrative text such as line descriptions and notes.

## Workbook template generation

Codex should generate a downloadable blank workbook template and a sample V1 workbook for each implemented pack. This can be built after the initial parser works.
