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
- Saudi Arabia: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\SA-VALID-001.xlsx`
- United Kingdom: `C:\Users\Philip\Downloads\EInvoicing\test_data\workbooks\UK-PEPPOL-SANDBOX-001.xlsx`

The **Export Template** button downloads a four-sheet starter workbook: `entities`, `customers`, `invoice_header`, and `invoice_lines`. It includes a valid Belgium domestic B2B sample row and optional Saudi-oriented columns such as `invoice_time` and `description_ar`.

## Belgium Demo

1. Select `Belgium / Peppol BIS Billing 3.0`.
2. Upload `BE-VALID-001.xlsx`.
3. Select **Validate**, then **Generate**.
4. The generated-output view provides the XML; select **Export ZIP** for the evidence bundle.

The bundle contains the workbook snapshot, canonical invoice, validation report, Belgium XML, country-pack manifest, evidence metadata, and hashes.

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
