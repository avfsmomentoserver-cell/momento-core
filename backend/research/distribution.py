"""Distribution conformance for crash-curve tapes.

A provably-fair crash curve draws its multiplier from

    P(X >= x) = p / x        for x >= 1, with p = 1 - house_edge

which means `U = p / X` is Uniform(0, p) and `log(X)` is exponential. That
gives three independent ways to check a recorded tape:

1. A closed-form maximum-likelihood estimate of the house edge.
2. A chi-square goodness-of-fit test across the band vocabulary.
3. A Kolmogorov-Smirnov test on the probability-integral transform.

The commercially important consequence is in `cashout_expected_values`: under
this law the expected return of cashing out at target `x` is `p` for *every*
reachable `x`. Expected value is invariant to the exit point, so no choice of
target, and no signal that selects when to bet, can move it.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from momento import linguistics as ling

from . import stats

__all__ = [
    "DEFAULT_CASHOUT_TARGETS",
    "band_goodness_of_fit",
    "cashout_expected_values",
    "estimate_house_edge",
    "pareto_survival",
    "probability_integral_transform",
    "survival_table",
    "tail_conformance",
]

DEFAULT_CASHOUT_TARGETS: List[float] = [1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0]

#: Minimum expected count per bin for the chi-square approximation to hold.
MIN_EXPECTED_PER_BIN = 5.0


def pareto_survival(x: float, p: float) -> float:
    """P(X >= x) for the house-edge Pareto law, clamped to [0, 1]."""
    if x <= 1.0:
        return min(1.0, max(0.0, p))
    return max(0.0, min(1.0, p / x))


def estimate_house_edge(multipliers: Sequence[float]) -> Dict[str, Any]:
    """Maximum-likelihood estimate of the retained fraction `p`.

    For this family the instant-bust rounds carry the edge: exact 1.00x results
    occur with probability `1 - p`. The MLE of `p` is therefore simply the
    fraction of rounds that paid above 1.00x, and its uncertainty is a binomial
    proportion interval.
    """
    values = [float(m) for m in multipliers]
    total = len(values)
    if total == 0:
        return {
            "rounds": 0,
            "survived": 0,
            "p_estimate": None,
            "house_edge": None,
            "house_edge_ci": None,
        }

    survived = sum(1 for m in values if m > 1.0)
    p_estimate = survived / total
    low, high = stats.wilson_interval(survived, total)

    return {
        "rounds": total,
        "survived": survived,
        "instant_bust": total - survived,
        "p_estimate": round(p_estimate, 6),
        "house_edge": round(1.0 - p_estimate, 6),
        # Interval on p inverts to an interval on the edge, so the bounds swap.
        "house_edge_ci": (round(1.0 - high, 6), round(1.0 - low, 6)),
    }


def survival_table(
    multipliers: Sequence[float],
    p: float,
    thresholds: Optional[Sequence[float]] = None,
) -> List[Dict[str, Any]]:
    """Observed versus theoretical survival at each threshold.

    Each row carries a Wilson interval on the observed rate and a z-score for
    the gap, so an apparent deviation can be read against its own noise.
    """
    values = [float(m) for m in multipliers]
    total = len(values)
    cuts = list(thresholds) if thresholds else list(ling.DISTRIBUTION_THRESHOLDS)

    rows: List[Dict[str, Any]] = []
    for cut in cuts:
        observed_count = sum(1 for m in values if m >= cut)
        observed_rate = observed_count / total if total else 0.0
        expected_rate = pareto_survival(cut, p)
        low, high = stats.wilson_interval(observed_count, total)

        if total > 0 and 0.0 < expected_rate < 1.0:
            standard_error = math.sqrt(expected_rate * (1.0 - expected_rate) / total)
            z_score = (observed_rate - expected_rate) / standard_error
            p_value = stats.two_sided_normal_p(z_score)
        else:
            z_score = 0.0
            p_value = 1.0

        rows.append(
            {
                "threshold": cut,
                "observed_count": observed_count,
                "expected_count": round(expected_rate * total, 2),
                "observed_rate": round(observed_rate, 6),
                "expected_rate": round(expected_rate, 6),
                "observed_ci": (round(low, 6), round(high, 6)),
                "z_score": round(z_score, 4),
                "p_value": round(p_value, 6),
                "consistent": p_value >= 0.01,
            }
        )
    return rows


def band_goodness_of_fit(multipliers: Sequence[float], p: float) -> Dict[str, Any]:
    """Chi-square goodness of fit across the band vocabulary.

    Bands are the platform's own unit of meaning, so a failure here would be
    directly actionable. Adjacent bands are merged upward until every expected
    count reaches `MIN_EXPECTED_PER_BIN`, keeping the approximation valid in
    the sparse tail.
    """
    values = [float(m) for m in multipliers]
    total = len(values)
    if total == 0:
        return {"statistic": 0.0, "degrees_of_freedom": 0, "p_value": 1.0, "bins": []}

    raw_bins: List[Dict[str, Any]] = []
    for band in ling.BANDS:
        low, high = band["lo"], band["hi"]
        observed = sum(1 for m in values if low <= m < high)
        probability = pareto_survival(low, p) - pareto_survival(high, p)
        raw_bins.append(
            {
                "label": band["key"],
                "lo": low,
                "hi": high,
                "observed": observed,
                "expected": probability * total,
            }
        )

    # Merge sparse bins upward so no expected count falls below the threshold.
    merged: List[Dict[str, Any]] = []
    for current in raw_bins:
        if merged and merged[-1]["expected"] < MIN_EXPECTED_PER_BIN:
            previous = merged[-1]
            previous["label"] = f"{previous['label']}+{current['label']}"
            previous["hi"] = current["hi"]
            previous["observed"] += current["observed"]
            previous["expected"] += current["expected"]
        else:
            merged.append(dict(current))

    while len(merged) > 2 and merged[-1]["expected"] < MIN_EXPECTED_PER_BIN:
        tail = merged.pop()
        previous = merged[-1]
        previous["label"] = f"{previous['label']}+{tail['label']}"
        previous["hi"] = tail["hi"]
        previous["observed"] += tail["observed"]
        previous["expected"] += tail["expected"]

    statistic = 0.0
    for entry in merged:
        if entry["expected"] > 0.0:
            residual = entry["observed"] - entry["expected"]
            statistic += (residual * residual) / entry["expected"]
            entry["std_residual"] = round(residual / math.sqrt(entry["expected"]), 4)
        else:
            entry["std_residual"] = 0.0
        entry["expected"] = round(entry["expected"], 3)

    # One degree of freedom is spent estimating p from the same sample.
    degrees_of_freedom = max(1, len(merged) - 1 - 1)
    p_value = stats.chi_square_sf(statistic, degrees_of_freedom)

    return {
        "statistic": round(statistic, 4),
        "degrees_of_freedom": degrees_of_freedom,
        "p_value": round(p_value, 6),
        "consistent": p_value >= 0.01,
        "bins": merged,
    }


def probability_integral_transform(multipliers: Sequence[float], p: float) -> List[float]:
    """Map surviving rounds onto Uniform(0, 1) under the fitted law.

    Conditional on X > 1, `p / X` is Uniform(0, p), so `1 / X` is uniform on
    (0, 1). Instant-bust rounds are excluded because they are the atom at 1.00x
    that `estimate_house_edge` already accounts for.
    """
    return [1.0 / float(m) for m in multipliers if float(m) > 1.0]


def tail_conformance(multipliers: Sequence[float]) -> Dict[str, Any]:
    """Hill estimator for the tail index above the ignition band.

    The theoretical law is Pareto with tail index 1.0. A materially different
    index would mean the tail is heavier or lighter than a fair curve, which is
    the deviation most likely to be exploitable if it were real.
    """
    threshold = 10.0
    excesses = [math.log(float(m) / threshold) for m in multipliers if float(m) >= threshold]
    count = len(excesses)
    if count < 30:
        return {
            "threshold": threshold,
            "exceedances": count,
            "tail_index": None,
            "note": "fewer than 30 exceedances; tail index not estimated",
        }

    mean_excess = sum(excesses) / count
    tail_index = 1.0 / mean_excess if mean_excess > 0 else None
    # Hill estimator standard error is alpha / sqrt(k).
    standard_error = (tail_index / math.sqrt(count)) if tail_index else None

    result: Dict[str, Any] = {
        "threshold": threshold,
        "exceedances": count,
        "tail_index": round(tail_index, 4) if tail_index else None,
        "standard_error": round(standard_error, 4) if standard_error else None,
        "theoretical_index": 1.0,
    }
    if tail_index and standard_error:
        z_score = (tail_index - 1.0) / standard_error
        result["z_score"] = round(z_score, 4)
        result["p_value"] = round(stats.two_sided_normal_p(z_score), 6)
        result["consistent"] = result["p_value"] >= 0.01
    return result


def cashout_expected_values(
    multipliers: Sequence[float],
    targets: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """Empirical return per unit staked for each fixed cashout target.

    A flat-stake strategy that always cashes out at `target` returns `target`
    when the round reaches it and 0 otherwise, so the empirical return is
    `target * P(X >= target)`.

    Under `P(X >= x) = p / x` this is `p` for every target. Observing a flat
    profile across two orders of magnitude is the clearest demonstration that
    exit choice cannot create an edge, and that anything which merely selects
    *when* to bet inherits the same `p`.
    """
    values = [float(m) for m in multipliers]
    total = len(values)
    cuts = list(targets) if targets else list(DEFAULT_CASHOUT_TARGETS)

    rows: List[Dict[str, Any]] = []
    for target in cuts:
        hits = sum(1 for m in values if m >= target)
        hit_rate = hits / total if total else 0.0
        expected_return = target * hit_rate
        low, high = stats.wilson_interval(hits, total)

        rows.append(
            {
                "target": target,
                "hits": hits,
                "hit_rate": round(hit_rate, 6),
                "return_per_unit": round(expected_return, 6),
                "return_ci": (round(target * low, 6), round(target * high, 6)),
                "edge_per_unit": round(expected_return - 1.0, 6),
            }
        )

    returns = [row["return_per_unit"] for row in rows if row["hits"] > 0]
    spread = (max(returns) - min(returns)) if returns else 0.0

    return {
        "rounds": total,
        "targets": rows,
        "mean_return_per_unit": round(sum(returns) / len(returns), 6) if returns else 0.0,
        "return_spread": round(spread, 6),
        "any_positive_edge": any(row["edge_per_unit"] > 0.0 for row in rows),
    }
