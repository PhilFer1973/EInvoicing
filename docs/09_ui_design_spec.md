# 09 — UI Design Spec

## Design objective

Build a composed, premium, cool-toned, quietly futuristic finance compliance workbench. It should feel calm, precise and controlled, with a subtle AI-era quality. It must not look like a generic SaaS dashboard.

Codex must build from this spec, not from a vague screenshot interpretation.

## Design tokens

```css
:root {
  --canvas: #EFEDF6;
  --surface: rgba(255, 255, 255, 0.72);
  --surface-strong: rgba(255, 255, 255, 0.86);
  --surface-muted: rgba(245, 244, 250, 0.76);
  --hairline: rgba(120, 120, 150, 0.18);
  --hairline-strong: rgba(120, 120, 150, 0.28);
  --ink: #15182A;
  --ink-soft: #33384C;
  --muted: #5E6378;
  --muted-light: #7A8095;
  --accent-violet: #9B6CF5;
  --accent-violet-deep: #6A4BC8;
  --accent-cyan: #46D8E0;
  --accent-cyan-deep: #0E97A1;
  --success: #2F8F6B;
  --warning: #B98020;
  --danger: #B64A5A;
  --radius-lg: 22px;
  --radius-md: 16px;
  --radius-sm: 10px;
  --shadow-soft: 0 20px 60px rgba(45, 38, 80, 0.10);
  --shadow-card: 0 10px 30px rgba(45, 38, 80, 0.075);
  --gradient-accent: linear-gradient(135deg, #9B6CF5 0%, #46D8E0 100%);
}
```

## Page background

- Use `#EFEDF6` as the canvas.
- Add one soft top-right aurora glow.
- Do not use pure white as the page background.
- Do not use pure black text.
- Do not use dark cyberpunk styling.

Example:

```css
body {
  margin: 0;
  background: var(--canvas);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.app-shell::before {
  content: "";
  position: fixed;
  inset: -20% -10% auto auto;
  width: 620px;
  height: 620px;
  background: radial-gradient(circle, rgba(155,108,245,.10), rgba(70,216,224,.055), transparent 68%);
  pointer-events: none;
}
```

## Main layout

Desktop must be a three-column workbench.

```css
.workbench-grid {
  display: grid;
  grid-template-columns: 320px minmax(420px, 1fr) 380px;
  gap: 20px;
  max-width: 1440px;
  margin: 0 auto;
  padding: 28px;
}
```

Columns:

1. Left: setup and upload.
2. Centre: country compliance pack and validation.
3. Right: invoice review and export.

## Top navigation

Top nav only. No sidebar.

Required items:

- Left: product name `E-Invoicing Workbench`.
- Centre/right nav links: `E-Invoicing`, `Audit Trail`.
- Right icons/buttons: Settings, Help.

## Cards

```css
.card {
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(18px);
  padding: 18px;
}
```

Do not use heavy shadows. Do not use sharp square cards.

## Buttons

Primary button:

```css
.button-primary {
  border: none;
  color: white;
  background: var(--gradient-accent);
  border-radius: 999px;
  padding: 11px 16px;
  font-weight: 650;
}
```

Secondary button:

```css
.button-secondary {
  border: 1px solid var(--hairline-strong);
  background: rgba(255,255,255,.52);
  color: var(--ink-soft);
  border-radius: 999px;
  padding: 10px 15px;
}
```

## Screen structure

```html
<body class="app-shell">
  <header class="top-nav">
    <div class="brand">E-Invoicing Workbench</div>
    <nav>
      <a>E-Invoicing</a>
      <a>Audit Trail</a>
    </nav>
    <div class="top-actions">
      <button>Settings</button>
      <button>Help</button>
    </div>
  </header>

  <main class="workbench-grid">
    <section class="left-column"></section>
    <section class="center-column"></section>
    <section class="right-column"></section>
  </main>
</body>
```

## Left column components

### `CountrySelectorCard`

Content:

- heading: `Country pack`;
- options: Belgium / Peppol, Saudi Arabia / ZATCA, UK info only;
- support-level pill;
- boundary note.

Behaviour:

- changing country resets validation and generated outputs;
- Saudi shows strong non-clearance warning;
- UK disables generation.

Visual:

- selected country has violet/cyan accent border;
- no large flag tiles;
- use small country/regime labels.

### `UploadWorkbookCard`

Content:

- drag/drop area;
- file selector;
- expected sheets list;
- upload status.

States:

- no file;
- uploading;
- uploaded;
- parse failed.

### `ValidationSummaryCard`

States:

- not uploaded;
- validating;
- failed;
- passed;
- passed with warnings.

## Centre column components

### `CountryInfoPanel`

Must show:

- regime summary;
- legal invoice requirements;
- e-invoice requirements;
- V1 boundary;
- source status;
- output profile.

Saudi panel must visibly state:

> Not submitted to FATOORA. No ZATCA clearance stamp. Not a cleared Saudi tax invoice.

Belgium panel must state:

> Not transmitted through Peppol. No access point or Mercurius submission.

### `ValidationResultsPanel`

Groups:

- blocking errors;
- warnings requiring acknowledgement;
- non-blocking warnings;
- passed checks;
- technical validation status.

Do not show raw XML as the main view. Put technical details behind expanders.

## Right column components

### `InvoiceReviewCard`

Show:

- invoice number;
- seller;
- buyer;
- date/time;
- currency;
- net/tax/gross;
- number of lines;
- first few line details.

### `ExportPanel`

Belgium buttons:

- Generate XML;
- Generate ZIP bundle.

Saudi buttons:

- Generate XML;
- Generate Arabic/Bilingual Visual PDF;
- Generate QR;
- Generate ZIP bundle.

Saudi must require acknowledgement before ZIP export.

## Audit trail page

Top nav remains. Main content is a single wide card/table.

Columns:

- generated at;
- invoice number;
- country pack;
- output profile;
- status;
- warnings;
- pack version;
- download ZIP.

## Responsive behaviour

```css
@media (max-width: 1180px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }
}
```

Below tablet width, stack:

1. setup/upload;
2. country info/validation;
3. invoice/export.

## Negative design instructions

Do not build:

- a left sidebar;
- KPI dashboard cards;
- charts;
- chat UI;
- bottom fixed status bar;
- dark mode as default;
- neon cyberpunk effects;
- saturated blue SaaS theme;
- country flag tile UI;
- marketing landing page;
- irrelevant analytics.

## Visual QA checklist

Before UI is accepted:

- [ ] Background is violet-tinted near-white, not plain white.
- [ ] Desktop has exactly three main workbench columns.
- [ ] Top nav only; no sidebar.
- [ ] Cards use translucent/glass surfaces and subtle borders.
- [ ] Belgium and Saudi show different boundary warnings.
- [ ] Saudi export panel includes Arabic PDF and QR.
- [ ] Audit Trail is top-nav page, not a dashboard sidebar item.
- [ ] No live-submission buttons exist.
- [ ] No generic dashboard charts were added.
- [ ] CSS tokens are used instead of ad hoc colours.
