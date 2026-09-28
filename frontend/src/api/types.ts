export interface DiscoverySummary {
  id: string;
  discovery_type: "cluster" | "anomaly" | "changepoint" | "sequence";
  title: string;
  description: string;
  teams: string[];
  seasons: number[];
  sample_size: number;
  effect_size: number;
  p_value: number;
  adjusted_p_value: number;
  confidence_interval: [number, number];
  stability_score: number | null;
  novelty_score: number | null;
  dataset_version: string;
  algorithm_version: string;
  created_at: string;
}

export interface DiscoveryDetail extends DiscoverySummary {
  state_ids: string[];
  sequence_pattern: string[] | null;
  players: string[];
  baseline: Record<string, unknown>;
  observed: Record<string, unknown>;
  statistical_test: string;
  replication_score: number | null;
  evidence_ids: string[];
  counterexample_ids: string[];
  limitations: string;
  feature_version: string;
}

export interface EvidenceItem {
  id: string;
  discovery_id: string | null;
  game_id: string | null;
  play_id: string | null;
  role: "supporting" | "counterexample";
  description: string;
  source: string;
  dataset_version: string;
}

export interface StateNode {
  id: string;
  down: number | null;
  distance_bucket: string;
  field_zone: string;
  score_bucket: string;
  qtr: number;
  sample_size: number;
  pass_rate: number | null;
  run_rate: number | null;
  epa_mean: number | null;
  action_entropy: number | null;
  dataset_version: string;
}

export interface Transition {
  from_state_id: string;
  action: string;
  to_state_id: string | null;
  count: number;
  probability: number;
}

export interface DiscoveredState {
  id: string;
  algorithm: string;
  cluster_label: number;
  feature_signature: Record<string, unknown>;
  sample_size: number;
  teams: string[];
  seasons: number[];
  outcome_distribution: Record<string, number>;
  representative_play_ids: string[];
  novelty: number | null;
  stability: number | null;
  algorithm_version: string;
  dataset_version: string;
}

export interface SystemStatus {
  mode: "LIVE" | "LOCAL" | "DEMO";
  code_version: string;
  feature_version: string;
  algorithm_versions: Record<string, string>;
  dataset_versions: string[];
  last_ingestion: string | null;
  n_games: number;
  n_plays: number;
  n_states: number;
  n_discovered_states: number;
  n_transitions: number;
  n_discoveries: number;
  sportsdataio_configured: boolean;
}

export interface TeamSummary {
  team: string;
  games: number;
  plays: number;
}
