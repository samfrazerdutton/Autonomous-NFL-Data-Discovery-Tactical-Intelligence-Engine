"""Unsupervised state discovery (Section 8): benchmarks KMeans, Gaussian
Mixture, and HDBSCAN on the pre-snap STATE feature vector (never the
action/outcome columns -- see features/state_engine.py) and keeps whichever
configuration produces the most internally coherent clusters, measured by
silhouette score on a held-out subsample.

Every discovered cluster is then tested for whether its play-outcome profile
(pass rate) actually differs from the rest of the dataset -- clustering alone
never manufactures a Discovery; the statistical test does.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from app.discovery.validation import passes_min_sample, two_sample_proportion_test
from app.features.state_engine import STATE_FEATURE_COLUMNS

BENCHMARK_SUBSAMPLE = 6000
STABILITY_SUBSAMPLE = 4000
RNG_SEED = 42
MIN_CLUSTER_SAMPLE = 30


@dataclass
class ClusterResult:
    algorithm: str
    params: dict
    silhouette: float


@dataclass
class DiscoveredClusterCandidate:
    algorithm: str
    algorithm_params: dict
    cluster_label: int
    play_ids: list[str]
    feature_signature: dict
    teams: list[str]
    seasons: list[int]
    outcome: dict
    baseline: dict
    novelty: float
    stability: float
    stat: object


def _fit_kmeans(X: np.ndarray, k: int, seed: int = RNG_SEED) -> np.ndarray:
    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)


def _fit_gmm(X: np.ndarray, k: int, seed: int = RNG_SEED) -> np.ndarray:
    return GaussianMixture(n_components=k, random_state=seed, n_init=2).fit_predict(X)


def _fit_hdbscan(X: np.ndarray, min_cluster_size: int) -> np.ndarray:
    return HDBSCAN(min_cluster_size=min_cluster_size).fit_predict(X)


def benchmark_algorithms(X: np.ndarray, seed: int = RNG_SEED) -> tuple[str, dict, list[ClusterResult]]:
    """Try several algorithm/hyperparameter configurations, score each by
    silhouette on a subsample, and return the winning (algorithm, params)."""
    rng = np.random.default_rng(seed)
    n = len(X)
    sub_idx = rng.choice(n, size=min(BENCHMARK_SUBSAMPLE, n), replace=False)
    X_sub = X[sub_idx]

    candidates: list[tuple[str, dict, callable]] = [
        ("kmeans", {"k": k}, lambda k=k: _fit_kmeans(X_sub, k)) for k in (6, 10, 14)
    ] + [
        ("gmm", {"k": k}, lambda k=k: _fit_gmm(X_sub, k)) for k in (6, 10)
    ] + [
        ("hdbscan", {"min_cluster_size": m}, lambda m=m: _fit_hdbscan(X_sub, m)) for m in (60, 120)
    ]

    results: list[ClusterResult] = []
    best: tuple[str, dict, float] | None = None
    for name, params, fit in candidates:
        labels = fit()
        n_labels = len(set(labels)) - (1 if -1 in labels else 0)
        if n_labels < 2 or n_labels >= len(X_sub) - 1:
            score = -1.0
        else:
            try:
                score = silhouette_score(X_sub, labels)
            except ValueError:
                score = -1.0
        results.append(ClusterResult(algorithm=name, params=params, silhouette=score))
        if best is None or score > best[2]:
            best = (name, params, score)

    assert best is not None
    return best[0], best[1], results


def _fit_final(algorithm: str, params: dict, X: np.ndarray) -> np.ndarray:
    if algorithm == "kmeans":
        return _fit_kmeans(X, params["k"])
    if algorithm == "gmm":
        return _fit_gmm(X, params["k"])
    if algorithm == "hdbscan":
        return _fit_hdbscan(X, params["min_cluster_size"])
    raise ValueError(algorithm)


def _nearest_centroid_predict(X: np.ndarray, centroids: dict[int, np.ndarray]) -> np.ndarray:
    labels = np.array(list(centroids.keys()))
    matrix = np.stack([centroids[l] for l in labels])
    dists = ((X[:, None, :] - matrix[None, :, :]) ** 2).sum(axis=2)
    return labels[dists.argmin(axis=1)]


def measure_stability(algorithm: str, params: dict, X: np.ndarray, seed: int = RNG_SEED, n_splits: int = 3) -> float:
    """Split-half agreement: fit independently on two halves, project half A's
    centroids onto half B, and compare to half B's own independent labeling."""
    rng = np.random.default_rng(seed)
    n = len(X)
    sub_n = min(STABILITY_SUBSAMPLE, n)
    scores = []
    for i in range(n_splits):
        idx = rng.choice(n, size=sub_n, replace=False)
        rng.shuffle(idx)
        half = sub_n // 2
        idx_a, idx_b = idx[:half], idx[half:]
        labels_a = _fit_final(algorithm, params, X[idx_a])
        labels_b = _fit_final(algorithm, params, X[idx_b])
        valid_a = labels_a != -1
        if valid_a.sum() < 2 or len(set(labels_a[valid_a])) < 2:
            continue
        centroids = {
            int(l): X[idx_a][labels_a == l].mean(axis=0) for l in set(labels_a[valid_a])
        }
        projected_b = _nearest_centroid_predict(X[idx_b], centroids)
        scores.append(adjusted_rand_score(labels_b, projected_b))
    return float(np.mean(scores)) if scores else 0.0


def _outcome_profile(df: pl.DataFrame) -> dict:
    n = df.height
    if n == 0:
        return {}
    return {
        "n": n,
        "pass_rate": float(df["pass_play"].fill_null(False).cast(pl.Float64).mean()),
        "run_rate": float(df["rush_play"].fill_null(False).cast(pl.Float64).mean()),
        "epa_mean": float(df["epa"].mean()) if df["epa"].null_count() < n else None,
        "first_down_rate": float(df["first_down"].fill_null(False).cast(pl.Float64).mean()),
        "touchdown_rate": float(df["touchdown"].fill_null(False).cast(pl.Float64).mean()),
        "turnover_rate": float(
            (df["interception"].fill_null(False) | df["fumble_lost"].fill_null(False)).cast(pl.Float64).mean()
        ),
    }


def discover_clusters(states: pl.DataFrame) -> tuple[str, dict, list[DiscoveredClusterCandidate]]:
    fm = states.select(STATE_FEATURE_COLUMNS).fill_null(0)
    X_raw = fm.to_numpy()
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    algorithm, params, _bench = benchmark_algorithms(X)
    labels = _fit_final(algorithm, params, X)
    stability = measure_stability(algorithm, params, X)

    states = states.with_columns(pl.Series("cluster_label", labels))
    global_baseline = _outcome_profile(states)
    global_centroid = X.mean(axis=0)

    label_to_dist = {}
    for label in sorted(set(labels)):
        if label == -1:
            continue
        mask = labels == label
        if mask.sum() < MIN_CLUSTER_SAMPLE:
            continue
        dist = float(np.linalg.norm(X[mask].mean(axis=0) - global_centroid))
        label_to_dist[label] = dist
    max_dist = max(label_to_dist.values()) if label_to_dist else 1.0

    candidates: list[DiscoveredClusterCandidate] = []
    for label, dist in label_to_dist.items():
        cluster_df = states.filter(pl.col("cluster_label") == label)
        rest_df = states.filter(pl.col("cluster_label") != label)
        if not passes_min_sample(cluster_df.height, rest_df.height):
            continue

        sample_a = cluster_df["pass_play"].fill_null(False).cast(pl.Int8).to_numpy()
        sample_b = rest_df["pass_play"].fill_null(False).cast(pl.Int8).to_numpy()
        stat = two_sample_proportion_test(sample_a, sample_b, n_perm=3000, max_side_n=5000)

        mean_features = {c: float(cluster_df[c].mean()) for c in STATE_FEATURE_COLUMNS}
        dominant = {
            "down": cluster_df["down"].mode().to_list()[:1],
            "distance_bucket": cluster_df["distance_bucket"].mode().to_list()[:1],
            "field_zone": cluster_df["field_zone"].mode().to_list()[:1],
            "score_bucket": cluster_df["score_bucket"].mode().to_list()[:1],
        }

        candidates.append(
            DiscoveredClusterCandidate(
                algorithm=algorithm,
                algorithm_params=params,
                cluster_label=int(label),
                play_ids=cluster_df["id"].to_list(),
                feature_signature={**mean_features, "dominant": dominant},
                teams=sorted([t for t in cluster_df["posteam"].unique().to_list() if t]),
                seasons=sorted(cluster_df["season"].unique().to_list()),
                outcome=_outcome_profile(cluster_df),
                baseline=global_baseline,
                novelty=round(dist / max_dist, 4) if max_dist else 0.0,
                stability=stability,
                stat=stat,
            )
        )
    return algorithm, params, candidates
