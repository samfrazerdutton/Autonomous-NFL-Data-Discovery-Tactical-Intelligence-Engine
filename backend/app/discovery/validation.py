"""Statistical validation primitives shared by every discovery sub-module.

The discovery engine tests many hypotheses per run (one per cluster, one per
team-week, one per team/motif, ...), so every raw p-value produced anywhere in
`discovery/` must flow through `benjamini_hochberg` before a Discovery is
persisted (Section 16/18). No discovery is created from a p-value alone --
callers are expected to also check `sample_size >= MIN_SAMPLE_SIZE` and report
a bootstrap CI and effect size alongside it.

Bootstrap/permutation loops are vectorized (index matrices built in one numpy
call) rather than looped in Python -- this is what keeps a discovery run with
dozens of hypotheses, each needing a few thousand resamples, running in
seconds instead of minutes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from statsmodels.stats.multitest import multipletests

MIN_SAMPLE_SIZE = 30
SIGNIFICANCE_ALPHA = 0.05
RNG_SEED = 42


@dataclass
class TwoSampleResult:
    n_a: int
    n_b: int
    observed_a: float
    observed_b: float
    effect_size: float
    p_value: float
    ci_low: float
    ci_high: float
    stability: float


def passes_min_sample(*sizes: int) -> bool:
    return all(s >= MIN_SAMPLE_SIZE for s in sizes)


def cohens_h(p1: float, p2: float) -> float:
    """Effect size for a difference of two proportions, bounded roughly [-pi, pi]."""
    phi1 = 2 * np.arcsin(np.sqrt(np.clip(p1, 0, 1)))
    phi2 = 2 * np.arcsin(np.sqrt(np.clip(p2, 0, 1)))
    return float(phi1 - phi2)


def _subsample(rng: np.random.Generator, arr: np.ndarray, max_n: int | None) -> np.ndarray:
    if max_n is not None and len(arr) > max_n:
        return rng.choice(arr, size=max_n, replace=False)
    return arr


def _vectorized_bootstrap_means(rng: np.random.Generator, sample: np.ndarray, n_boot: int) -> np.ndarray:
    n = len(sample)
    idx = rng.integers(0, n, size=(n_boot, n))
    return sample[idx].mean(axis=1)


def bootstrap_ci_diff_proportions(
    sample_a: np.ndarray, sample_b: np.ndarray, n_boot: int = 2000, alpha: float = 0.05, seed: int = RNG_SEED
) -> tuple[float, float]:
    """Bootstrap CI on p_a - p_b for two binary (0/1) samples."""
    rng = np.random.default_rng(seed)
    diffs = _vectorized_bootstrap_means(rng, sample_a, n_boot) - _vectorized_bootstrap_means(rng, sample_b, n_boot)
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def bootstrap_ci_mean(sample: np.ndarray, n_boot: int = 2000, alpha: float = 0.05, seed: int = RNG_SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = _vectorized_bootstrap_means(rng, sample, n_boot)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def permutation_test_proportions(sample_a: np.ndarray, sample_b: np.ndarray, n_perm: int = 5000, seed: int = RNG_SEED) -> float:
    """Two-sided permutation test p-value for a difference in binary proportions (vectorized)."""
    rng = np.random.default_rng(seed)
    observed = abs(sample_a.mean() - sample_b.mean())
    pooled = np.concatenate([sample_a, sample_b])
    n = len(pooled)
    n_a = len(sample_a)
    # one shuffle-matrix instead of a Python loop: argsort of random keys == a permutation
    keys = rng.random((n_perm, n))
    perm_idx = np.argsort(keys, axis=1)
    permuted = pooled[perm_idx]
    diffs = np.abs(permuted[:, :n_a].mean(axis=1) - permuted[:, n_a:].mean(axis=1))
    count = int((diffs >= observed).sum())
    return (count + 1) / (n_perm + 1)


def stability_bootstrap_proportion(sample_a: np.ndarray, sample_b: np.ndarray, n_boot: int = 500, seed: int = RNG_SEED) -> float:
    """Fraction of bootstrap resamples where the sign of (p_a - p_b) matches the point estimate."""
    rng = np.random.default_rng(seed)
    sign = np.sign(sample_a.mean() - sample_b.mean())
    if sign == 0:
        return 0.0
    a_means = _vectorized_bootstrap_means(rng, sample_a, n_boot)
    b_means = _vectorized_bootstrap_means(rng, sample_b, n_boot)
    matches = int((np.sign(a_means - b_means) == sign).sum())
    return matches / n_boot


def two_sample_proportion_test(
    sample_a: np.ndarray, sample_b: np.ndarray, n_perm: int = 5000, max_side_n: int | None = None
) -> TwoSampleResult:
    """Full battery (effect size on the true samples; CI/p-value/stability on a
    deterministically subsampled version of oversized sides, when `max_side_n`
    is given, purely as a runtime/precision tradeoff for very large baselines)."""
    p_a, p_b = float(sample_a.mean()), float(sample_b.mean())

    rng = np.random.default_rng(RNG_SEED)
    test_a = _subsample(rng, sample_a, max_side_n)
    test_b = _subsample(rng, sample_b, max_side_n)

    ci_low, ci_high = bootstrap_ci_diff_proportions(test_a, test_b)
    p_value = permutation_test_proportions(test_a, test_b, n_perm=n_perm)
    stability = stability_bootstrap_proportion(test_a, test_b)
    return TwoSampleResult(
        n_a=len(sample_a),
        n_b=len(sample_b),
        observed_a=p_a,
        observed_b=p_b,
        effect_size=cohens_h(p_a, p_b),
        p_value=p_value,
        ci_low=ci_low,
        ci_high=ci_high,
        stability=stability,
    )


def benjamini_hochberg(p_values: list[float], alpha: float = SIGNIFICANCE_ALPHA) -> list[float]:
    if not p_values:
        return []
    _, adjusted, _, _ = multipletests(p_values, alpha=alpha, method="fdr_bh")
    return [float(p) for p in adjusted]
