import type { CountryPack } from "../types";

interface CountrySelectorCardProps {
  packs: CountryPack[];
  selectedPackId: string | null;
  onSelect: (packId: string) => void;
}

export function CountrySelectorCard({ packs, selectedPackId, onSelect }: CountrySelectorCardProps) {
  const selectedPack = packs.find((pack) => pack.country_pack_id === selectedPackId) ?? packs[0];

  return (
    <section className="card stack" aria-labelledby="country-pack-heading">
      <div className="panel-title-row">
        <span className="panel-number">01</span>
        <h2 id="country-pack-heading">Region select / Import</h2>
      </div>
      <label className="field-label" htmlFor="country-pack-select">Country / Regime</label>
      <select
        className="country-listbox"
        id="country-pack-select"
        onChange={(event) => onSelect(event.target.value)}
        size={Math.min(5, Math.max(3, packs.length))}
        value={selectedPack?.country_pack_id ?? ""}
      >
        {packs.map((pack) => (
          <option key={pack.country_pack_id} value={pack.country_pack_id}>
            {pack.display_name}
          </option>
        ))}
      </select>
    </section>
  );
}
