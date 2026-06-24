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
