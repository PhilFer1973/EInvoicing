# E-Invoicing Workbench

Local V1 e-invoicing file generation and validation workbench.

This repository contains the build pack plus the Milestone 1 implementation:

- React + TypeScript + Vite frontend app shell.
- FastAPI backend skeleton.
- Country pack JSON loading for Belgium, Saudi Arabia and UK info-only.
- Workbook upload and parsing scaffold.
- Canonical invoice JSON construction scaffold.
- Validation result model and summary.
- Error/warning drawer.
- Evidence bundle preview skeleton.
- Audit Trail placeholder.

Milestone 1 does not generate Belgium XML, Saudi XML, Saudi PDF, QR codes, ZIP exports, Peppol transmission, ZATCA/FATOORA submission, production signing or authority clearance.

## Product Boundary

E-Invoicing Workbench is not an ERP, not a tax engine and not a live tax authority submission tool.

Compliance status in the app must remain honest:

> Generated and validated against the published schemas, validation artefacts, and configured country rules available in this application. Not submitted to tax authorities and not a substitute for professional compliance review.

Official artefact validation is shown as `not_configured` until a real validator artefact is wired and run.

## Project Structure

```text
apps/web/              React + TypeScript + Vite frontend
server/                FastAPI backend
country_packs/         Runtime country pack manifests
country_pack_stubs/    Original build-pack stubs
docs/                  V1 build pack
prompts/               Codex milestone prompts
```

## Backend Setup

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m playwright install chromium
python -m uvicorn app.main:app --reload --port 8000
```

`python -m playwright install chromium` is required once on each development machine for the Saudi Arabic/bilingual visual PDF renderer. It runs locally and does not connect to ZATCA/FATOORA.

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Backend tests:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\server
.\.venv\Scripts\Activate.ps1
pytest
```

## Frontend Setup

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\apps\web
npm install
npm run dev
```

The frontend defaults to:

```text
http://127.0.0.1:5173
```

The API base URL defaults to `http://localhost:8000`. To override it, create `apps/web/.env.local`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Frontend checks:

```powershell
cd C:\Users\Philip\Downloads\EInvoicing\apps\web
npm test
npm run build
```

## Saudi QR And Visual PDF Check

1. Start the backend and frontend using the commands above.
2. Open `http://127.0.0.1:5173`.
3. Select `Saudi Arabia / ZATCA`.
4. Upload `test_data/workbooks/SA-VALID-001.xlsx`.
5. Select `Generate` after validation completes, then use the generated-output dialog to open or download the XML, Phase-1-style QR image and Arabic/bilingual visual PDF. The same dialog shows the decoded QR fields and offers `Decoded JSON`.
6. Select `Export ZIP` to download the evidence bundle containing all generated artifacts.

The Saudi QR contains Base64-encoded TLV invoice-data tags 1-5 only, so a normal phone scanner may display encoded text rather than a sentence. The visual PDF is not PDF/A-3 and neither artifact is submitted, cleared or production-signed.

## Milestone 1 Acceptance Checks

- Backend `GET /health` returns OK.
- UI uses top navigation only: E-Invoicing, Audit Trail, Settings, Help.
- Desktop workbench uses the specified three-column layout.
- No sidebar, dashboard charts, KPI cards, analytics panels or chat interface.
- Country selector displays Belgium / Peppol, Saudi Arabia / ZATCA and UK info-only.
- Saudi boundary warning states that there is no FATOORA submission, no clearance stamp and no cleared Saudi tax invoice.
- Workbook upload flows through canonical invoice JSON before validation or output placeholders.
- Country outputs remain adapter-shaped placeholders until later milestones.
- Evidence bundle is a skeleton preview only in Milestone 1.

## Build Pack

Read the documents in `docs/` before changing milestone scope. The key files are:

1. `docs/01_product_scope.md`
2. `docs/02_app_architecture.md`
3. `docs/03_data_model_and_excel_template.md`
4. `docs/04_validation_engine.md`
5. `docs/05_country_pack_standard.md`
6. `docs/08_output_bundle_and_audit_trail_spec.md`
7. `docs/09_ui_design_spec.md`
8. `docs/11_milestones_and_acceptance_tests.md`

Do not proceed to Milestone 2 or later until Milestone 1 is accepted.
