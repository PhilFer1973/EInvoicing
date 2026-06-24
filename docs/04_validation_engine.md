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
