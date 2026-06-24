

---

<!-- README.md -->

# E-Invoicing V1 Build Specification Pack

**Project:** E-Invoicing Workbench  
**GitHub repository:** https://github.com/PhilFer1973/EInvoicing  
**Local folder:** `C:\Users\Philip\Downloads\EInvoicing`  
**Prepared for:** Philip Fernandez  
**Purpose:** Codex-ready build pack for a V1 e-invoicing file generation and validation workbench.

## What this pack is

This pack converts the project research and design decisions into implementation documents for Codex. It deliberately locks the first build to a controlled V1 rather than trying to build a global compliance platform in one pass.

V1 implements:

- a local/web workbench for e-invoicing file generation and validation;
- upload of a fixed Excel workbook;
- canonical invoice JSON construction;
- layered validation;
- country-pack-driven output generation;
- Belgium / Peppol basic XML generation;
- Saudi / ZATCA-style XML generation;
- Saudi Arabic/bilingual visual PDF with QR code;
- ZIP evidence bundle;
- audit trail.

V1 does **not** implement:

- live Peppol transmission;
- live ZATCA/FATOORA clearance or reporting;
- production cryptographic stamping;
- tax determination;
- ERP integration;
- multi-tenant client management;
- a dashboard analytics product.

## Document order

1. `docs/01_product_scope.md`
2. `docs/02_app_architecture.md`
3. `docs/03_data_model_and_excel_template.md`
4. `docs/04_validation_engine.md`
5. `docs/05_country_pack_standard.md`
6. `docs/06_belgium_peppol_pack_spec.md`
7. `docs/07_saudi_zatca_pack_spec.md`
8. `docs/08_output_bundle_and_audit_trail_spec.md`
9. `docs/09_ui_design_spec.md`
10. `docs/10_codex_build_prompt.md`
11. `docs/11_milestones_and_acceptance_tests.md`
12. `docs/12_repository_setup_and_commands.md`
13. `docs/13_source_material_inventory.md`
14. `docs/14_open_items_and_deferred_scope.md`

## How to use this pack with Codex

1. Put these docs into the repository under `/docs`.
2. Copy source artefacts into `/docs/source_material` or keep them locally outside Git if you do not want to commit regulatory documents.
3. Open Codex against the local folder `C:\Users\Philip\Downloads\EInvoicing`.
4. Start with `docs/10_codex_build_prompt.md`.
5. Build by milestone, not all at once.

## Non-negotiable instruction

Codex must never claim official compliance or authority acceptance unless the app has genuinely run the relevant official artefact validator or authority response workflow. V1 is a controlled offline generator and evidence-bundle workbench.


---

<!-- docs/00_build_pack_index.md -->

# 00 — Build Pack Index

## Repository and local environment

- GitHub repository: https://github.com/PhilFer1973/EInvoicing
- Local development folder: `C:\Users\Philip\Downloads\EInvoicing`
- Recommended repository root name: `EInvoicing`

## Product name

**E-Invoicing Workbench**

## V1 one-sentence definition

A country-pack-driven web workbench that takes a controlled Excel invoice workbook, validates it, generates e-invoicing files for selected country packs, and creates an audit-ready evidence bundle — without live authority submission.

## V1 country packs

| Pack | V1 status | Output |
|---|---|---|
| `belgium_peppol` | Basic generator, final XSD clean-up pending | Peppol-style UBL XML + evidence bundle |
| `saudi_zatca` | Basic generator ready | ZATCA-style XML + Arabic/bilingual visual PDF + QR + evidence bundle |
| `uk_info` | Info-only placeholder | No generation |

## V1 milestones

1. Repository skeleton and local dev setup.
2. App shell and exact workbench UI.
3. Workbook upload and canonical invoice JSON.
4. Validation engine and audit persistence.
5. Belgium Peppol XML generator.
6. Saudi ZATCA-style XML, QR and Arabic/bilingual PDF.
7. ZIP evidence bundle and acceptance tests.

## Acceptance principle

A build is accepted only if it follows the scope and design exactly. A visually generic dashboard, live-submission buttons, or fake compliance claims are build failures.


---

<!-- docs/01_product_scope.md -->

# 01 — Product Scope

## Product

**E-Invoicing Workbench** is a controlled file generation and validation application for finance teams working across jurisdictions with e-invoicing mandates.

It is designed as a practical CFO/FD-grade proof of concept that demonstrates how a finance user can take invoice data exported from an ERP, validate it, generate country-specific structured outputs, and retain an audit trail.

## Core V1 proposition

The application allows a user to:

1. select a country/regime;
2. upload a fixed Excel workbook containing invoice data;
3. validate workbook structure, data types, required fields, arithmetic and country-specific preflight rules;
4. generate country-specific e-invoicing outputs;
5. download a ZIP evidence bundle;
6. view past generations in an audit trail.

## V1 scope

### In scope

- Single-user local/dev web app.
- One uploaded workbook at a time.
- One invoice per workbook for V1.
- Four workbook sheets: `entities`, `customers`, `invoice_header`, `invoice_lines`.
- Country-pack-driven rules.
- Belgium / Peppol basic generator.
- Saudi / ZATCA basic generator.
- UK info-only placeholder.
- Internal validation status.
- Official artefact validation status where validators are actually configured.
- Evidence bundle storage.
- Audit trail.
- Saudi Arabic/bilingual visual PDF with QR.

### Out of scope

- Live Peppol transmission.
- Live ZATCA/FATOORA clearance.
- Live ZATCA reporting.
- Production CSID onboarding.
- Production cryptographic stamping.
- Tax determination.
- ERP integration.
- Manual invoice entry/editing.
- Multi-tenant client management.
- Full dashboard analytics.
- Full global country coverage.
- Credit notes, debit notes, self-billing and simplified invoices in V1.
- Mixed VAT-rate invoice support in the first build milestone.

## Product boundary statement

Use this text in the app wherever compliance status is shown:

> Generated and validated against the published schemas, validation artefacts, and configured country rules available in this application. Not submitted to tax authorities and not a substitute for professional compliance review.

## V1 exactness boundary

> V1 generates files that are structurally valid and pass internal/published validation artefacts where configured. It does not guarantee live authority acceptance.

## Country-specific boundary notes

### Belgium

Belgium V1 generates a Peppol-style UBL XML invoice and evidence bundle. It does not transmit through Peppol, connect to an access point, submit to Mercurius, or guarantee live recipient acceptance.

### Saudi Arabia

Saudi V1 generates ZATCA-style XML, Arabic/bilingual visual PDF, QR code and evidence bundle. It does not submit to FATOORA, obtain ZATCA clearance, create a production cryptographic stamp, maintain a production invoice hash chain, or produce a live-valid Saudi B2B tax invoice.

## Primary user

A finance/FD/CFO-oriented user who understands invoice data and compliance risk but does not want to manually construct XML or interpret validation errors from raw command-line tooling.

## Success criteria

V1 succeeds if:

- the user can upload the controlled workbook;
- validation failures are clear and actionable;
- Belgium XML can be generated from a simple domestic Belgian B2B invoice;
- Saudi XML, PDF and QR can be generated from a simple Saudi B2B invoice;
- every generation creates a complete evidence bundle;
- the audit trail records inputs, outputs, warnings, pack versions and hashes;
- the UI clearly distinguishes internal validation from official/authority validation.


---

<!-- docs/02_app_architecture.md -->

# 02 — App Architecture

## Repository

- GitHub: https://github.com/PhilFer1973/EInvoicing
- Local folder: `C:\Users\Philip\Downloads\EInvoicing`

## Recommended stack

### Frontend

- React
- TypeScript
- Vite
- Plain CSS or CSS modules using the tokens in `09_ui_design_spec.md`
- No default UI kit that overrides the agreed visual style
- No Tailwind unless the generated UI exactly follows the design tokens

### Backend

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- SQLite for local V1 audit trail
- `openpyxl` for Excel workbook parsing
- `lxml` for XML generation and XML/XSD validation where configured
- Java/Saxon or other XSLT 2.0-capable route later for Schematron/XSLT if needed
- `qrcode` + Pillow or SVG QR generation
- Playwright/Chromium for Arabic/bilingual PDF rendering
- `zipfile` for evidence bundles

## High-level architecture

```text
React Workbench UI
  -> FastAPI backend
      -> Workbook parser
      -> Canonical invoice builder
      -> Validation engine
      -> Country pack adapter
      -> Output generators
      -> Evidence bundle builder
      -> Audit trail database
      -> Local file storage
```

## Core data flow

```text
Excel workbook
  -> workbook structure validation
  -> typed workbook rows
  -> canonical invoice JSON
  -> validation pipeline
  -> selected country adapter
  -> country output generation
  -> output validation where configured
  -> warning acknowledgement
  -> ZIP evidence bundle
  -> audit trail entry
```

## Non-negotiable architecture rule

Country adapters must read the canonical invoice model only. They must not generate XML directly from Excel rows.

## Suggested repository structure

```text
EInvoicing/
  apps/
    web/
      package.json
      src/
        main.tsx
        App.tsx
        routes/
        components/
        screens/
        services/
        styles/
          tokens.css
          app.css
  server/
    pyproject.toml
    app/
      main.py
      api/
        uploads.py
        validation.py
        generations.py
        audit.py
        country_packs.py
      core/
        config.py
        errors.py
        logging.py
      models/
        canonical.py
        workbook.py
        validation.py
        audit.py
      db/
        session.py
        schema.py
      validation/
        workbook_validator.py
        canonical_validator.py
        arithmetic_validator.py
        code_list_validator.py
        legal_invoice_validator.py
        country_preflight_validator.py
        xml_validator.py
        xslt_validator.py
        validation_result.py
      adapters/
        base.py
        belgium_peppol.py
        saudi_zatca.py
        uk_info.py
      generators/
        ubl_generator.py
        zatca_ubl_generator.py
        qr_generator.py
        pdf_generator.py
        zip_bundle_generator.py
      storage/
        file_store.py
        hash_utils.py
  country_packs/
    belgium_peppol/
    saudi_zatca/
    uk_info/
  schemas/
    shared/
      ubl/
      en16931/
  test_data/
    workbooks/
    expected_outputs/
    fixtures/
  docs/
```

## API endpoints

### Country packs

```text
GET /api/country-packs
GET /api/country-packs/{pack_id}
```

### Upload and validation

```text
POST /api/uploads
GET /api/uploads/{upload_id}
POST /api/uploads/{upload_id}/validate
GET /api/uploads/{upload_id}/validation-results
```

### Generation

```text
POST /api/uploads/{upload_id}/generate
GET /api/generations/{generation_id}
GET /api/generations/{generation_id}/download
```

### Audit trail

```text
GET /api/audit
GET /api/audit/{generation_id}
```

## Database tables

### `uploads`

- `id`
- `original_filename`
- `stored_path`
- `sha256_hash`
- `created_at`
- `selected_country_pack`
- `selected_output_profile`
- `status`

### `invoices`

- `id`
- `upload_id`
- `invoice_number`
- `country_pack_id`
- `canonical_json_path`
- `canonical_sha256_hash`
- `created_at`

### `validation_results`

- `id`
- `upload_id`
- `generation_id nullable`
- `layer`
- `severity`
- `rule_id`
- `message`
- `field_path`
- `status`
- `created_at`

### `generations`

- `id`
- `upload_id`
- `invoice_id`
- `country_pack_id`
- `output_profile_id`
- `country_pack_version`
- `status`
- `zip_path`
- `zip_sha256_hash`
- `created_at`

### `warning_acknowledgements`

- `id`
- `generation_id`
- `warning_code`
- `acknowledgement_text`
- `acknowledged_at`

## Local storage structure

```text
storage/
  uploads/YYYY/MM/upload_<id>.xlsx
  canonical/YYYY/MM/invoice_<id>.json
  generated/YYYY/MM/<generation_id>/invoice.xml
  generated/YYYY/MM/<generation_id>/invoice_ar_visual.pdf
  generated/YYYY/MM/<generation_id>/qr.png
  exports/YYYY/MM/<generation_id>.zip
```

## Error handling principle

Errors must be specific, deterministic and finance-user-readable. Do not show raw stack traces to the user.

## Configuration principle

Everything country-specific must live in country pack files or country adapter code. The UI must not hard-code Belgium or Saudi legal logic.


---

<!-- docs/03_data_model_and_excel_template.md -->

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


---

<!-- docs/04_validation_engine.md -->

# 04 — Validation Engine

## Validation philosophy

Validation must be layered, deterministic and honest. The app must never claim official validation unless the relevant official artefact validator has actually run.

## Validation sequence

```text
1. Workbook structure validation
2. Data type validation
3. Referential integrity validation
4. Canonical invoice construction
5. Generic arithmetic validation
6. Country rounding policy validation
7. Code-list validation
8. Legal invoice requirement validation
9. Country e-invoice preflight validation
10. Output generation
11. Technical output validation where configured
12. Warning acknowledgement check
13. Evidence bundle generation
```

## Severity levels

| Severity | Behaviour |
|---|---|
| `error` | Blocks generation/export. |
| `warning_ack_required` | Allows export only after explicit acknowledgement. |
| `warning` | Non-blocking. |
| `info` | Informational. |

## Validation result object

```json
{
  "rule_id": "SA-EINV-012",
  "layer": "country_preflight",
  "severity": "warning_ack_required",
  "status": "failed",
  "message": "This file has not been submitted to FATOORA and is not a cleared Saudi tax invoice.",
  "field_path": "invoice.selected_country_pack",
  "country_pack_id": "saudi_zatca",
  "country_pack_version": "0.3.0"
}
```

## Internal validation vs official artefact validation

The app must display two statuses:

### Internal validation

- workbook present;
- data types valid;
- arithmetic valid;
- country required fields present;
- country preflight rules passed;
- output generated.

### Official artefact validation

Only shown as passed if the app actually ran the configured artefact validator, such as:

- UBL XSD;
- EN 16931 XSLT/Schematron;
- Peppol XSLT/Schematron;
- ZATCA SDK/toolbox in future;
- authority API response in future.

If the artefact is missing, show:

```text
Not configured
```

Do not show fake green statuses.

## Generic arithmetic rules

- Sum of line net amounts equals header line extension total / net total.
- Tax exclusive total equals net total adjusted for document allowances/charges where implemented.
- Tax inclusive total equals tax exclusive total plus tax total.
- Payable amount equals tax inclusive total minus prepaid amount plus rounding amount where implemented.

## Country-aware VAT validation

The engine must support:

```text
Group invoice lines by VAT category and VAT rate.
Calculate taxable base per group.
Apply country rounding method.
Compare against VAT category tax amount.
Sum VAT category tax amounts to invoice VAT total.
```

### Belgium policy

```json
{
  "rounding_method": "country_pack_defined",
  "vat_rounding_level": "total_per_vat_rate",
  "line_level_vat_rounding_allowed": false
}
```

### Saudi policy

```json
{
  "rounding_method": "half_up",
  "amount_decimals": 2,
  "vat_rounding_level": "vat_category_document_level",
  "line_vat_summation_is_not_sufficient": true
}
```

## Code-list validation

Code lists must be pack-configurable.

Examples:

- country codes;
- currency codes;
- VAT category codes;
- invoice type codes;
- unit codes;
- exemption reason codes;
- payment means codes.

## Blocking examples

- Missing invoice number.
- Duplicate invoice number within upload.
- Missing seller legal name.
- Missing seller tax registration number for V1 Belgium/Saudi.
- Missing buyer tax number for V1 B2B Belgium/Saudi.
- Missing invoice date.
- VAT totals mismatch.
- Unsupported country pack or profile.
- Saudi production compliance mode selected.
- UK info-only pack used for generation.

## Warning acknowledgement examples

- Missing Peppol endpoint IDs in Belgium V1.
- Saudi non-clearance warning.
- Saudi non-production-signing warning.
- Saudi previous invoice hash placeholder.
- Invoice issue date appears late based on tax point date.

## Technical validation notes

### XSD

Use `lxml` for XSD validation where a complete schema bundle is present. If schema imports fail, return a configuration error.

### XSLT/Schematron

Do not manually rewrite complex Schematron rules in Python. Use official/precompiled XSLT artefacts where possible. If the runtime cannot execute the relevant XSLT version, mark validation as not configured rather than faking success.

### ZATCA SDK

The ZATCA SDK / Compliance Enablement Toolbox is out of scope for V1, but the architecture must allow adding it later as a validation provider.

## Validation UI rules

- Show blocking errors first.
- Group errors by sheet/field/layer.
- Include a plain-English explanation.
- Include expected value or corrective action where possible.
- Do not show raw XML/XPath as the main user-facing message, but include technical details in the evidence bundle.


---

<!-- docs/05_country_pack_standard.md -->

# 05 — Country Pack Standard

## Purpose

A country pack contains all country-specific information, rules, output profiles, mappings and validation artefact references.

The UI must not hard-code country compliance logic.

## Support levels

| Level | Meaning |
|---|---|
| `info_only` | Country information panel only; no generation. |
| `generator_scaffold` | Pack folder exists, but output generation not complete. |
| `generator_basic` | Internal validation and output generation work for V1 scenario. |
| `generator_validated` | Output also passes configured official artefact validators. |
| `submission_sandbox` | Sandbox submission supported. Not V1. |
| `submission_live` | Live submission supported. Not V1. |

## Country pack folder structure

```text
country_packs/<pack_id>/
  pack.json
  info_panel.md
  sources.json
  legal_invoice_requirements.json
  einvoice_requirements.json
  field_requirements.json
  output_profiles.json
  code_lists.json
  currency_rules.json
  rounding_rules.json
  security_boundary.json
  mappings/
    canonical_to_output.json
  validators/
    xsd/
    schematron/
    xslt/
    sdk/
  examples/
    valid/
    invalid/
  tests/
    expected_results.json
```

## `pack.json` required fields

```json
{
  "country_pack_id": "saudi_zatca",
  "display_name": "Saudi Arabia / ZATCA",
  "country_code": "SA",
  "pack_version": "0.3.0",
  "support_level": "generator_basic",
  "v1_boundary": "...",
  "output_profiles": [],
  "requires_pdf": true,
  "requires_qr": true,
  "requires_signature": true,
  "requires_live_submission_for_validity": true,
  "validation_layers": [],
  "last_reviewed": "2026-06-24"
}
```

## Adapter contract

Every country adapter must implement:

```text
get_pack_manifest()
get_info_panel()
get_output_profiles()
get_required_fields(profile_id)
preflight_validate(canonical_invoice, profile_id)
generate_output(canonical_invoice, profile_id)
validate_output(generated_output, profile_id)
build_evidence_metadata(canonical_invoice, generated_output, validation_result)
```

## Country adapter base class

The base adapter should enforce:

- declared support level;
- known output profiles;
- no live submission unless explicitly implemented;
- no production compliance claim unless configured;
- pack version included in all validation outputs.

## Source tracking

Each country pack must include `sources.json`.

Example:

```json
{
  "sources": [
    {
      "source_id": "SA-XML-STD-20230519",
      "title": "ZATCA Electronic Invoice XML Implementation Standard",
      "filename": "20230519_ZATCA_Electronic_Invoice_XML_Implementation_Standard_ vF.pdf",
      "source_type": "official_pdf",
      "status": "uploaded",
      "used_for": ["xml_mapping", "business_rules", "rounding", "code_lists"]
    }
  ]
}
```

## Evidence manifest

Every output bundle must contain the country pack ID, pack version, output profile ID, artefact versions and validation status.

## Rule file format

```json
{
  "rule_id": "BE-EINV-011",
  "severity": "error",
  "layer": "country_preflight",
  "message": "Either buyer reference or purchase order reference must be provided.",
  "condition": "buyer_reference is empty and purchase_order_reference is empty",
  "applies_to_profiles": ["peppol_bis_billing_3_0_ubl_invoice"]
}
```

## Mapping file format

Mappings should be explicit and testable.

```json
{
  "source": "invoice.invoice_number",
  "target": "cbc:ID",
  "required": true,
  "transform": null
}
```

## Pack status discipline

Do not upgrade a pack to `generator_validated` unless:

1. the output is generated;
2. official artefact validators are configured;
3. golden sample passes;
4. failed samples fail for the expected reasons;
5. evidence bundle records the validator outputs.


---

<!-- docs/06_belgium_peppol_pack_spec.md -->

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


---

<!-- docs/07_saudi_zatca_pack_spec.md -->

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


---

<!-- docs/08_output_bundle_and_audit_trail_spec.md -->

# 08 — Output Bundle and Audit Trail Spec

## Purpose

Every generation must produce a clear, reviewable evidence bundle that allows a finance user, reviewer or future auditor to understand:

- what input was used;
- what country pack was selected;
- what validation ran;
- what warnings were acknowledged;
- what outputs were generated;
- what was not done.

## ZIP bundle structure

### Belgium

```text
GEN-<generation_id>.zip
  invoice.xml
  canonical_invoice.json
  validation_report.json
  evidence.json
  source_upload_snapshot.xlsx
  country_pack_manifest.json
  hashes.txt
```

### Saudi

```text
GEN-<generation_id>.zip
  invoice.xml
  invoice_arabic_bilingual_visual.pdf
  qr.png
  qr_payload.txt
  canonical_invoice.json
  translation_audit.json
  validation_report.json
  evidence.json
  source_upload_snapshot.xlsx
  country_pack_manifest.json
  hashes.txt
```

## `evidence.json`

```json
{
  "generation_id": "GEN-001",
  "created_at": "2026-06-24T10:30:00Z",
  "country_pack_id": "saudi_zatca",
  "country_pack_version": "0.3.0",
  "output_profile_id": "zatca_standard_tax_invoice_xml_plus_arabic_visual_pdf",
  "source_upload_hash": "...",
  "canonical_invoice_hash": "...",
  "generated_files": [
    {"filename": "invoice.xml", "sha256": "..."},
    {"filename": "invoice_arabic_bilingual_visual.pdf", "sha256": "..."},
    {"filename": "qr.png", "sha256": "..."}
  ],
  "validation_summary": {
    "blocking_errors": 0,
    "warnings_acknowledged": 2,
    "official_artefact_validation": "not_configured"
  },
  "v1_boundary": "No live submission or authority acceptance guarantee."
}
```

## `validation_report.json`

Must contain every rule result, including passed critical rules where useful.

```json
{
  "overall_status": "passed_with_acknowledged_warnings",
  "results": [
    {
      "rule_id": "SA-EINV-012",
      "layer": "country_boundary",
      "severity": "warning_ack_required",
      "status": "acknowledged",
      "message": "This file has not been submitted to FATOORA and is not a cleared Saudi tax invoice."
    }
  ]
}
```

## `country_pack_manifest.json`

Must capture:

- country pack ID;
- display name;
- version;
- support level;
- source artefact statuses;
- validation artefact statuses;
- output profile;
- last reviewed date.

## `hashes.txt`

Plain text list of file hashes:

```text
source_upload_snapshot.xlsx  SHA256  ...
canonical_invoice.json       SHA256  ...
invoice.xml                  SHA256  ...
invoice_arabic_bilingual_visual.pdf SHA256 ...
qr.png                       SHA256  ...
```

## Audit trail page

The audit page should show:

| Field | Description |
|---|---|
| Generated at | Date/time. |
| Invoice number | Source invoice number. |
| Country pack | Belgium/Saudi/UK. |
| Pack version | Version used. |
| Output profile | Profile generated. |
| Status | Passed, failed, passed with warnings. |
| Warnings | Count and acknowledgement status. |
| Download | ZIP bundle link. |

## Storage policy for V1

- Store every upload.
- Store every generated output.
- Store validation reports.
- Store warning acknowledgements.
- Do not allow deletion in V1.

## Warning acknowledgements

Saudi must require acknowledgement before export:

> I understand this file has not been submitted to ZATCA/FATOORA and is not a cleared Saudi tax invoice.

Belgium warning if Peppol IDs missing:

> I understand this XML has not been transmitted through Peppol and missing Peppol endpoint details would prevent live Peppol delivery.

## Audit discipline

The audit trail must distinguish:

- internal validation passed;
- external artefact validation passed;
- external artefact validation not configured;
- live submission not supported;
- live submission not attempted.


---

<!-- docs/09_ui_design_spec.md -->

# 09 — UI Design Spec

## Design objective

Build a composed, premium, cool-toned, quietly futuristic finance compliance workbench. It should feel calm, precise and controlled, with a subtle AI-era quality. It must not look like a generic SaaS dashboard.

Codex must build from this spec, not from a vague screenshot interpretation.

## Design tokens

```css
:root {
  --canvas: #EFEDF6;
  --surface: rgba(255, 255, 255, 0.72);
  --surface-strong: rgba(255, 255, 255, 0.86);
  --surface-muted: rgba(245, 244, 250, 0.76);
  --hairline: rgba(120, 120, 150, 0.18);
  --hairline-strong: rgba(120, 120, 150, 0.28);
  --ink: #15182A;
  --ink-soft: #33384C;
  --muted: #5E6378;
  --muted-light: #7A8095;
  --accent-violet: #9B6CF5;
  --accent-violet-deep: #6A4BC8;
  --accent-cyan: #46D8E0;
  --accent-cyan-deep: #0E97A1;
  --success: #2F8F6B;
  --warning: #B98020;
  --danger: #B64A5A;
  --radius-lg: 22px;
  --radius-md: 16px;
  --radius-sm: 10px;
  --shadow-soft: 0 20px 60px rgba(45, 38, 80, 0.10);
  --shadow-card: 0 10px 30px rgba(45, 38, 80, 0.075);
  --gradient-accent: linear-gradient(135deg, #9B6CF5 0%, #46D8E0 100%);
}
```

## Page background

- Use `#EFEDF6` as the canvas.
- Add one soft top-right aurora glow.
- Do not use pure white as the page background.
- Do not use pure black text.
- Do not use dark cyberpunk styling.

Example:

```css
body {
  margin: 0;
  background: var(--canvas);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.app-shell::before {
  content: "";
  position: fixed;
  inset: -20% -10% auto auto;
  width: 620px;
  height: 620px;
  background: radial-gradient(circle, rgba(155,108,245,.10), rgba(70,216,224,.055), transparent 68%);
  pointer-events: none;
}
```

## Main layout

Desktop must be a three-column workbench.

```css
.workbench-grid {
  display: grid;
  grid-template-columns: 320px minmax(420px, 1fr) 380px;
  gap: 20px;
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px;
}
```

Columns:

1. Left: setup and upload.
2. Centre: country compliance pack and validation.
3. Right: invoice review and export.

## Top navigation

Top nav only. No sidebar.

Required items:

- Left: product name `E-Invoicing Workbench`.
- Centre/right nav links: `E-Invoicing`, `Audit Trail`.
- Right icons/buttons: Settings, Help.

## Cards

```css
.card {
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(18px);
  padding: 18px;
}
```

Do not use heavy shadows. Do not use sharp square cards.

## Buttons

Primary button:

```css
.button-primary {
  border: none;
  color: white;
  background: var(--gradient-accent);
  border-radius: 999px;
  padding: 11px 16px;
  font-weight: 650;
}
```

Secondary button:

```css
.button-secondary {
  border: 1px solid var(--hairline-strong);
  background: rgba(255,255,255,.52);
  color: var(--ink-soft);
  border-radius: 999px;
  padding: 10px 15px;
}
```

## Screen structure

```html
<body class="app-shell">
  <header class="top-nav">
    <div class="brand">E-Invoicing Workbench</div>
    <nav>
      <a>E-Invoicing</a>
      <a>Audit Trail</a>
    </nav>
    <div class="top-actions">
      <button>Settings</button>
      <button>Help</button>
    </div>
  </header>

  <main class="workbench-grid">
    <section class="left-column"></section>
    <section class="center-column"></section>
    <section class="right-column"></section>
  </main>
</body>
```

## Left column components

### `CountrySelectorCard`

Content:

- heading: `Country pack`;
- options: Belgium / Peppol, Saudi Arabia / ZATCA, UK info only;
- support-level pill;
- boundary note.

Behaviour:

- changing country resets validation and generated outputs;
- Saudi shows strong non-clearance warning;
- UK disables generation.

Visual:

- selected country has violet/cyan accent border;
- no large flag tiles;
- use small country/regime labels.

### `UploadWorkbookCard`

Content:

- drag/drop area;
- file selector;
- expected sheets list;
- upload status.

States:

- no file;
- uploading;
- uploaded;
- parse failed.

### `ValidationSummaryCard`

States:

- not uploaded;
- validating;
- failed;
- passed;
- passed with warnings.

## Centre column components

### `CountryInfoPanel`

Must show:

- regime summary;
- legal invoice requirements;
- e-invoice requirements;
- V1 boundary;
- source status;
- output profile.

Saudi panel must visibly state:

> Not submitted to FATOORA. No ZATCA clearance stamp. Not a cleared Saudi tax invoice.

Belgium panel must state:

> Not transmitted through Peppol. No access point or Mercurius submission.

### `ValidationResultsPanel`

Groups:

- blocking errors;
- warnings requiring acknowledgement;
- non-blocking warnings;
- passed checks;
- technical validation status.

Do not show raw XML as the main view. Put technical details behind expanders.

## Right column components

### `InvoiceReviewCard`

Show:

- invoice number;
- seller;
- buyer;
- date/time;
- currency;
- net/tax/gross;
- number of lines;
- first few line details.

### `ExportPanel`

Belgium buttons:

- Generate XML;
- Generate ZIP bundle.

Saudi buttons:

- Generate XML;
- Generate Arabic/Bilingual Visual PDF;
- Generate QR;
- Generate ZIP bundle.

Saudi must require acknowledgement before ZIP export.

## Audit trail page

Top nav remains. Main content is a single wide card/table.

Columns:

- generated at;
- invoice number;
- country pack;
- output profile;
- status;
- warnings;
- pack version;
- download ZIP.

## Responsive behaviour

```css
@media (max-width: 1180px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }
}
```

Below tablet width, stack:

1. setup/upload;
2. country info/validation;
3. invoice/export.

## Negative design instructions

Do not build:

- a left sidebar;
- KPI dashboard cards;
- charts;
- chat UI;
- bottom fixed status bar;
- dark mode as default;
- neon cyberpunk effects;
- saturated blue SaaS theme;
- country flag tile UI;
- marketing landing page;
- irrelevant analytics.

## Visual QA checklist

Before UI is accepted:

- [ ] Background is violet-tinted near-white, not plain white.
- [ ] Desktop has exactly three main workbench columns.
- [ ] Top nav only; no sidebar.
- [ ] Cards use translucent/glass surfaces and subtle borders.
- [ ] Belgium and Saudi show different boundary warnings.
- [ ] Saudi export panel includes Arabic PDF and QR.
- [ ] Audit Trail is top-nav page, not a dashboard sidebar item.
- [ ] No live-submission buttons exist.
- [ ] No generic dashboard charts were added.
- [ ] CSS tokens are used instead of ad hoc colours.


---

<!-- docs/10_codex_build_prompt.md -->

# 10 — Codex Build Prompt

Use this as the first prompt to Codex after copying the build pack into the repository.

---

You are working in the repository:

- GitHub: https://github.com/PhilFer1973/EInvoicing
- Local folder: `C:\Users\Philip\Downloads\EInvoicing`

Build the V1 E-Invoicing Workbench exactly as specified in the `/docs` build pack.

## Required behaviour

Read these documents first and follow them strictly:

1. `docs/01_product_scope.md`
2. `docs/02_app_architecture.md`
3. `docs/03_data_model_and_excel_template.md`
4. `docs/04_validation_engine.md`
5. `docs/05_country_pack_standard.md`
6. `docs/06_belgium_peppol_pack_spec.md`
7. `docs/07_saudi_zatca_pack_spec.md`
8. `docs/08_output_bundle_and_audit_trail_spec.md`
9. `docs/09_ui_design_spec.md`
10. `docs/11_milestones_and_acceptance_tests.md`
12. `docs/12_repository_setup_and_commands.md`

## Build only V1

Build:

- React + TypeScript + Vite frontend;
- Python FastAPI backend;
- workbook upload;
- canonical invoice JSON construction;
- layered validation;
- country pack loading;
- Belgium Peppol basic XML generation;
- Saudi ZATCA-style XML generation;
- Saudi Arabic/bilingual visual PDF with QR;
- evidence bundle ZIP;
- local SQLite audit trail;
- exact UI described in `09_ui_design_spec.md`.

## Do not build

Do not build:

- live Peppol transmission;
- live ZATCA/FATOORA clearance;
- live ZATCA reporting;
- production cryptographic signing;
- production CSID onboarding;
- tax determination engine;
- ERP integration;
- manual invoice editing;
- multi-tenant client management;
- analytics dashboard;
- chat UI;
- sidebar navigation;
- bottom status bar;
- unsupported countries beyond placeholders.

## Critical architecture rules

1. Excel data must be converted to canonical invoice JSON before country output generation.
2. Country adapters must read canonical invoice JSON, not raw Excel rows.
3. Country logic must not be hard-coded into the UI.
4. Official validation must not be claimed unless the relevant official artefact validator actually runs.
5. If an artefact is missing or fails to configure, show `not configured` or `configuration error`, not `passed`.
6. Saudi output must always show non-clearance and non-production-signing warnings in V1.
7. Belgium output must always show non-transmission warning in V1.

## First milestone only

Start with Milestone 1:

- create repository structure;
- create FastAPI app skeleton;
- create React app skeleton;
- implement exact workbench UI shell from `09_ui_design_spec.md`;
- implement country pack manifest loading;
- implement placeholder API endpoints;
- implement local dev run instructions;
- add tests that prove the app starts.

Do not proceed to Belgium/Saudi generation until Milestone 1 is accepted.

## Acceptance condition

The UI must visually match the design spec: violet-tinted near-white background, no sidebar, no dashboard charts, three-column workbench, glass-like cards, violet/cyan accent, and clear country boundary warnings.

---

For later milestones, follow `docs/11_milestones_and_acceptance_tests.md`.


---

<!-- docs/11_milestones_and_acceptance_tests.md -->

# 11 — Milestones and Acceptance Tests

## Milestone 1 — Repository skeleton and UI shell

### Build

- Create `/apps/web` React TypeScript Vite app.
- Create `/server` FastAPI app.
- Create `/country_packs` folder with Belgium, Saudi and UK manifests.
- Create exact workbench UI shell.
- Create Audit Trail placeholder page.
- Add local dev commands.

### Acceptance tests

- App starts locally.
- Backend health endpoint returns OK.
- UI has top nav only.
- UI has three-column desktop layout.
- No sidebar exists.
- No dashboard charts exist.
- Country selector displays Belgium, Saudi and UK.
- Saudi boundary warning is visible when Saudi selected.

## Milestone 2 — Workbook upload and canonical model

### Build

- Upload `.xlsx` workbook.
- Validate required sheets.
- Parse `entities`, `customers`, `invoice_header`, `invoice_lines`.
- Validate required columns.
- Build canonical invoice JSON.
- Store upload and canonical JSON.

### Acceptance tests

- Missing sheet fails with clear error.
- Missing required column fails with clear error.
- Valid sample workbook creates canonical JSON.
- Canonical JSON is downloadable in evidence preview.

## Milestone 3 — Validation engine

### Build

- Implement validation result model.
- Implement workbook/data type/referential validations.
- Implement generic arithmetic validation.
- Implement derived tax summary.
- Implement country rounding policies.
- Implement warning acknowledgement framework.

### Acceptance tests

- VAT total mismatch blocks generation.
- Missing invoice number blocks generation.
- Saudi non-clearance warning requires acknowledgement.
- Belgium missing Peppol IDs triggers warning acknowledgement, not blocking error.

## Milestone 4 — Belgium generator

### Build

- Implement Belgium adapter.
- Generate Peppol-style UBL XML for golden sample.
- Generate validation report.
- Generate ZIP bundle.
- Mark UBL XSD as not configured unless clean bundle installed.

### Acceptance tests

- `BE-VALID-001` generates XML and ZIP.
- Missing buyer reference and PO reference blocks generation.
- Missing Peppol IDs requires acknowledgement.
- Attempt live Peppol submission unsupported.

## Milestone 5 — Saudi generator, QR and PDF

### Build

- Implement Saudi adapter.
- Generate ZATCA-style XML.
- Generate QR payload with tags 1–5.
- Generate QR image.
- Generate Arabic/bilingual visual PDF using HTML/Playwright.
- Generate translation audit file.
- Generate ZIP bundle.

### Acceptance tests

- `SA-VALID-001` generates XML, PDF, QR and ZIP.
- QR payload decodes into five TLV fields.
- PDF displays Arabic and English headings.
- Saudi warning acknowledgement is required before ZIP export.
- App never says the invoice is cleared.

## Milestone 6 — Audit trail

### Build

- Persist uploads, validation, generations, acknowledgements.
- Build Audit Trail page.
- Download prior ZIP bundle.

### Acceptance tests

- Generation appears in audit list.
- Pack version displayed.
- Warning acknowledgement displayed.
- ZIP hash displayed or included in details.

## Milestone 7 — Polish and QA

### Build

- Improve error messages.
- Add sample workbook downloads.
- Add README and run instructions.
- Add unit tests around QR and validation.

### Acceptance tests

- New developer can run locally from README.
- All tests pass.
- UI checklist in `09_ui_design_spec.md` is complete.

## Red-line failures

Reject the build if Codex adds:

- live authority submission buttons;
- dashboard analytics;
- sidebar;
- tax determination;
- fake official validation status;
- Saudi production signing claim;
- Peppol transmission claim.


---

<!-- docs/12_repository_setup_and_commands.md -->

# 12 — Repository Setup and Commands

## Existing repository

- GitHub: https://github.com/PhilFer1973/EInvoicing
- Local folder: `C:\Users\Philip\Downloads\EInvoicing`

## Recommended first steps

Open PowerShell:

```powershell
cd C:\Users\Philip\Downloads

# If repo is not cloned yet:
git clone https://github.com/PhilFer1973/EInvoicing EInvoicing

cd C:\Users\Philip\Downloads\EInvoicing
```

Copy this build pack into:

```text
C:\Users\Philip\Downloads\EInvoicing\docs
```

## Suggested repository initialization

```powershell
git status
git add docs
git commit -m "Add V1 e-invoicing build specification pack"
git push
```

## Frontend setup

```powershell
cd C:\Users\Philip\Downloads\EInvoicing
npm create vite@latest apps/web -- --template react-ts
cd apps/web
npm install
npm run dev
```

## Backend setup

```powershell
cd C:\Users\Philip\Downloads\EInvoicing
mkdir server
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn pydantic openpyxl lxml sqlalchemy sqlmodel python-multipart qrcode pillow playwright pytest
python -m playwright install chromium
```

## Backend run command

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

## Frontend environment

Create:

```text
apps/web/.env.local
```

With:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Backend health endpoint

Codex should create:

```text
GET http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

## Source materials

Recommended local source-material folders:

```text
docs/source_material/belgium_peppol/
docs/source_material/saudi_zatca/
```

Do not assume every source document should be committed to GitHub. If licensing or file size is uncertain, keep source materials locally and store only a manifest in Git.

## Git ignore additions

```gitignore
server/.venv/
server/storage/
server/*.db
apps/web/node_modules/
apps/web/dist/
docs/source_material/private/
```

## First Codex instruction

Use `docs/10_codex_build_prompt.md` and ask Codex to complete Milestone 1 only.


---

<!-- docs/13_source_material_inventory.md -->

# 13 — Source Material Inventory

## Purpose

This document records the research artefacts and where Codex should expect them to be placed. It is not a legal opinion.

## Belgium / Peppol source materials

Recommended folder:

```text
docs/source_material/belgium_peppol/
```

Known/collected materials:

| File/source | Use |
|---|---|
| `OpenPeppol Policy on BIS Billing Country specific validation rules v1.1.0.pdf` | Country-specific validation policy and triggering logic. |
| `PEPPOL-EN16931-UBL.sch` | Peppol Schematron source. |
| `PEPPOL-EN16931-UBL.xslt` | Peppol validation XSLT. |
| `CEN-EN16931-UBL.xslt` | EN 16931 validation XSLT. |
| `UBL-Invoice-2.1.xsd` and supporting UBL XSD files | UBL schema validation, but current bundle must be verified as complete and consistent. |
| Belgium e-invoicing portal | Mandate information and official Belgian guidance. |
| EU Digital Building Blocks Belgium page | Peppol/EN16931 context. |

Belgium open source issue:

- obtain a complete, consistent UBL 2.1 XSD bundle from one official source;
- obtain primary Belgian legal invoice source or official FPS Finance page for final legal certainty.

## Saudi / ZATCA source materials

Recommended folder:

```text
docs/source_material/saudi_zatca/
```

Uploaded/collected materials:

| File | Use |
|---|---|
| `20230519_ZATCA_Electronic_Invoice_XML_Implementation_Standard_ vF.pdf` | XML structure, business rules, code lists, validation, calculations, rounding. |
| `20230519_EInvoice_Data_Dictionary vF.xlsx` | Field-level source of truth. |
| `EInvoice_Data_Dictionary.xlsx` | Data dictionary duplicate/variant. |
| `EInvoice_Data_Dictionary (1).xlsx` | Data dictionary duplicate/variant. |
| `QRCodeCreation.pdf` | QR TLV/Base64 guidance. |
| `E-invoicing-Detailed-Technical-Guideline.pdf` | Clearance/reporting/onboarding/process boundary. |
| `20220624_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards.pdf` | Signing, previous hash, QR, CSID, XAdES/PAdES, authentication. |
| `Standard_Invoice.xml` | V1 standard invoice reference fixture. |
| `Exempt Tax Invoice.xml` | Future exempt invoice fixture. |
| `Export invoice.xml` | Future export/zero-rated fixture. |
| `Out of Scope Standard Tax Invoice.xml` | Future out-of-scope fixture. |
| `Third party billing.xml` | Future transaction flag fixture. |
| `zatcaexample1.xml` to `zatcaexample5.xml` | Additional reference XMLs. |

## Do not over-rely on secondary sources

The Tally and other explanatory articles are useful for orientation but should not override official ZATCA source documents.

## Source-status principle

Country packs should record source status explicitly:

```json
{
  "source_id": "SA-SEC-20220624",
  "status": "uploaded",
  "used_for": ["security_boundary", "qr", "signing_future", "previous_hash_future"]
}
```


---

<!-- docs/14_open_items_and_deferred_scope.md -->

# 14 — Open Items and Deferred Scope

## Open items that do not block V1 basic build

### Belgium

- Complete, consistent UBL 2.1 XSD schema bundle.
- Primary Belgian legal invoice source / FPS Finance source for final legal invoice rule certainty.
- Full official Peppol artefact version reconciliation.
- Live Peppol delivery and participant lookup.

### Saudi

- ZATCA SDK / Compliance Enablement Toolbox integration.
- Sandbox credentials.
- API Swagger documentation for clearance/reporting.
- Production CSID onboarding.
- Production XAdES signing.
- Production previous invoice hash chain.
- PDF/A-3 with embedded XML and PAdES.

## Deferred country packs

Do not implement in first V1 build:

- France;
- Poland KSeF;
- Malaysia MyInvois;
- UAE PINT AE;
- India;
- Italy;
- Germany;
- Romania;
- Spain;
- Singapore;
- Australia/New Zealand;
- Brazil;
- Mexico;
- Chile;
- Argentina.

Keep architecture ready for them, but do not build them now.

## Deferred invoice scenarios

Do not implement in first V1 build:

- mixed VAT rates;
- credit notes;
- debit notes;
- simplified invoices;
- self-billing;
- prepayments;
- exports;
- exemptions;
- out-of-scope supplies;
- third-party billing;
- document-level allowances/charges.

Saudi source examples for exempt/export/out-of-scope/third-party should be saved as future fixtures, not used as V1 core acceptance.

## Deferred technical features

- Live authority APIs.
- Background validation jobs.
- Multi-user authentication.
- Supabase/Postgres production storage.
- Cloud deployment.
- Role-based access.
- Document deletion/retention policies beyond V1.
- PDF/A-3 production compliance.

## What must not be deferred

- Clear boundary warnings.
- Audit trail.
- Evidence bundle.
- Country pack versioning.
- Canonical model.
- UI design discipline.
- No fake compliance claims.
