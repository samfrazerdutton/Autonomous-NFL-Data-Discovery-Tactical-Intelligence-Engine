import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { StatRow } from "../components/StatRow";
import { TransitionBars } from "../components/TransitionBars";

export function StateDetail() {
  const { id = "" } = useParams();
  const { data: state, loading, error } = useAsync(() => api.state(id), [id]);
  const { data: transitions } = useAsync(() => api.transitions(id), [id]);

  if (loading) return <div className="page state-loading">Loading state…</div>;
  if (error) return <div className="page state-error">Failed to load state: {error}</div>;
  if (!state) return null;

  return (
    <div className="page">
      <p className="page-subtitle">
        <Link to="/states">&larr; State Explorer</Link>
      </p>
      <div className="page-header">
        <div>
          <h1 className="page-title mono" style={{ fontSize: 24 }}>
            {state.id}
          </h1>
          <p className="page-subtitle">
            Down {state.down} &middot; {state.distance_bucket.replace(/_/g, " ")} &middot;{" "}
            {state.field_zone.replace(/_/g, " ")} &middot; {state.score_bucket} &middot; Q{state.qtr}
          </p>
        </div>
      </div>

      <StatRow
        stats={[
          { label: "Sample size", value: state.sample_size.toLocaleString() },
          { label: "Pass rate", value: state.pass_rate !== null ? `${(state.pass_rate * 100).toFixed(1)}%` : "—" },
          { label: "Run rate", value: state.run_rate !== null ? `${(state.run_rate * 100).toFixed(1)}%` : "—" },
          { label: "Mean EPA", value: state.epa_mean?.toFixed(3) ?? "—" },
          { label: "Action entropy", value: state.action_entropy?.toFixed(2) ?? "—" },
        ]}
      />

      <h2 className="section-label" style={{ marginTop: 32, fontSize: 13 }}>
        What usually happens next
      </h2>
      {transitions && <TransitionBars transitions={transitions} />}
    </div>
  );
}
