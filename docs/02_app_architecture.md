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
