# Statistical validation methodology

Every number a Discovery reports comes from `app/discovery/validation.py`.
This document is the reference a reviewer should be able to check the code
against.

## Effect size: Cohen's h

For two observed proportions p1, p2 (e.g. a cluster's pass rate vs. the
league baseline):

```
h = 2*arcsin(sqrt(p1)) - 2*arcsin(sqrt(p2))
```

The arcsine transform stabilizes variance across the full [0, 1] range of a
proportion, unlike a raw difference, which is why it's used instead of
`p1 - p2` as the reported effect size.

## Confidence interval: percentile bootstrap

For samples A and B (binary 0/1 arrays), `bootstrap_ci_diff_proportions`
resamples each with replacement `n_boot` times (default 2000), computes
`mean(A*) - mean(B*)` per resample, and reports the [2.5, 97.5] percentiles
of that distribution as the 95% CI on the true difference in proportions.
Implemented as one vectorized index-matrix draw (`rng.integers(0, n, (n_boot,
n))`) rather than a Python loop, which is what keeps a full discovery run
(dozens of hypotheses, each needing several thousand resamples) under two
minutes.

## Significance: permutation test

`permutation_test_proportions` pools A and B, repeatedly reshuffles the
pooled labels (`n_perm` times, default 5000, fewer for the large-baseline
sequence-motif comparisons -- see below), and asks what fraction of shuffles
produce a `|mean(A*) - mean(B*)|` at least as large as the one actually
observed. That fraction (with a +1/+1 continuity correction) is the p-value.
This makes no distributional assumption about the underlying proportions,
unlike a z-test, which matters when comparing rates built from a few dozen
plays.

For sequence-motif tests, where the league-baseline side can be tens of
thousands of overlapping drive-windows, `max_side_n` deterministically
subsamples an oversized side before pooling -- a runtime/precision tradeoff
(wider uncertainty on the p-value's own precision, not on the reported effect
size, which is always computed on the true full samples) that keeps a full
discovery run tractable.

## Stability: bootstrap sign agreement

`stability_bootstrap_proportion` resamples both groups `n_boot` times
(default 500) and reports the fraction of resamples where
`sign(mean(A*) - mean(B*))` matches the sign of the point estimate. A
discovery whose direction flips under resampling is not stable even if its
point-estimate p-value looks small.

For cluster discoveries specifically, stability is measured differently (see
`app/discovery/clustering.py::measure_stability`): the clustering
configuration is independently refit on two disjoint random halves of the
data, half A's cluster centroids are used to nearest-centroid-assign half B's
points, and the result is compared via Adjusted Rand Index to half B's own
independent clustering. This is a property of the *clustering configuration*
for the whole run, not a per-cluster number -- every cluster discovery from
the same run reports the same stability score, and the Discovery's
`limitations` field says so explicitly.

## Multiple-testing correction: Benjamini-Hochberg

A single discovery run tests dozens of hypotheses (one per cluster, one per
flagged team-week, one per team/motif pair, one changepoint per team). Testing
that many hypotheses at a raw alpha=0.05 would produce false discoveries by
construction. `app/discovery/engine.py::run_discovery` pools **every** raw
p-value produced across **every** sub-module in one run and applies
`statsmodels.stats.multitest.multipletests(..., method="fdr_bh")` once,
globally -- not once per sub-module, which would understate the true
multiple-testing burden. Only findings whose Benjamini-Hochberg-adjusted
p-value is below 0.05 are persisted as a Discovery.

## Minimum sample size

`passes_min_sample` (threshold: 30 per group, `MIN_SAMPLE_SIZE` in
`validation.py`) gates every comparison before a statistical test is even
run. A cluster, team-week, changepoint segment, or sequence-motif/team pair
that doesn't clear this bar never produces a hypothesis, regardless of how
extreme its raw rate looks.

## Train/validate separation

Change-point detection (`app/discovery/changepoint.py`) explicitly splits a
team's week-ordered series into a before-segment and after-segment at the
detected breakpoint and computes the reported statistics only from that
temporal split -- it never shuffles weeks out of chronological order.
