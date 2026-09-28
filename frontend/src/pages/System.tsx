import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function SystemPage() {
  const { data, loading, error } = useAsync(() => api.system(), []);

  if (loading) return <div className="page state-loading">Loading system status…</div>;
  if (error) return <div className="page state-error">Failed to load system status: {error}</div>;
  if (!data) return null;

  const rows: [string, string][] = [
    ["Mode", data.mode],
    ["SportsDataIO configured", data.sportsdataio_configured ? "yes" : "no (LIVE mode inactive)"],
    ["Code version", data.code_version],
    ["Feature version", data.feature_version],
    ["Dataset versions", data.dataset_versions.join(", ") || "—"],
    ["Last ingestion", data.last_ingestion ? new Date(data.last_ingestion).toLocaleString() : "never"],
    ["Games ingested", data.n_games.toLocaleString()],
    ["Plays ingested", data.n_plays.toLocaleString()],
    ["State graph nodes", data.n_states.toLocaleString()],
    ["State graph transitions", data.n_transitions.toLocaleString()],
    ["Discovered clusters", data.n_discovered_states.toLocaleString()],
    ["Validated discoveries", data.n_discoveries.toLocaleString()],
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">System</h1>
          <p className="page-subtitle">Live counts and versioning for reproducibility — nothing here is cached copy.</p>
        </div>
      </div>

      <table className="ledger-table">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <td style={{ color: "var(--text-muted)", width: "40%" }}>{label}</td>
              <td className="mono">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-label" style={{ marginTop: 32, fontSize: 13 }}>
        Algorithm versions
      </h2>
      <table className="ledger-table">
        <tbody>
          {Object.entries(data.algorithm_versions).map(([name, version]) => (
            <tr key={name}>
              <td style={{ color: "var(--text-muted)", width: "40%" }}>{name}</td>
              <td className="mono">{version}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
