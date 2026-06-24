import type { CountryPack } from "../types";

interface CountryInfoPanelProps {
  pack: CountryPack | null;
}

export function CountryInfoPanel({ pack }: CountryInfoPanelProps) {
  if (!pack) {
    return (
      <section className="card stack">
        <h2>Country Compliance Pack</h2>
        <p className="muted">Country packs are loading.</p>
      </section>
    );
  }

  return (
    <section className="card stack country-info" aria-labelledby="country-info-heading">
      <div className="panel-title-row">
        <span className="panel-number">02</span>
        <h2 id="country-info-heading">Country Compliance Pack</h2>
      </div>
      <div className="regime-header">
        <div>
          <strong>{pack.display_name}</strong>
          <span>{pack.country_code} / {pack.pack_version}</span>
        </div>
        <span className="live-regime-pill">Regime facts</span>
      </div>
      <div className="compliance-scroll">
        <p className="lead">{pack.legal_regime_summary}</p>
        <InfoBlock title="Scope" items={pack.scope} />
        <InfoBlock title="Mandatory format" items={pack.mandatory_format} />
        <InfoBlock title="Transmission / clearance model" items={pack.transmission_or_clearance_model} />
        <InfoBlock title="QR / signature requirements" items={pack.qr_signature_requirements} />
        <InfoBlock title="Retention / audit notes" items={pack.retention_or_audit_notes} />
        <div className="info-block source-links">
          <h3>Official sources</h3>
          {pack.official_sources.map((source) => (
            <a href={source.url} key={source.url} rel="noreferrer" target={source.url.startsWith("http") ? "_blank" : undefined}>
              {source.label}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function InfoBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="info-block">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
