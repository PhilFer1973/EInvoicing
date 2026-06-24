# 10 — Codex Build Prompt

Use this as the first prompt to Codex after copying the build pack into the repository.

---

You are working in the repository:

- GitHub: https://github.com/PhilFer1973/EInvoicing
- Local folder: `C:\Users\Philip\Downloads\EInvoicing`

Build the V1 E-Invoicing Workbench exactly as specified in the `/docs` build pack.

## Required behaviour

Read these documents first and follow them strictly:

1. `docs/01_product_scope.md`
2. `docs/02_app_architecture.md`
3. `docs/03_data_model_and_excel_template.md`
4. `docs/04_validation_engine.md`
5. `docs/05_country_pack_standard.md`
6. `docs/06_belgium_peppol_pack_spec.md`
7. `docs/07_saudi_zatca_pack_spec.md`
8. `docs/08_output_bundle_and_audit_trail_spec.md`
9. `docs/09_ui_design_spec.md`
10. `docs/11_milestones_and_acceptance_tests.md`
12. `docs/12_repository_setup_and_commands.md`

## Build only V1

Build:

- React + TypeScript + Vite frontend;
- Python FastAPI backend;
- workbook upload;
- canonical invoice JSON construction;
- layered validation;
- country pack loading;
- Belgium Peppol basic XML generation;
- Saudi ZATCA-style XML generation;
- Saudi Arabic/bilingual visual PDF with QR;
- evidence bundle ZIP;
- local SQLite audit trail;
- exact UI described in `09_ui_design_spec.md`.

## Do not build

Do not build:

- live Peppol transmission;
- live ZATCA/FATOORA clearance;
- live ZATCA reporting;
- production cryptographic signing;
- production CSID onboarding;
- tax determination engine;
- ERP integration;
- manual invoice editing;
- multi-tenant client management;
- analytics dashboard;
- chat UI;
- sidebar navigation;
- bottom status bar;
- unsupported countries beyond placeholders.

## Critical architecture rules

1. Excel data must be converted to canonical invoice JSON before country output generation.
2. Country adapters must read canonical invoice JSON, not raw Excel rows.
3. Country logic must not be hard-coded into the UI.
4. Official validation must not be claimed unless the relevant official artefact validator actually runs.
5. If an artefact is missing or fails to configure, show `not configured` or `configuration error`, not `passed`.
6. Saudi output must always show non-clearance and non-production-signing warnings in V1.
7. Belgium output must always show non-transmission warning in V1.

## First milestone only

Start with Milestone 1:

- create repository structure;
- create FastAPI app skeleton;
- create React app skeleton;
- implement exact workbench UI shell from `09_ui_design_spec.md`;
- implement country pack manifest loading;
- implement placeholder API endpoints;
- implement local dev run instructions;
- add tests that prove the app starts.

Do not proceed to Belgium/Saudi generation until Milestone 1 is accepted.

## Acceptance condition

The UI must visually match the design spec: violet-tinted near-white background, no sidebar, no dashboard charts, three-column workbench, glass-like cards, violet/cyan accent, and clear country boundary warnings.

---

For later milestones, follow `docs/11_milestones_and_acceptance_tests.md`.
