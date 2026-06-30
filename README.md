# E-Invoicing Workbench

Local V1 e-invoicing file generation and validation workbench. It accepts a structured Excel workbook, builds canonical invoice JSON, applies country-pack validation, and creates offline evidence bundles.

## V1 Boundary

This application is not an ERP, tax engine, Peppol access point, or live tax-authority submission tool.

- Belgium: generates a Peppol-style UBL XML file only. It does not transmit through Peppol.
- Saudi Arabia: generates offline/demo ZATCA-style XML, a tags 1-5 QR image, and a visual bilingual PDF. It does not submit, clear, report, apply authority stamps, onboard a CSID, or create a production cryptographic signature.
- United Kingdom: provides a 2029 Peppol roadmap pack and disabled-by-default Storecove sandbox-readiness scaffold only. It does not prove final UK 2029 statutory compliance.
- Official artefact validation is `not_configured` unless a real validator has been configured and run. The app does not claim UBL XSD, EN 16931, Peppol Schematron, UK statutory validation, or ZATCA SDK validation.

## Project Structure

```text
apps/web/              React, TypeScript, and Vite frontend
server/                FastAPI backend
country_packs/         Runtime country pack manifests
test_data/workbooks/   Demo workbooks
docs/                  Product and build-pack documentation
```

## Local Run

Install the backend environment once:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m playwright install chromium
```

`playwright install chromium` is needed once for the deterministic Saudi visual-PDF renderer. It does not connect to ZATCA/FATOORA.

Start the backend:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Install frontend packages once and start Vite in a second terminal:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\apps\web
npm install
npm run dev -- --port 5173
```

Open `http://127.0.0.1:5173`. The frontend uses `http://localhost:8000` by default. Set `VITE_API_BASE_URL` in `apps/web/.env.local` only when the API is hosted elsewhere.

## Demo Workbooks

- Belgium: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\BE-VALID-001.xlsx`
- Belgium e-invoice.be sandbox validation: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\BE-EINVOICEBE-VALIDATION-001.xlsx`
- Belgium e-invoice.be sandbox send: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\BE-EINVOICEBE-SEND-001.xlsx`
- Saudi Arabia: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\SA-VALID-001.xlsx`
- United Kingdom: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\UK-PEPPOL-SANDBOX-001.xlsx`

The **Export Template** button downloads a four-sheet starter workbook: `entities`, `customers`, `invoice_header`, and `invoice_lines`. It includes a valid Belgium domestic B2B sample row and optional Saudi-oriented columns such as `invoice_time` and `description_ar`.

## Belgium Demo

1. Select `Belgium / Peppol BIS Billing 3.0`.
2. Upload `BE-VALID-001.xlsx`.
3. Select **Validate**, then **Generate**.
4. The generated-output view provides the XML; select **Export ZIP** for the evidence bundle.

The bundle contains the workbook snapshot, canonical invoice, validation report, Belgium XML, country-pack manifest, evidence metadata, and hashes.

### Belgium XML Validation Foundation

Milestone 6A adds reusable local XML validation for generated Belgium UBL XML. The main **Validate** pipeline now generates Belgium XML from canonical invoice JSON, checks XML well-formedness, runs basic UBL invoice structure checks, and runs Peppol-readiness checks for endpoint IDs, scheme IDs, buyer/order reference, VAT category/rate information and payable amount.

These checks are readiness checks only. Full UBL XSD validation, EN16931 validation and Peppol Schematron validation are explicitly marked as:

```text
Official validator not configured in this milestone.
```

Milestone 6A does not prove Peppol delivery, recipient acceptance, SMP registration, or final statutory compliance.

To demo the Belgium XML validation foundation:

1. Select `Belgium / Peppol BIS Billing 3.0`.
2. Upload `BE-VALID-001.xlsx` or `BE-EINVOICEBE-VALIDATION-001.xlsx`.
3. Select **Validate**.
4. Open **Validation Details** to see Internal validation, XML generation, XML well-formedness, UBL structure checks, Peppol readiness checks, external sandbox validation status, and official validator status.
5. Export the evidence ZIP and inspect `xml_validation_report.json` and `evidence_metadata.json`.

### Belgium EN16931 / Peppol Schematron Validation

Milestone 6B adds a reusable Schematron/SVRL runner for Belgium EN16931 and Peppol BIS Billing 3.0 validation. This layer is disabled by default because the official/precompiled validator artefacts are not committed to this repository.

Milestone 6B adds the official validator runner/reporting framework. In the current local setup, UBL XSD, EN16931 and Peppol Schematron artefacts are not configured, so those statuses remain Not Configured. No official validation pass is claimed.

Expected artefact locations:

```text
validators/belgium_peppol/en16931/CEN-EN16931-UBL.xslt
validators/belgium_peppol/peppol/PEPPOL-EN16931-UBL.xslt
```

Optional environment variables:

```powershell
EINVOICING_EN16931_VALIDATOR_ARTEFACT=validators/belgium_peppol/en16931/CEN-EN16931-UBL.xslt
EINVOICING_PEPPOL_VALIDATOR_ARTEFACT=validators/belgium_peppol/peppol/PEPPOL-EN16931-UBL.xslt
EINVOICING_SCHEMATRON_ENGINE_COMMAND="java -jar C:\path\to\saxon-he.jar -s:{xml} -xsl:{artefact} -o:{output}"
EINVOICING_EN16931_VALIDATOR_VERSION=
EINVOICING_PEPPOL_VALIDATOR_VERSION=
```

The runner writes concise JSON reports and preserves raw SVRL output where a validator actually runs:

- `en16931_validation_report.json`
- `peppol_schematron_validation_report.json`
- `en16931_validation_raw.svrl`
- `peppol_schematron_validation_raw.svrl`

Status meanings:

- `passed`: configured validator artefact executed and returned no failed assertions.
- `failed`: configured validator executed and found issues, or execution/output parsing failed.
- `warning`: configured validator executed and returned warning/report messages without failed assertions.
- `skipped`: validation layer was not run because an earlier XML layer could not proceed.
- `not_configured`: artefact or execution engine is not configured.

The UI and evidence only show EN16931 or Peppol Schematron validation as passed when the configured artefact has actually run against the generated XML. These validator results still do not prove Peppol delivery, recipient acceptance, SMP registration or final statutory compliance.

### Optional e-invoice.be Sandbox Validation And Send

Milestone 5B adds an optional Belgium-only external sandbox validation stage inside the main **Validate** pipeline. It generates Belgium UBL XML from canonical invoice JSON where needed, validates that XML with e-invoice.be when configured, and stores the provider response as evidence. It does not deliver through Peppol, prove recipient acceptance, prove SMP registration, or prove final statutory compliance.

Milestone 5C adds an optional e-invoice.be sandbox send/test action after validation has passed. This uses the documented e-invoice.be document flow: `POST /api/documents/ubl` with multipart form field `file`, then `POST /api/documents/{document_id}/send` with optional Peppol ID query parameters. It is still sandbox-provider workflow evidence only:

```text
Sandbox send only. This does not prove Peppol delivery, recipient acceptance or final statutory compliance.
```

Default configuration is disabled:

```powershell
EINVOICEBE_ENABLED=false
EINVOICEBE_API_BASE_URL=https://api.e-invoice.be
EINVOICEBE_API_KEY=
EINVOICEBE_SANDBOX_COMPANY_NUMBER=099025170
EINVOICEBE_SANDBOX_PEPPOL_ID=0208:099025170
```

To test locally with your sandbox key, set environment variables in the backend terminal before starting Uvicorn:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
$env:EINVOICEBE_ENABLED="true"
$env:EINVOICEBE_API_BASE_URL="https://api.e-invoice.be"
$env:EINVOICEBE_API_KEY="your-sandbox-api-key"
$env:EINVOICEBE_SANDBOX_COMPANY_NUMBER="099025170"
$env:EINVOICEBE_SANDBOX_PEPPOL_ID="0208:099025170"
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then:

1. Start the frontend with `npm run dev -- --port 5173`.
2. Select `Belgium / Peppol BIS Billing 3.0`.
3. Upload `BE-EINVOICEBE-VALIDATION-001.xlsx` for validation-only testing, or `BE-EINVOICEBE-SEND-001.xlsx` for sandbox send testing. The send request omits explicit sender query parameters so e-invoice.be can infer the sender from the configured sandbox tenant/provider context.
4. Select **Validate**. When configured, this automatically runs internal validation, generates Belgium XML for validation, and runs e-invoice.be sandbox validation.
5. If external sandbox validation passes and the workbook's `einvoicebe_sender_peppol_id` matches `EINVOICEBE_SANDBOX_PEPPOL_ID`, select **Send to e-invoice.be sandbox** to run the optional sandbox send/test action.
6. Select **Generate** to open generated outputs, or **Export ZIP** for the evidence bundle.

The e-invoice.be validation evidence files are `einvoicebe_validation_request.json`, `einvoicebe_validation_response.json`, and `external_validation_status.json`. If sandbox send has run, the bundle also includes `einvoicebe_send_request.json`, `einvoicebe_send_response.json`, `external_sandbox_send_status.json`, and `einvoicebe_send_provider_reference.txt` when the provider returns a reference. API keys are read from environment variables only and are redacted from evidence.

Known limitation: The e-invoice.be sandbox send flow currently reaches the provider and captures the provider response, but successful sandbox send is blocked by a sandbox tenant Peppol ID mismatch. External validation passes; send completion is parked pending provider clarification.

## Saudi Demo

1. Select `Saudi Arabia / ZATCA`.
2. Upload `SA-VALID-001.xlsx`.
3. Select **Validate**, then **Generate**.
4. The generated-output view provides the Saudi XML, QR image, decoded QR payload, and Arabic/bilingual visual PDF.
5. Acknowledge the displayed Saudi V1 boundary before selecting **Export ZIP**.

The Saudi QR encodes Base64 TLV tags 1-5 only: seller name, VAT/TIN, timestamp, total including VAT, and VAT total. Normal phone scanners may display the Base64/TLV value; use the decoded QR payload view to inspect the invoice fields.

The Saudi bundle contains the workbook snapshot, canonical invoice, validation report, XML, `qr_payload_base64.txt`, `qr_payload_decoded.json`, `qr.png`, `saudi_visual_invoice.pdf`, country-pack manifest, evidence metadata, and hashes.

## UK Peppol Roadmap Demo

Product wording used in the UI and evidence:

```text
UK Peppol sandbox test only. This tests Peppol-style invoice readiness through a sandbox provider. It does not prove final UK 2029 statutory compliance.
```

1. Select `United Kingdom / 2029 Peppol Roadmap`.
2. Upload `UK-PEPPOL-SANDBOX-001.xlsx`.
3. Select **Validate** to build canonical invoice JSON and run local UK sandbox-readiness checks.
4. The **Send to Storecove sandbox** action remains disabled unless sandbox configuration is explicitly provided.
5. Select **Export ZIP** for the local evidence skeleton.

Milestone 5A does not perform live Storecove API calls. When Storecove sandbox settings are provided for local testing, the backend still returns a mocked Storecove sandbox response so tests do not require real credentials or network access.

Planned environment variables:

```powershell
STORECOVE_SANDBOX_ENABLED=false
STORECOVE_API_BASE_URL=
STORECOVE_API_KEY=
STORECOVE_SENDER_LEGAL_ENTITY_ID=
STORECOVE_RECEIVER_LEGAL_ENTITY_ID=
```

Without those settings, the UI shows:

```text
Storecove sandbox is not configured. Add sandbox credentials to enable UK Peppol testing.
```

Production Storecove endpoints are rejected in Milestone 5A. Storecove API keys are redacted from evidence files. The UK evidence bundle can include the workbook snapshot, canonical invoice, validation report, redacted `storecove_request.json`, `storecove_response.json`, `storecove_status.json`, `provider_reference.txt`, country-pack manifest, evidence metadata, hashes, and a sandbox-only README where available.

## Audit Trail And Evidence Viewer

Select **Audit Trail** in the top navigation to review prior local uploads and output runs. The page shows a workbench list with upload timestamp, invoice number, country/regime, seller, buyer, currency, gross amount, validation status, XML generation status, external sandbox validation status, sandbox send status and evidence bundle availability.

Selecting a row opens the audit detail view. The detail view shows the source workbook filename, country pack/version, output profile, invoice summary, validation summary, generated outputs, XML validation summary, official validator status, external e-invoice.be validation status where applicable, e-invoice.be sandbox send status where applicable, Saudi QR/PDF output status where applicable, timestamps and hashes already held by the evidence metadata.

The evidence viewer lists available evidence files such as:

- `source_upload_snapshot.xlsx`
- `canonical_invoice.json`
- `validation_report.json`
- `xml_validation_report.json`
- `en16931_validation_report.json`
- `peppol_schematron_validation_report.json`
- `invoice.xml`
- `einvoicebe_validation_request.json`
- `einvoicebe_validation_response.json`
- `einvoicebe_send_request.json`
- `einvoicebe_send_response.json`
- `external_validation_status.json`
- `external_sandbox_send_status.json`
- Saudi QR/PDF files where applicable
- `evidence_metadata.json`
- `hashes.txt`

JSON, XML and text evidence can be previewed in the audit detail view. Binary files such as workbooks, QR images and PDFs are available through download actions. The evidence ZIP can also be downloaded again from the audit detail view. If a ZIP or file is not available, the UI shows that evidence is not available for the selected item.

Status labels remain deliberately conservative:

- `Generated only`: an output file was created locally.
- `External sandbox validation`: a sandbox provider validation result, not Peppol delivery.
- `Sandbox send attempted`: provider workflow evidence only.
- `Official validator not configured`: UBL XSD, EN16931 or Peppol Schematron artefacts have not run.
- `Not submitted`, `Not production-signed`, `No recipient acceptance claim`: no live authority or production delivery claim is made.

Audit storage is local only. The backend persists a lightweight audit index under ignored `server/storage/` so local audit records can survive a server restart on the same machine. This is not a multi-user database, document management system or access-controlled archive.

## Checks

Backend tests:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
.\.venv\Scripts\python -m pytest
```

Frontend tests and production build:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\apps\web
npm test
npm run build
```

## Build Pack

The implementation follows the documents in `docs/`. The key references are `01_product_scope.md`, `02_app_architecture.md`, `03_data_model_and_excel_template.md`, `04_validation_engine.md`, `05_country_pack_standard.md`, `08_output_bundle_and_audit_trail_spec.md`, `09_ui_design_spec.md`, and `11_milestones_and_acceptance_tests.md`.
