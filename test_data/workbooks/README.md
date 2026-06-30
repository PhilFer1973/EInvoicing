# Workbook Fixtures

`BE-VALID-001.xlsx` is the Milestone 2A Belgium / Peppol domestic B2B services workbook fixture.

`BE-EINVOICEBE-VALIDATION-001.xlsx` is the Milestone 5B Belgium e-invoice.be external sandbox validation fixture.

`BE-EINVOICEBE-SEND-001.xlsx` is the Milestone 5C Belgium e-invoice.be sandbox send fixture. It uses the validation-passing Belgium seller Peppol ID `0208:0990251719` in the generated UBL and keeps the e-invoice.be tenant-owned sender Peppol ID `0208:099025170` as sandbox metadata/diagnostic context. The send request omits explicit sender query parameters so e-invoice.be can infer the sender from the configured sandbox tenant/provider context.

Known limitation: the e-invoice.be sandbox send flow reaches the provider and captures the provider response, but successful sandbox send is currently blocked by a sandbox tenant Peppol ID mismatch. External validation passes; send completion is parked pending provider clarification.

`SA-VALID-001.xlsx` is the Milestone 3A Saudi / ZATCA standard B2B tax invoice workbook fixture.

`UK-PEPPOL-SANDBOX-001.xlsx` is the Milestone 5A UK / 2029 Peppol roadmap sandbox-readiness workbook fixture.

They are generated from `server/tests/workbook_fixtures.py` and contain:

- `entities`
- `customers`
- `invoice_header`
- `invoice_lines`

These fixtures do not represent authority-submitted, cleared, reported or transmitted invoices. The UK workbook is a Storecove sandbox-readiness sample only and does not prove final UK 2029 statutory compliance.
