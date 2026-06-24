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
