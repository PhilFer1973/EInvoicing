# 00 — Build Pack Index

## Repository and local environment

- GitHub repository: https://github.com/PhilFer1973/EInvoicing
- Local development folder: `C:\Users\Philip\Downloads\EInvoicing`
- Recommended repository root name: `EInvoicing`

## Product name

**E-Invoicing Workbench**

## V1 one-sentence definition

A country-pack-driven web workbench that takes a controlled Excel invoice workbook, validates it, generates e-invoicing files for selected country packs, and creates an audit-ready evidence bundle — without live authority submission.

## V1 country packs

| Pack | V1 status | Output |
|---|---|---|
| `belgium_peppol` | Basic generator, final XSD clean-up pending | Peppol-style UBL XML + evidence bundle |
| `saudi_zatca` | Basic generator ready | ZATCA-style XML + Arabic/bilingual visual PDF + QR + evidence bundle |
| `uk_info` | Info-only placeholder | No generation |

## V1 milestones

1. Repository skeleton and local dev setup.
2. App shell and exact workbench UI.
3. Workbook upload and canonical invoice JSON.
4. Validation engine and audit persistence.
5. Belgium Peppol XML generator.
6. Saudi ZATCA-style XML, QR and Arabic/bilingual PDF.
7. ZIP evidence bundle and acceptance tests.

## Acceptance principle

A build is accepted only if it follows the scope and design exactly. A visually generic dashboard, live-submission buttons, or fake compliance claims are build failures.
