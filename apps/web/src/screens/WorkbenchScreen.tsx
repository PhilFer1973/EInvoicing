import { CountryInfoPanel } from "../components/CountryInfoPanel";
import { CountrySelectorCard } from "../components/CountrySelectorCard";
import { ReviewExportPanel } from "../components/ReviewExportPanel";
import { UploadWorkbookCard } from "../components/UploadWorkbookCard";
import type { CountryPack, UploadRecord } from "../types";

interface WorkbenchScreenProps {
  countryPacks: CountryPack[];
  selectedPackId: string | null;
  uploadRecord: UploadRecord | null;
  onPackSelect: (packId: string) => void;
  onUploadComplete: (record: UploadRecord) => void;
}

export function WorkbenchScreen({
  countryPacks,
  selectedPackId,
  uploadRecord,
  onPackSelect,
  onUploadComplete
}: WorkbenchScreenProps) {
  const selectedPack = countryPacks.find((pack) => pack.country_pack_id === selectedPackId) ?? countryPacks[0] ?? null;

  return (
    <main className="workbench-grid">
      <section className="left-column column-stack" aria-label="Setup and upload">
        <CountrySelectorCard packs={countryPacks} selectedPackId={selectedPack?.country_pack_id ?? null} onSelect={onPackSelect} />
        <UploadWorkbookCard selectedPackId={selectedPack?.country_pack_id ?? null} onUploadComplete={onUploadComplete} />
      </section>
      <section className="center-column column-stack" aria-label="Country pack and validation">
        <CountryInfoPanel pack={selectedPack} />
      </section>
      <section className="right-column column-stack" aria-label="Invoice review and export">
        <ReviewExportPanel pack={selectedPack} uploadRecord={uploadRecord} />
      </section>
    </main>
  );
}
