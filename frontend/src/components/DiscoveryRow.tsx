import { Link } from "react-router-dom";
import type { DiscoverySummary } from "../api/types";

function formatP(p: number): string {
  if (p < 0.001) return "p<.001";
  return `p=${p.toFixed(3).replace(/^0/, "")}`;
}

export function DiscoveryRow({ d }: { d: DiscoverySummary }) {
  return (
    <Link to={`/discoveries/${d.id}`} className="d-row">
      <span className="type-tag" data-type={d.discovery_type}>
        {d.discovery_type}
      </span>
      <span className="d-body">
        <p className="d-title">{d.title}</p>
        <p className="d-desc">{d.description}</p>
      </span>
      <span className="d-stats">
        <span className="n">n={d.sample_size.toLocaleString()}</span>
        <span className="p">{formatP(d.adjusted_p_value)} (adj.)</span>
      </span>
    </Link>
  );
}
