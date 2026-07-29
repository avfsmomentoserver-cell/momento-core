"""Test the clean tape against the provably-fair crash law.

The hypothesis under test is that the tape is drawn from

    P(X >= x) = p / x

with independent rounds. The commercial consequence is decided here: if this
holds, expected value is `p` at every cashout target and no history-based
signal can change it.

Each test also runs against a synthetic fair tape, so a failure distinguishes
"the real tape is unusual" from "the test is broken".
"""

from __future__ import annotations

import pytest

from conftest import synthetic_fair_tape
from research import distribution, stats

pytestmark = pytest.mark.tape


@pytest.fixture(scope="module")
def fair_multipliers():
    return [r["multiplier"] for r in synthetic_fair_tape()]


class TestHouseEdgeEstimate:
    def test_edge_is_small_and_positive(self, multipliers):
        estimate = distribution.estimate_house_edge(multipliers)
        assert estimate["house_edge"] is not None
        # A commercial crash game sits in the low single digits.
        assert 0.0 <= estimate["house_edge"] < 0.10, (
            f"implied house edge {estimate['house_edge']} is outside the plausible range"
        )

    def test_confidence_interval_contains_the_estimate(self, multipliers):
        estimate = distribution.estimate_house_edge(multipliers)
        low, high = estimate["house_edge_ci"]
        assert low <= estimate["house_edge"] <= high

    def test_instant_busts_are_present(self, multipliers):
        # The 1.00x atom is the mechanism that produces the edge.
        estimate = distribution.estimate_house_edge(multipliers)
        assert estimate["instant_bust"] > 0

    def test_recovers_a_known_edge_from_synthetic_data(self):
        tape = [r["multiplier"] for r in synthetic_fair_tape(house_edge=0.03)]
        estimate = distribution.estimate_house_edge(tape)
        assert estimate["house_edge"] == pytest.approx(0.03, abs=0.01)


class TestSurvivalConformance:
    def test_observed_survival_tracks_p_over_x(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        table = distribution.survival_table(multipliers, p)

        inconsistent = [row for row in table if not row["consistent"]]
        assert not inconsistent, (
            "survival deviates from the fair law at "
            f"{[(r['threshold'], r['z_score']) for r in inconsistent]}"
        )

    def test_ten_x_rate_matches_theory(self, multipliers):
        # The filtered export is exactly this population, so it is worth naming.
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        row = next(r for r in distribution.survival_table(multipliers, p) if r["threshold"] == 10.0)
        assert abs(row["z_score"]) < 3.0, (
            f"P(X>=10) observed {row['observed_rate']} vs expected {row['expected_rate']}"
        )

    def test_theoretical_survival_is_monotone(self):
        p = 0.99
        rates = [distribution.pareto_survival(x, p) for x in (1.0, 2.0, 10.0, 100.0)]
        assert rates == sorted(rates, reverse=True)


class TestBandGoodnessOfFit:
    def test_band_distribution_fits_the_fair_law(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        result = distribution.band_goodness_of_fit(multipliers, p)
        assert result["consistent"], (
            f"band distribution rejected the fair law: chi2={result['statistic']} "
            f"dof={result['degrees_of_freedom']} p={result['p_value']}"
        )

    def test_no_band_shows_an_extreme_residual(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        result = distribution.band_goodness_of_fit(multipliers, p)
        worst = max(result["bins"], key=lambda b: abs(b["std_residual"]))
        assert abs(worst["std_residual"]) < 4.0, f"band {worst['label']} is off-model"

    def test_every_expected_count_is_large_enough(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        result = distribution.band_goodness_of_fit(multipliers, p)
        # Merging must leave the chi-square approximation valid.
        assert all(b["expected"] >= distribution.MIN_EXPECTED_PER_BIN for b in result["bins"])

    def test_fits_synthetic_fair_data(self, fair_multipliers):
        p = distribution.estimate_house_edge(fair_multipliers)["p_estimate"]
        assert distribution.band_goodness_of_fit(fair_multipliers, p)["consistent"]


class TestProbabilityIntegralTransform:
    def test_transform_is_uniform(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        transform = distribution.probability_integral_transform(multipliers, p)
        result = stats.ks_uniform(transform)
        assert result["p_value"] > 0.01, (
            f"1/X is not uniform (KS D={result['statistic']}, p={result['p_value']}), "
            "which would mean the multiplier CDF is not p/x"
        )

    def test_transform_excludes_instant_busts(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        transform = distribution.probability_integral_transform(multipliers, p)
        assert all(0.0 < value < 1.0 for value in transform)


class TestTailBehaviour:
    def test_tail_index_is_consistent_with_one(self, multipliers):
        result = distribution.tail_conformance(multipliers)
        if result.get("tail_index") is None:
            pytest.skip(result.get("note", "tail index unavailable"))
        assert result["consistent"], (
            f"tail index {result['tail_index']} +/- {result['standard_error']} "
            "differs from the theoretical 1.0"
        )

    def test_extreme_outlier_is_expected_not_anomalous(self, multipliers):
        # A ~7000x round looks shocking but is unremarkable under a tail index
        # of 1: expected count above x is n*p/x.
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        biggest = max(multipliers)
        expected_above_1000 = len(multipliers) * distribution.pareto_survival(1000.0, p)
        assert biggest > 1000.0
        assert expected_above_1000 > 1.0, (
            "a four-figure multiplier should be expected at this sample size"
        )


class TestCashoutExpectedValue:
    """The central commercial result."""

    def test_no_cashout_target_is_profitable(self, multipliers):
        table = distribution.cashout_expected_values(multipliers)
        profitable = [row for row in table["targets"] if row["return_ci"][0] > 1.0]
        assert not profitable, (
            f"targets {[r['target'] for r in profitable]} appear profitable; "
            "reproduce on an independent tape before believing it"
        )

    def test_return_is_flat_across_targets(self, multipliers):
        # target * P(X >= target) = p for every target, so the profile is flat.
        table = distribution.cashout_expected_values(multipliers)
        returns = [
            row["return_per_unit"]
            for row in table["targets"]
            if row["hits"] >= 30
        ]
        assert max(returns) - min(returns) < 0.15, (
            f"expected value varies by {max(returns) - min(returns):.3f} across "
            "targets, which would mean exit choice matters"
        )

    def test_mean_return_is_just_below_one(self, multipliers):
        table = distribution.cashout_expected_values(multipliers)
        assert 0.85 < table["mean_return_per_unit"] < 1.0, (
            "mean return per unit staked should sit just below 1.0, i.e. the "
            "house edge, regardless of cashout target"
        )

    def test_matches_the_estimated_retention(self, multipliers):
        p = distribution.estimate_house_edge(multipliers)["p_estimate"]
        table = distribution.cashout_expected_values(multipliers)
        assert table["mean_return_per_unit"] == pytest.approx(p, abs=0.06)

    def test_holds_on_synthetic_fair_data(self, fair_multipliers):
        table = distribution.cashout_expected_values(fair_multipliers)
        assert table["return_spread"] < 0.15
        assert not [row for row in table["targets"] if row["return_ci"][0] > 1.0]
