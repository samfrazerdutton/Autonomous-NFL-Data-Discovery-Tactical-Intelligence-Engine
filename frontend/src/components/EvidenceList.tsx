import type { EvidenceItem } from "../api/types";

export function EvidenceList({ items }: { items: EvidenceItem[] }) {
  if (items.length === 0) {
    return <p className="state-empty">No evidence recorded for this discovery.</p>;
  }
  return (
    <ul className="evidence-list">
      {items.map((e) => (
        <li key={e.id} className={`evidence-item${e.role === "counterexample" ? " counterexample" : ""}`}>
          <div className="meta">
            {e.game_id}
            {e.role === "counterexample" && <span className="counterexample-tag"> counterexample</span>}
          </div>
          <div>{e.description}</div>
        </li>
      ))}
    </ul>
  );
}
