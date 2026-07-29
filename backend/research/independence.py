"""Independence testing — does any past state predict the next round?

This module answers the question the platform's analytics implicitly assume a
yes to. The Forex framing behind the pressure and resistance features supposes
that energy accumulates under a ceiling and later releases. In a continuous
auction that mechanism is real: there is an order book, inventory and
participants whose unfilled interest persists across time.

A crash curve has none of that. Each round is an independent draw from a fixed
CDF, so the joint distribution factorises and

    P(X_next | anything about X_1..X_n) = P(X_next)

So these tests are deliberately built to *fail to reject*. Each one takes a
signal the platform already computes and asks whether rounds following the
signal differ from rounds that do not. Conditional band distributions are
compared with chi-square, mean outcomes with a permutation test that shuffles
the signal-to-outcome pairing, and serial structure with autocorrelation and
runs tests.

If every test returns "no detectable dependence", the accumulation narrative is
falsified on this tape and the honest product is verification and harm
reduction. If any test rejects robustly, that is an RNG defect and a security
disclosure.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence

from momento import linguistics as ling

from . import stats

__all__ = [
    "SignalResult",
    "conditional_band_test",
    "gap_independence",
    "serial_structure",
    "signal_lift",
    "test_pressure_release",
]

#: Outcome horizon: does a moonshot land within this many rounds of a signal?
DEFAULT_HORIZON = 10

#: Multiplier defining a moonshot outcome, matching linguistics.BANDS.
MOONSHOT_THRESHOLD = 20.0

SignalResult = Dict[str, Any]


def _band_index(multiplier: float) -> int:
    key = ling.band_for(multiplier)["key"]
    return ling.BAND_KEYS.index(key)


def conditional_band_test(
    multipliers: Sequence[float],
    flags: Sequence[bool],
) -> Dict[str, Any]:
    """Chi-square test that the next round's band depends on a signal.

    `flags[i]` must describe the state *before* round `i`, using only rounds
    strictly earlier than `i`. Bands are merged upward so every expected count
    stays above 5.
    """
    values = [float(m) for m in multipliers]
    if len(values) != len(flags):
        raise ValueError("multipliers and flags must be the same length")

    band_count = len(ling.BAND_KEYS)
    flagged = [0] * band_count
    unflagged = [0] * band_count

    for value, flag in zip(values, flags):
        index = _band_index(value)
        if flag:
            flagged[index] += 1
        else:
            unflagged[index] += 1

    total_flagged = sum(flagged)
    total_unflagged = sum(unflagged)
    if total_flagged < 20 or total_unflagged < 20:
        return {
            "statistic": 0.0,
            "degrees_of_freedom": 0,
            "p_value": 1.0,
            "dependent": False,
            "note": "insufficient observations in one arm",
            "flagged": total_flagged,
            "unflagged": total_unflagged,
        }

    # Merge bands upward until both arms expect at least 5 in every bin.
    total = total_flagged + total_unflagged
    bins: List[Dict[str, Any]] = []
    for index in range(band_count):
        combined = flagged[index] + unflagged[index]
        entry = {
            "label": ling.BAND_KEYS[index],
            "flagged": flagged[index],
            "unflagged": unflagged[index],
            "combined": combined,
        }
        if bins and min(
            bins[-1]["combined"] * total_flagged / total,
            bins[-1]["combined"] * total_unflagged / total,
        ) < 5.0:
            previous = bins[-1]
            previous["label"] = f"{previous['label']}+{entry['label']}"
            previous["flagged"] += entry["flagged"]
            previous["unflagged"] += entry["unflagged"]
            previous["combined"] += entry["combined"]
        else:
            bins.append(entry)

    while len(bins) > 2 and min(
        bins[-1]["combined"] * total_flagged / total,
        bins[-1]["combined"] * total_unflagged / total,
    ) < 5.0:
        tail = bins.pop()
        previous = bins[-1]
        previous["label"] = f"{previous['label']}+{tail['label']}"
        previous["flagged"] += tail["flagged"]
        previous["unflagged"] += tail["unflagged"]
        previous["combined"] += tail["combined"]

    statistic = 0.0
    for entry in bins:
        for arm, arm_total in (("flagged", total_flagged), ("unflagged", total_unflagged)):
            expected = entry["combined"] * arm_total / total
            if expected > 0.0:
                residual = entry[arm] - expected
                statistic += (residual * residual) / expected

    degrees_of_freedom = max(1, len(bins) - 1)
    p_value = stats.chi_square_sf(statistic, degrees_of_freedom)

    return {
        "statistic": round(statistic, 4),
        "degrees_of_freedom": degrees_of_freedom,
        "p_value": round(p_value, 6),
        "dependent": p_value < 0.01,
        "flagged": total_flagged,
        "unflagged": total_unflagged,
        "bins": bins,
    }


def signal_lift(
    rounds: Sequence[Dict[str, Any]],
    signal: Callable[[Sequence[float]], bool],
    name: str,
    lookback: int = 40,
    horizon: int = DEFAULT_HORIZON,
    threshold: float = MOONSHOT_THRESHOLD,
    permutations: int = 2000,
) -> SignalResult:
    """Measure whether a signal lifts the rate of a moonshot within `horizon`.

    Causality is enforced structurally: at decision index `i` the signal sees
    only `multipliers[i - lookback:i]`, and the outcome is drawn from
    `multipliers[i:i + horizon]`. The windows cannot overlap, so a signal can
    never peek at its own outcome.

    Reported lift is accompanied by a permutation p-value, because on 15,000
    rounds a lift of a few percentage points is routinely produced by chance.
    """
    multipliers = [float(r["multiplier"]) for r in rounds]
    total = len(multipliers)

    flags: List[bool] = []
    outcomes: List[float] = []
    next_round: List[float] = []

    for index in range(lookback, total - horizon):
        window = multipliers[index - lookback : index]
        future = multipliers[index : index + horizon]
        flags.append(bool(signal(window)))
        outcomes.append(1.0 if max(future) >= threshold else 0.0)
        next_round.append(multipliers[index])

    decisions = len(flags)
    fired = sum(1 for f in flags if f)
    if decisions == 0 or fired == 0 or fired == decisions:
        return {
            "signal": name,
            "decisions": decisions,
            "fired": fired,
            "note": "signal never fired, or fired on every decision",
            "actionable": False,
        }

    hits_when_fired = sum(o for f, o in zip(flags, outcomes) if f)
    hits_when_idle = sum(o for f, o in zip(flags, outcomes) if not f)
    idle = decisions - fired

    rate_fired = hits_when_fired / fired
    rate_idle = hits_when_idle / idle
    base_rate = sum(outcomes) / decisions

    fired_ci = stats.wilson_interval(int(hits_when_fired), fired)
    idle_ci = stats.wilson_interval(int(hits_when_idle), idle)
    permutation = stats.permutation_test(flags, outcomes, iterations=permutations)

    # A signal is only actionable if the intervals separate AND the
    # permutation test survives a Bonferroni-style threshold.
    intervals_disjoint = fired_ci[0] > idle_ci[1] or idle_ci[0] > fired_ci[1]
    actionable = intervals_disjoint and permutation["p_value"] < 0.01

    return {
        "signal": name,
        "decisions": decisions,
        "fired": fired,
        "fire_rate": round(fired / decisions, 6),
        "base_rate": round(base_rate, 6),
        "rate_when_fired": round(rate_fired, 6),
        "rate_when_idle": round(rate_idle, 6),
        "lift": round(rate_fired - rate_idle, 6),
        "rate_when_fired_ci": (round(fired_ci[0], 6), round(fired_ci[1], 6)),
        "rate_when_idle_ci": (round(idle_ci[0], 6), round(idle_ci[1], 6)),
        "permutation_p_value": permutation["p_value"],
        "intervals_disjoint": intervals_disjoint,
        "actionable": actionable,
        "next_round_band_test": conditional_band_test(next_round, flags),
        "horizon": horizon,
        "threshold": threshold,
    }


def serial_structure(multipliers: Sequence[float], max_lag: int = 20) -> Dict[str, Any]:
    """Autocorrelation and runs tests on the multiplier series.

    Raw multipliers are heavy-tailed enough that a single cosmic round dominates
    the sample covariance, so autocorrelation is computed on `log(multiplier)`,
    which is exponential and well behaved under the theoretical law.
    """
    values = [float(m) for m in multipliers]
    if len(values) < 50:
        return {"note": "fewer than 50 rounds; serial tests not run"}

    log_values = [math.log(max(1.0, v)) for v in values]
    correlations = stats.autocorrelation(log_values, max_lag=max_lag)
    bound = stats.bartlett_bound(len(log_values))

    exceedances = {
        lag: value for lag, value in correlations.items() if abs(value) > bound
    }

    # Ljung-Box portmanteau across all reported lags.
    count = len(log_values)
    ljung_box = count * (count + 2.0) * sum(
        (value * value) / (count - lag) for lag, value in correlations.items()
    )
    ljung_p = stats.chi_square_sf(ljung_box, max(1, len(correlations)))

    return {
        "rounds": count,
        "autocorrelation": correlations,
        "white_noise_bound": round(bound, 6),
        "lags_outside_bound": exceedances,
        "ljung_box": round(ljung_box, 4),
        "ljung_box_p_value": round(ljung_p, 6),
        "runs_test_median": stats.runs_test(values),
        "runs_test_moonshot": stats.runs_test(values, threshold=MOONSHOT_THRESHOLD),
        "serially_dependent": ljung_p < 0.01,
    }


def gap_independence(
    multipliers: Sequence[float],
    threshold: float = MOONSHOT_THRESHOLD,
) -> Dict[str, Any]:
    """Test whether waiting between rare events changes their arrival rate.

    This is the "it is due" belief stated precisely. For independent draws the
    gaps between events above `threshold` are geometric, so the hazard rate is
    flat: the chance the next round is an event does not grow with the drought.
    Gaps are split at their median and the two halves compared, and the
    coefficient of variation is checked against the geometric value of ~1.
    """
    values = [float(m) for m in multipliers]
    indices = [i for i, m in enumerate(values) if m >= threshold]
    if len(indices) < 30:
        return {
            "threshold": threshold,
            "events": len(indices),
            "note": "fewer than 30 events; gap analysis not run",
        }

    gaps = [b - a for a, b in zip(indices, indices[1:])]
    mean_gap = sum(gaps) / len(gaps)
    variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
    coefficient_of_variation = math.sqrt(variance) / mean_gap if mean_gap else 0.0

    # Hazard check: after a longer-than-median drought, is the event nearer?
    cut = stats.median(gaps)
    after_long = [g for g in gaps if g > cut]
    after_short = [g for g in gaps if g <= cut]

    flags = [g > cut for g in gaps[:-1]]
    following = [float(g) for g in gaps[1:]]
    permutation = stats.permutation_test(flags, following)

    return {
        "threshold": threshold,
        "events": len(indices),
        "mean_gap": round(mean_gap, 4),
        "median_gap": round(cut, 4),
        "gap_cv": round(coefficient_of_variation, 4),
        "geometric_cv": round(math.sqrt(1.0 - 1.0 / mean_gap), 4) if mean_gap > 1 else None,
        "mean_gap_after_long_drought": round(
            sum(after_long) / len(after_long), 4
        ) if after_long else None,
        "mean_gap_after_short_drought": round(
            sum(after_short) / len(after_short), 4
        ) if after_short else None,
        "permutation_p_value": permutation["p_value"],
        "drought_predicts_next_gap": permutation["p_value"] < 0.01,
    }


def test_pressure_release(
    rounds: Sequence[Dict[str, Any]],
    lookback: int = 40,
    horizon: int = DEFAULT_HORIZON,
    permutations: int = 2000,
) -> Dict[str, Any]:
    """Evaluate the accumulation/release hypothesis in its strongest forms.

    Each signal below is a concrete reading of "pressure has built up and is
    about to release", expressed only from rounds strictly before the decision
    point. All are tested with the same causal harness and multiplicity-aware
    thresholds.

    `permutations` is the cost driver: each signal shuffles the full outcome
    vector that many times. The smallest reportable p-value is
    `1 / (permutations + 1)`, so 400 still resolves the 0.01 threshold every
    gate uses while running roughly five times faster.
    """

    def drought(window: Sequence[float]) -> bool:
        """No round above 10x for the whole lookback — maximum stored pressure."""
        return max(window) < 10.0

    def compression(window: Sequence[float]) -> bool:
        """Recent variance in the bottom quartile of the window — a coiling shelf."""
        if len(window) < 20:
            return False
        points = [ling.to_points(m) for m in window]
        recent = points[-10:]
        recent_spread = max(recent) - min(recent)
        full_spread = max(points) - min(points)
        return full_spread > 0 and recent_spread < 0.25 * full_spread

    def ceiling_touches(window: Sequence[float]) -> bool:
        """Repeated rejections just under 10x — a tested resistance ceiling."""
        touches = sum(1 for m in window[-20:] if 7.0 <= m < 10.0)
        return touches >= 3

    def ascending_pressure(window: Sequence[float]) -> bool:
        """Rising floor with no release — the classic accumulation shape."""
        if len(window) < 20:
            return False
        first = window[: len(window) // 2]
        second = window[len(window) // 2 :]
        return (
            stats.median(second) > stats.median(first) * 1.15
            and max(second) < 10.0
        )

    def cold_streak(window: Sequence[float]) -> bool:
        """Ten consecutive sub-2x rounds — the streak players call \"due\"."""
        return all(m < 2.0 for m in window[-10:])

    signals: Dict[str, Callable[[Sequence[float]], bool]] = {
        "drought_no_10x_in_lookback": drought,
        "variance_compression_shelf": compression,
        "repeated_ceiling_rejection": ceiling_touches,
        "ascending_floor_accumulation": ascending_pressure,
        "cold_streak_ten_sub_2x": cold_streak,
    }

    results = [
        signal_lift(
            rounds,
            signal,
            name,
            lookback=lookback,
            horizon=horizon,
            permutations=permutations,
        )
        for name, signal in signals.items()
    ]

    actionable = [r for r in results if r.get("actionable")]
    return {
        "lookback": lookback,
        "horizon": horizon,
        "permutations": permutations,
        "signals_tested": len(results),
        "results": results,
        "actionable_signals": [r["signal"] for r in actionable],
        "hypothesis_supported": bool(actionable),
    }
