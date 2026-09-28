import type { Transition } from "../api/types";

export function TransitionBars({ transitions }: { transitions: Transition[] }) {
  const top = [...transitions].sort((a, b) => b.probability - a.probability).slice(0, 12);
  if (top.length === 0) {
    return <p className="state-empty">No outgoing transitions recorded.</p>;
  }
  return (
    <div>
      {top.map((t, i) => (
        <div className="bar-row" key={`${t.action}-${t.to_state_id}-${i}`} style={{ gridTemplateColumns: "1fr 70px" }}>
          <div>
            <div className="bar-label">
              <span>
                <strong>{t.action}</strong> &rarr; {t.to_state_id ?? "drive ends"}
              </span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.round(t.probability * 100)}%` }} />
            </div>
          </div>
          <div className="bar-value">{(t.probability * 100).toFixed(1)}%</div>
        </div>
      ))}
    </div>
  );
}
