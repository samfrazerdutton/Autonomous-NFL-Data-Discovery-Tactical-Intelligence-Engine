export interface Stat {
  label: string;
  value: string;
}

export function StatRow({ stats }: { stats: Stat[] }) {
  return (
    <div className="stat-row">
      {stats.map((s) => (
        <div className="stat-cell" key={s.label}>
          <div className="label">{s.label}</div>
          <div className="value">{s.value}</div>
        </div>
      ))}
    </div>
  );
}
