"""Verify the statistics core against known closed-form values.

Every p-value the suite reports comes from this module, so it is tested against
values that can be derived independently. If these break, no other result in
the suite can be trusted.
"""

from __future__ import annotations

import math
import random

import pytest

from research import stats


class TestGammaAndChiSquare:
    def test_gamma_q_matches_exponential_closed_form(self):
        # Q(1, x) = exp(-x) exactly.
        for x in (0.5, 1.0, 2.5, 7.0):
            assert stats.gamma_q(1.0, x) == pytest.approx(math.exp(-x), abs=1e-10)

    def test_chi_square_median_approximation(self):
        # The median of chi-square(k) sits near k*(1 - 2/(9k))^3.
        for dof in (1, 3, 8, 20):
            median = dof * (1.0 - 2.0 / (9.0 * dof)) ** 3
            assert stats.chi_square_sf(median, dof) == pytest.approx(0.5, abs=0.02)

    def test_chi_square_known_critical_values(self):
        # 95th percentiles from standard tables.
        assert stats.chi_square_sf(3.841, 1) == pytest.approx(0.05, abs=0.001)
        assert stats.chi_square_sf(5.991, 2) == pytest.approx(0.05, abs=0.001)
        assert stats.chi_square_sf(16.919, 9) == pytest.approx(0.05, abs=0.001)

    def test_zero_statistic_is_never_significant(self):
        assert stats.chi_square_sf(0.0, 5) == 1.0

    def test_invalid_shape_is_rejected(self):
        with pytest.raises(ValueError):
            stats.gamma_q(0.0, 1.0)


class TestNormalTail:
    def test_normal_sf_known_quantiles(self):
        assert stats.normal_sf(0.0) == pytest.approx(0.5, abs=1e-9)
        assert stats.normal_sf(1.645) == pytest.approx(0.05, abs=0.001)
        assert stats.normal_sf(1.960) == pytest.approx(0.025, abs=0.001)
        assert stats.normal_sf(2.576) == pytest.approx(0.005, abs=0.001)

    def test_two_sided_p_is_symmetric(self):
        for z in (0.3, 1.2, 2.8):
            assert stats.two_sided_normal_p(z) == pytest.approx(
                stats.two_sided_normal_p(-z), abs=1e-12
            )


class TestKolmogorovSmirnov:
    def test_uniform_sample_is_not_rejected(self):
        rng = random.Random(7)
        sample = [rng.random() for _ in range(3000)]
        assert stats.ks_uniform(sample)["p_value"] > 0.05

    def test_clearly_non_uniform_sample_is_rejected(self):
        rng = random.Random(7)
        # Squaring pushes mass toward zero.
        sample = [rng.random() ** 2 for _ in range(3000)]
        assert stats.ks_uniform(sample)["p_value"] < 0.001

    def test_tiny_sample_returns_neutral(self):
        assert stats.ks_uniform([0.1, 0.2])["p_value"] == 1.0


class TestWilsonInterval:
    def test_interval_brackets_the_point_estimate(self):
        low, high = stats.wilson_interval(96, 1000)
        assert low < 0.096 < high

    def test_interval_narrows_with_more_data(self):
        narrow = stats.wilson_interval(1000, 10000)
        wide = stats.wilson_interval(10, 100)
        assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])

    def test_degenerate_inputs_are_safe(self):
        assert stats.wilson_interval(0, 0) == (0.0, 0.0)
        low, high = stats.wilson_interval(0, 500)
        assert low == 0.0 and high > 0.0


class TestSerialTests:
    def test_white_noise_has_no_significant_autocorrelation(self):
        rng = random.Random(11)
        series = [rng.gauss(0.0, 1.0) for _ in range(4000)]
        correlations = stats.autocorrelation(series, max_lag=10)
        bound = stats.bartlett_bound(len(series))
        outside = [lag for lag, value in correlations.items() if abs(value) > bound]
        # At the 95% bound roughly one lag in twenty may exceed by chance.
        assert len(outside) <= 2

    def test_strong_trend_is_detected(self):
        correlations = stats.autocorrelation(list(range(1000)), max_lag=5)
        assert correlations[1] > 0.9

    def test_runs_test_flags_perfect_alternation(self):
        result = stats.runs_test([1.0, 2.0] * 200)
        # Maximal runs means far more than expected under independence.
        assert result["z_score"] > 5.0
        assert result["p_value"] < 1e-6

    def test_runs_test_accepts_random_series(self):
        rng = random.Random(3)
        series = [rng.random() for _ in range(2000)]
        assert stats.runs_test(series)["p_value"] > 0.05

    def test_runs_test_handles_constant_series(self):
        assert stats.runs_test([1.0] * 100)["p_value"] == 1.0


class TestResampling:
    def test_bootstrap_ci_brackets_the_true_mean(self):
        rng = random.Random(5)
        sample = [rng.gauss(10.0, 2.0) for _ in range(500)]
        low, high = stats.bootstrap_ci(sample, lambda s: sum(s) / len(s), iterations=500)
        assert low < 10.0 < high

    def test_bootstrap_is_deterministic_for_a_seed(self):
        sample = [float(i) for i in range(200)]
        mean = lambda s: sum(s) / len(s)
        first = stats.bootstrap_ci(sample, mean, iterations=300, seed=1)
        second = stats.bootstrap_ci(sample, mean, iterations=300, seed=1)
        assert first == second

    def test_permutation_test_accepts_unrelated_signal(self):
        rng = random.Random(13)
        flags = [rng.random() < 0.3 for _ in range(1500)]
        outcomes = [1.0 if rng.random() < 0.1 else 0.0 for _ in range(1500)]
        assert stats.permutation_test(flags, outcomes, iterations=500)["p_value"] > 0.05

    def test_permutation_test_detects_a_real_relationship(self):
        flags = [i % 2 == 0 for i in range(1000)]
        outcomes = [1.0 if flag else 0.0 for flag in flags]
        assert stats.permutation_test(flags, outcomes, iterations=500)["p_value"] < 0.01

    def test_permutation_test_rejects_mismatched_lengths(self):
        with pytest.raises(ValueError):
            stats.permutation_test([True, False], [1.0], iterations=10)
