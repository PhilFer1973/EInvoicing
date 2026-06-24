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
