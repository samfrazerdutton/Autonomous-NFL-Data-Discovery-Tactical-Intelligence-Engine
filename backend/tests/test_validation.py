from __future__ import annotations

import numpy as np

from app.discovery.validation import (
    benjamini_hochberg,
    bootstrap_ci_mean,
    cohens_h,
    passes_min_sample,
    two_sample_proportion_test,
)


def test_benjamini_hochberg_matches_known_reference():
    # Classic textbook example: 5 p-values, alpha=0.05
    raw = [0.01, 0.02, 0.03, 0.04, 0.5]
    adjusted = benjamini_hochberg(raw, alpha=0.05)
    assert adjusted[:4] == [adjusted[0]] * 4  # first four collapse to the same adjusted value
    assert adjusted[0] < 0.05
    assert adjusted[4] > 0.05


def test_benjamini_hochberg_empty_input():
    assert benjamini_hochberg([]) == []


def test_bootstrap_ci_mean_contains_true_mean_on_large_sample():
    rng = np.random.default_rng(1)
    sample = rng.normal(loc=5.0, scale=1.0, size=2000)
    lo, hi = bootstrap_ci_mean(sample, n_boot=1000)
    assert lo < 5.0 < hi
    assert hi - lo < 0.5  # reasonably tight for n=2000


def test_cohens_h_zero_when_proportions_equal():
    assert abs(cohens_h(0.5, 0.5)) < 1e-9


def test_cohens_h_positive_when_first_larger():
    assert cohens_h(0.7, 0.3) > 0


def test_passes_min_sample():
    assert passes_min_sample(30, 30) is True
    assert passes_min_sample(29, 100) is False


def test_two_sample_proportion_test_detects_real_difference():
    rng = np.random.default_rng(0)
    a = rng.binomial(1, 0.8, 300)
    b = rng.binomial(1, 0.3, 300)
    result = two_sample_proportion_test(a, b)
    assert result.p_value < 0.01
    assert result.effect_size > 0
    assert result.ci_low > 0  # CI on (p_a - p_b) should exclude 0


def test_two_sample_proportion_test_no_difference_is_not_significant():
    rng = np.random.default_rng(0)
    a = rng.binomial(1, 0.5, 300)
    b = rng.binomial(1, 0.5, 300)
    result = two_sample_proportion_test(a, b)
    assert result.p_value > 0.05
