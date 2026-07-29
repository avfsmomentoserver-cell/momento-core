"""Research strategies on the platform's own feature contract.

Each strategy here implements `features.base.BaseFeature`, so anything that
survives testing ports into `backend/features/` and the plugin inventory
without a rewrite. That contract is also why these are the right place to state
a hypothesis: `compute` produces the live metric, `backtest` produces the
evidence, and the two cannot drift apart.

The strategies are written to be *falsifiable*, not persuasive. Each one
returns an explicit `actionable` verdict from `research.independence`, and the
honest expected outcome on a sound crash curve is that every verdict is False.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from features.base import BaseFeature
from momento import linguistics as ling

from . import distribution, independence, stats

logger = logging.getLogger("research.strategies")

__all__ = [
    "CashoutTargetStrategy",
    "NextBandStrategy",
    "PressureReleaseStrategy",
    "STRATEGIES",
    "run_all",
]


class PressureReleaseStrategy(BaseFeature):
    """Target 1 — does accumulated pressure predict a moonshot release?

    Reuses the platform's existing resistance vocabulary (`CeilingDetector`,
    `PressureCalculator`) where available, and falls back to equivalent pure
    signals so the strategy remains runnable without the optional stack.
    """

    def __init__(self, lookback: int = 40, horizon: int = 10) -> None:
        self.lookback = lookback
        self.horizon = horizon

    def get_name(self) -> str:
        return "pressure_release"

    def get_description(self) -> str:
        return (
            "Tests the Forex-style accumulation/release hypothesis: whether "
            "pressure built under a resistance ceiling predicts a moonshot "
            "within the following horizon."
        )

    def get_metrics(self) -> List[str]:
        return [
            "ceiling_count",
            "dominant_ceiling",
            "total_pressure",
            "rounds_since_10x",
            "lift",
            "permutation_p_value",
            "actionable",
        ]

    def compute(self, rounds: Sequence[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
        multipliers = [float(r["multiplier"]) for r in rounds]
        if not multipliers:
            return {"ceiling_count": 0, "total_pressure": 0.0, "rounds_since_10x": 0}

        since = 0
        for value in reversed(multipliers):
            if value >= 10.0:
                break
            since += 1

        result: Dict[str, Any] = {
            "rounds_since_10x": since,
            "window": len(multipliers),
            "median_multiplier": round(stats.median(multipliers), 4),
        }

        try:
            from features.pressure.calculator import PressureCalculator
            from features.pressure.detector import CeilingDetector
        except ImportError:
            result["ceiling_count"] = 0
            result["total_pressure"] = 0.0
            result["pressure_source"] = "unavailable"
            return result

        ceilings = CeilingDetector().detect_resistance_ceilings(list(rounds))
        pressure = PressureCalculator().compute_pressure(list(rounds), ceilings)
        result.update(
            {
                "ceiling_count": len(ceilings),
                "dominant_ceiling": pressure.get("dominant_ceiling"),
                "total_pressure": pressure.get("total_pressure", 0.0),
                "release_probability_claimed": pressure.get("release_probability", 0.0),
                "pressure_source": "features.pressure",
            }
        )
        return result

    def backtest(self, rounds: Sequence[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        horizon = int(config.get("horizon", self.horizon))
        lookback = int(config.get("lookback", self.lookback))
        permutations = int(config.get("permutations", 2000))
        outcome = independence.test_pressure_release(
            rounds, lookback=lookback, horizon=horizon, permutations=permutations
        )
        return {
            "strategy": self.get_name(),
            "target": "moonshot_within_horizon",
            "actionable": outcome["hypothesis_supported"],
            "detail": outcome,
        }


class NextBandStrategy(BaseFeature):
    """Target 2 — is the next round's band predictable from recent state?

    Compares a state-conditioned predictor against the unconditional base rate.
    Because the base rate is itself the optimal predictor under independence,
    matching it is the expected result and beating it is the claim requiring
    proof.
    """

    def __init__(self, lookback: int = 40) -> None:
        self.lookback = lookback

    def get_name(self) -> str:
        return "next_band"

    def get_description(self) -> str:
        return (
            "Tests whether the recent window's shape and state predict the next "
            "round's band better than the unconditional band distribution."
        )

    def get_metrics(self) -> List[str]:
        return ["shape", "conditioned_accuracy", "base_rate_accuracy", "edge", "actionable"]

    def compute(self, rounds: Sequence[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
        multipliers = [float(r["multiplier"]) for r in rounds]
        if not multipliers:
            return {"shape": "seed", "modal_band": None}
        counts: Dict[str, int] = {}
        for value in multipliers:
            key = ling.band_for(value)["key"]
            counts[key] = counts.get(key, 0) + 1
        modal = max(counts.items(), key=lambda kv: kv[1])[0]
        return {
            "shape": ling.shape_of(multipliers[-20:]),
            "modal_band": modal,
            "band_counts": counts,
        }

    def backtest(self, rounds: Sequence[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        lookback = int(config.get("lookback", self.lookback))
        multipliers = [float(r["multiplier"]) for r in rounds]
        total = len(multipliers)
        if total <= lookback + 10:
            return {
                "strategy": self.get_name(),
                "actionable": False,
                "note": "insufficient rounds",
            }

        # Walk forward: predict each round's band from only prior rounds.
        conditioned_correct = 0
        base_correct = 0
        decisions = 0

        global_counts: Dict[str, int] = {}
        shape_counts: Dict[str, Dict[str, int]] = {}

        for index in range(lookback, total):
            window = multipliers[index - lookback : index]
            shape = ling.shape_of(window[-20:])
            actual = ling.band_for(multipliers[index])["key"]

            # Predict from state built strictly before this round.
            table = shape_counts.get(shape)
            if table:
                predicted = max(table.items(), key=lambda kv: kv[1])[0]
                if predicted == actual:
                    conditioned_correct += 1
            if global_counts:
                base = max(global_counts.items(), key=lambda kv: kv[1])[0]
                if base == actual:
                    base_correct += 1
            decisions += 1

            # Only now fold the outcome into the tables.
            global_counts[actual] = global_counts.get(actual, 0) + 1
            shape_counts.setdefault(shape, {})
            shape_counts[shape][actual] = shape_counts[shape].get(actual, 0) + 1

        conditioned_accuracy = conditioned_correct / decisions if decisions else 0.0
        base_accuracy = base_correct / decisions if decisions else 0.0
        low, high = stats.wilson_interval(conditioned_correct, decisions)

        # The conditioned predictor only counts as an edge if its interval
        # clears the base rate outright.
        actionable = low > base_accuracy

        return {
            "strategy": self.get_name(),
            "target": "next_round_band",
            "decisions": decisions,
            "conditioned_accuracy": round(conditioned_accuracy, 6),
            "conditioned_ci": (round(low, 6), round(high, 6)),
            "base_rate_accuracy": round(base_accuracy, 6),
            "edge": round(conditioned_accuracy - base_accuracy, 6),
            "actionable": actionable,
        }


class CashoutTargetStrategy(BaseFeature):
    """Target 3 — is any fixed cashout target better than any other?

    This is the strategy with a closed-form answer. Return per unit staked is
    `target * P(X >= target)`, which under `P(X >= x) = p / x` equals `p` for
    every target. The backtest reports the empirical profile so the invariance
    is visible in the data rather than asserted.
    """

    def get_name(self) -> str:
        return "cashout_target"

    def get_description(self) -> str:
        return (
            "Measures empirical return per unit staked across fixed cashout "
            "targets to test whether exit choice changes expected value."
        )

    def get_metrics(self) -> List[str]:
        return ["mean_return_per_unit", "return_spread", "best_target", "any_positive_edge"]

    def compute(self, rounds: Sequence[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
        multipliers = [float(r["multiplier"]) for r in rounds]
        return distribution.cashout_expected_values(multipliers)

    def backtest(self, rounds: Sequence[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        multipliers = [float(r["multiplier"]) for r in rounds]
        targets = config.get("targets") or distribution.DEFAULT_CASHOUT_TARGETS
        table = distribution.cashout_expected_values(multipliers, targets)

        rows = [row for row in table["targets"] if row["hits"] > 0]
        best = max(rows, key=lambda r: r["return_per_unit"]) if rows else None

        # A target only counts as an edge if its entire interval clears 1.0.
        profitable = [row for row in rows if row["return_ci"][0] > 1.0]

        return {
            "strategy": self.get_name(),
            "target": "fixed_cashout_expected_value",
            "mean_return_per_unit": table["mean_return_per_unit"],
            "return_spread": table["return_spread"],
            "best_target": best["target"] if best else None,
            "best_return_per_unit": best["return_per_unit"] if best else None,
            "targets_with_proven_edge": [row["target"] for row in profitable],
            "actionable": bool(profitable),
            "detail": table,
        }


STRATEGIES: List[BaseFeature] = [
    PressureReleaseStrategy(),
    NextBandStrategy(),
    CashoutTargetStrategy(),
]


def run_all(
    rounds: Sequence[Dict[str, Any]],
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Backtest every registered strategy and summarise the verdicts."""
    settings = dict(config or {})
    results = []
    for strategy in STRATEGIES:
        try:
            results.append(strategy.backtest(rounds, settings))
        except Exception as exc:  # a broken strategy must not hide the others
            logger.exception("strategy %s failed", strategy.get_name())
            results.append(
                {"strategy": strategy.get_name(), "error": str(exc), "actionable": False}
            )

    actionable = [r["strategy"] for r in results if r.get("actionable")]
    return {
        "strategies_run": len(results),
        "results": results,
        "actionable_strategies": actionable,
        "any_edge_found": bool(actionable),
    }
