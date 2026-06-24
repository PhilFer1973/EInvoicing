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
