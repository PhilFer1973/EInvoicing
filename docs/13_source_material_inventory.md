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
