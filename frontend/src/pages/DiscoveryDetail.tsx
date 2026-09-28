import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { StatRow } from "../components/StatRow";
import { WhyChain, type WhyStep } from "../components/WhyChain";
import { EvidenceList } from "../components/EvidenceList";

function formatRate(obj: Record<string, unknown>): string {
  const rate = (obj.pass_rate ?? obj.rate) as number | undefined;
  const n = obj.n as number | undefined;
  if (rate === undefined) return JSON.stringify(obj);
  return `${(rate * 100).toFixed(1)}%${n !== undefined ? ` (n=${n.toLocaleString()})` : ""}`;
}

export function DiscoveryDetail() {
  const { id = "" } = useParams();
  const { data: d, loading, error } = useAsync(() => api.discovery(id), [id]);
  const { data: evidence } = useAsync(() => api.discoveryEvidence(id), [id]);

  if (loading) return <div className="page state-loading">Loading discovery…</div>;
  if (error) return <div className="page state-error">Failed to load discovery: {error}</div>;
  if (!d) return null;

  const supporting = evidence?.filter((e) => e.role === "supporting") ?? [];
  const counterexamples = evidence?.filter((e) => e.role === "counterexample") ?? [];

  const steps: WhyStep[] = [
    {
      label: "Triggering condition",
      content: d.description,
    },
    {
      label: "Baseline",
      content: formatRate(d.baseline),
    },
    {
      label: "Observed",
      content: formatRate(d.observed),
    },
    {
      label: "Statistical test",
      content: `${d.statistical_test} — p=${d.p_value.toExponential(2)}, adjusted p=${d.adjusted_p_value.toExponential(
        2
      )} (Benjamini-Hochberg across this run's full hypothesis set), 95% CI [${d.confidence_interval[0].toFixed(
        3
      )}, ${d.confidence_interval[1].toFixed(3)}], effect size ${d.effect_size.toFixed(3)}${
        d.stability_score !== null ? `, stability ${d.stability_score.toFixed(2)}` : ""
      }.`,
    },
    {
      label: "Historical evidence",
      content:
        supporting.length > 0
          ? `${supporting.length} representative play${supporting.length === 1 ? "" : "s"} shown below (full sample size: ${d.sample_size.toLocaleString()}).`
          : "No representative plays recorded.",
    },
    {
      label: "Counterexamples",
      content: counterexamples.length > 0 ? `${counterexamples.length} shown below.` : "None recorded for this discovery type.",
    },
    {
      label: "Limitations",
      content: d.limitations,
    },
  ];

  return (
    <div className="page">
      <p className="page-subtitle">
        <Link to="/">&larr; Discoveries</Link>
      </p>
      <div className="page-header">
        <div>
          <span className="type-tag" data-type={d.discovery_type}>
            {d.discovery_type}
          </span>
          <h1 className="page-title" style={{ marginTop: 8 }}>
            {d.title}
          </h1>
          <p className="page-subtitle">
            {d.teams.join(", ")} &middot; {d.seasons.join(", ")}
          </p>
        </div>
      </div>

      <StatRow
        stats={[
          { label: "Sample size", value: d.sample_size.toLocaleString() },
          { label: "Effect size", value: d.effect_size.toFixed(3) },
          { label: "Adjusted p-value", value: d.adjusted_p_value.toExponential(2) },
          {
            label: "95% CI",
            value: `[${d.confidence_interval[0].toFixed(3)}, ${d.confidence_interval[1].toFixed(3)}]`,
          },
          { label: "Stability", value: d.stability_score !== null ? d.stability_score.toFixed(2) : "—" },
        ]}
      />

      <h2 className="section-label" style={{ marginTop: 32, fontSize: 13 }}>
        Why
      </h2>
      <WhyChain steps={steps} />

      <h2 className="section-label" style={{ fontSize: 13 }}>
        Evidence
      </h2>
      <EvidenceList items={supporting} />

      {counterexamples.length > 0 && (
        <>
          <h2 className="section-label" style={{ marginTop: 24, fontSize: 13 }}>
            Counterexamples
          </h2>
          <EvidenceList items={counterexamples} />
        </>
      )}

      <p className="limitations">
        Dataset version <span className="mono">{d.dataset_version}</span> &middot; algorithm version{" "}
        <span className="mono">{d.algorithm_version}</span> &middot; feature version{" "}
        <span className="mono">{d.feature_version}</span>
      </p>
    </div>
  );
}
