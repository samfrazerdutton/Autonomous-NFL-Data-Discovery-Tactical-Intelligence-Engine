import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

function pct(v: number | null): string {
  return v === null ? "—" : `${(v * 100).toFixed(1)}%`;
}

export function States() {
  const navigate = useNavigate();
  const { data: nodes, loading, error } = useAsync(() => api.states({ min_sample_size: 20 }), []);
  const { data: clusters } = useAsync(() => api.discoveredStates(), []);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">State Explorer</h1>
          <p className="page-subtitle">
            Every state is down/distance/field-position/score/quarter before the snap — never the play call itself.
          </p>
        </div>
      </div>

      {loading && <p className="state-loading">Loading states…</p>}
      {error && <p className="state-error">Failed to load states: {error}</p>}

      {nodes && (
        <div className="table-scroll">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Down</th>
                <th>Distance</th>
                <th>Field zone</th>
                <th>Score</th>
                <th>Qtr</th>
                <th className="num">Plays</th>
                <th className="num">Pass %</th>
                <th className="num">EPA</th>
                <th className="num">Entropy</th>
              </tr>
            </thead>
            <tbody>
              {nodes.slice(0, 80).map((n) => (
                <tr key={n.id} className="clickable" onClick={() => navigate(`/states/${encodeURIComponent(n.id)}`)}>
                  <td>{n.down}</td>
                  <td>{n.distance_bucket.replace(/_/g, " ")}</td>
                  <td>{n.field_zone.replace(/_/g, " ")}</td>
                  <td>{n.score_bucket}</td>
                  <td>{n.qtr}</td>
                  <td className="num">{n.sample_size.toLocaleString()}</td>
                  <td className="num">{pct(n.pass_rate)}</td>
                  <td className="num">{n.epa_mean?.toFixed(3) ?? "—"}</td>
                  <td className="num">{n.action_entropy?.toFixed(2) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="page-title" style={{ fontSize: 22, marginTop: 40 }}>
        Discovered clusters
      </h2>
      <p className="page-subtitle" style={{ marginBottom: 16 }}>
        Unsupervised groupings found by the clustering benchmark — distinct from the deterministic states above.
      </p>
      {clusters && (
        <div className="table-scroll">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Algorithm</th>
                <th>Cluster</th>
                <th className="num">Plays</th>
                <th className="num">Pass %</th>
                <th className="num">Novelty</th>
                <th className="num">Stability</th>
              </tr>
            </thead>
            <tbody>
              {clusters.map((c) => (
                <tr key={c.id}>
                  <td>{c.algorithm}</td>
                  <td>#{c.cluster_label}</td>
                  <td className="num">{c.sample_size.toLocaleString()}</td>
                  <td className="num">{pct(c.outcome_distribution.pass_rate ?? null)}</td>
                  <td className="num">{c.novelty?.toFixed(2) ?? "—"}</td>
                  <td className="num">{c.stability?.toFixed(2) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="page-subtitle" style={{ marginTop: 24 }}>
        Looking for the discoveries generated from these states? See the <Link to="/">Discoveries feed</Link>.
      </p>
    </div>
  );
}
