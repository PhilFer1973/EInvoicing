# 14 — Open Items and Deferred Scope

## Open items that do not block V1 basic build

### Belgium

- Complete, consistent UBL 2.1 XSD schema bundle.
- Primary Belgian legal invoice source / FPS Finance source for final legal invoice rule certainty.
- Full official Peppol artefact version reconciliation.
- Live Peppol delivery and participant lookup.

### Saudi

- ZATCA SDK / Compliance Enablement Toolbox integration.
- Sandbox credentials.
- API Swagger documentation for clearance/reporting.
- Production CSID onboarding.
- Production XAdES signing.
- Production previous invoice hash chain.
- PDF/A-3 with embedded XML and PAdES.

## Deferred country packs

Do not implement in first V1 build:

- France;
- Poland KSeF;
- Malaysia MyInvois;
- UAE PINT AE;
- India;
- Italy;
- Germany;
- Romania;
- Spain;
- Singapore;
- Australia/New Zealand;
- Brazil;
- Mexico;
- Chile;
- Argentina.

Keep architecture ready for them, but do not build them now.

## Deferred invoice scenarios

Do not implement in first V1 build:

- mixed VAT rates;
- credit notes;
- debit notes;
- simplified invoices;
- self-billing;
- prepayments;
- exports;
- exemptions;
- out-of-scope supplies;
- third-party billing;
- document-level allowances/charges.

Saudi source examples for exempt/export/out-of-scope/third-party should be saved as future fixtures, not used as V1 core acceptance.

## Deferred technical features

- Live authority APIs.
- Background validation jobs.
- Multi-user authentication.
- Supabase/Postgres production storage.
- Cloud deployment.
- Role-based access.
- Document deletion/retention policies beyond V1.
- PDF/A-3 production compliance.

## What must not be deferred

- Clear boundary warnings.
- Audit trail.
- Evidence bundle.
- Country pack versioning.
- Canonical model.
- UI design discipline.
- No fake compliance claims.
