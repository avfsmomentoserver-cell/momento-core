"""Permutation testing.

The cheapest and highest-value check in the suite. Shuffling the round order
preserves the marginal distribution of multipliers exactly and destroys all
temporal structure. Re-running the identical walk-forward pipeline on shuffled
tapes therefore produces the distribution of skill scores obtainable from *no
structure at all*.

If the real skill score sits inside that distribution, the strategy learned
nothing, however good its hit rate looks in isolation. Reporting an edge without
this check is how a 55% hit rate on 1,484 events becomes a product claim it
cannot support.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Sequence


@dataclass
class PermutationResult:
    observed: float
    n_permutations: int
    null_mean: float = float("nan")
    null_p95: float = float("nan")
    percentile: float = float("nan")
    p_value: float = float("nan")
    null_samples: List[float] = field(default_factory=list)

    @property
    def significant(self) -> bool:
        """One-sided at 0.05. ``False`` is the expected outcome for a fair game."""
        return bool(self.p_value == self.p_value and self.p_value < 0.05)

    def as_dict(self, include_samples: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "observed": self.observed,
            "n_permutations": self.n_permutations,
            "null_mean": self.null_mean,
            "null_p95": self.null_p95,
            "percentile_vs_null": self.percentile,
            "p_value_one_sided": self.p_value,
            "significant_at_0.05": self.significant,
            "interpretation": (
                "Observed skill clears the shuffled null; investigate before "
                "believing it."
                if self.significant
                else "Observed skill is inside the shuffled null: no structure "
                "beyond what shuffling reproduces. This is a pass."
            ),
        }
        if include_samples:
            payload["null_samples"] = self.null_samples
        return payload


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return float(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac)


def permutation_test(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float],
    *,
    n_permutations: int = 200,
    seed: int = 20260729,
) -> PermutationResult:
    """Compare ``statistic(values)`` against its shuffled null distribution.

    ``statistic`` must run the *whole* pipeline, fit and score, on the series it
    is given. Anything fitted outside it escapes the null and makes the test
    meaningless.
    """
    observed = float(statistic(values))
    rng = random.Random(seed)
    series = list(values)

    null: List[float] = []
    for _ in range(max(0, n_permutations)):
        rng.shuffle(series)
        value = float(statistic(series))
        if value == value:  # drop NaN
            null.append(value)

    result = PermutationResult(observed=observed, n_permutations=len(null))
    if not null:
        return result

    null.sort()
    result.null_samples = null
    result.null_mean = sum(null) / len(null)
    result.null_p95 = _percentile(null, 0.95)
    result.percentile = 100.0 * sum(1 for v in null if v < observed) / len(null)
    # Add-one correction so a p-value can never be exactly zero.
    at_least = sum(1 for v in null if v >= observed)
    result.p_value = (at_least + 1) / (len(null) + 1)
    return result
