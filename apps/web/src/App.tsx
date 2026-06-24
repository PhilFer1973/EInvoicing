import { useEffect, useMemo, useState } from "react";

import { TopNav } from "./components/TopNav";
import { fetchCountryPacks } from "./services/api";
import { AuditTrailScreen } from "./screens/AuditTrailScreen";
import { WorkbenchScreen } from "./screens/WorkbenchScreen";
import type { CountryPack, UploadRecord, View } from "./types";

export default function App() {
  const [activeView, setActiveView] = useState<View>("workbench");
  const [countryPacks, setCountryPacks] = useState<CountryPack[]>([]);
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);
  const [uploadRecord, setUploadRecord] = useState<UploadRecord | null>(null);
  const [loadState, setLoadState] = useState("Loading country packs");

  useEffect(() => {
    let isMounted = true;
    fetchCountryPacks()
      .then((packs) => {
        if (!isMounted) return;
        setCountryPacks(packs);
        setSelectedPackId(packs[0]?.country_pack_id ?? null);
        setLoadState(packs.length ? "Loaded" : "No country packs configured");
      })
      .catch((error: unknown) => {
        if (!isMounted) return;
        setLoadState(error instanceof Error ? error.message : "Country packs unavailable");
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const selectedPack = useMemo(
    () => countryPacks.find((pack) => pack.country_pack_id === selectedPackId) ?? countryPacks[0] ?? null,
    [countryPacks, selectedPackId]
  );

  function handlePackSelect(packId: string) {
    setSelectedPackId(packId);
    setUploadRecord(null);
  }

  return (
    <div className="app-shell">
      <TopNav activeView={activeView} onViewChange={setActiveView} />
      {countryPacks.length ? (
        activeView === "workbench" ? (
          <WorkbenchScreen
            countryPacks={countryPacks}
            onPackSelect={handlePackSelect}
            onUploadComplete={setUploadRecord}
            selectedPackId={selectedPack?.country_pack_id ?? null}
            uploadRecord={uploadRecord}
          />
        ) : (
          <AuditTrailScreen />
        )
      ) : (
        <main className="audit-page">
          <section className="card audit-card">
            <p>{loadState}</p>
          </section>
        </main>
      )}
    </div>
  );
}

