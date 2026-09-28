import { useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { DiscoveryRow } from "../components/DiscoveryRow";
import type { DiscoverySummary } from "../api/types";

const TYPES: { key: string; label: string }[] = [
  { key: "", label: "All" },
  { key: "cluster", label: "Cluster" },
  { key: "anomaly", label: "Anomaly" },
  { key: "changepoint", label: "Changepoint" },
  { key: "sequence", label: "Sequence" },
];

export function DiscoveryFeed() {
  const [type, setType] = useState("");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const { data, loading, error, reload } = useAsync(
    () => api.discoveries(type ? { discovery_type: type } : {}),
    [type]
  );

  async function runDiscovery() {
    setRunning(true);
    setRunError(null);
    try {
      await api.runDiscovery();
      reload();
    } catch (e) {
      setRunError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Discoveries</h1>
          <p className="page-subtitle">
            Patterns the discovery engine found on its own, each backed by a validated statistical test.
          </p>
        </div>
        <button className="btn btn-primary" onClick={runDiscovery} disabled={running}>
          {running ? "Running discovery engine…" : "Find something I didn't ask"}
        </button>
      </div>

      {running && (
        <p className="page-subtitle" style={{ marginBottom: 16 }}>
          Re-clustering states, re-scanning for anomalies, change points, and sequence motifs across every
          ingested play — this runs the real engine, so it can take up to a minute.
        </p>
      )}
      {runError && <p className="state-error">Discovery run failed: {runError}</p>}

      <div className="discovery-toolbar">
        <div className="filter-row">
          {TYPES.map((t) => (
            <button
              key={t.key}
              className={`filter-chip${type === t.key ? " active" : ""}`}
              onClick={() => setType(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="state-loading">Loading discoveries…</p>}
      {error && <p className="state-error">Failed to load discoveries: {error}</p>}
      {data && data.length === 0 && (
        <p className="state-empty">
          No discoveries yet. Run the ingestion pipeline, then click "Find something I didn't ask."
        </p>
      )}
      {data && data.length > 0 && (
        <div className="ledger">
          {data.map((d: DiscoverySummary) => (
            <DiscoveryRow d={d} key={d.id} />
          ))}
        </div>
      )}
    </div>
  );
}
