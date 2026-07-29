"""Distribution-free statistics implemented on the standard library.

The research suite has to be runnable in CI, on a laptop, and inside an audit
without the optional GPU/scientific stack from `requirements.txt`. So every
statistic and p-value here is computed from `math` and `random` alone.

All functions are pure and take plain sequences of floats.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "autocorrelation",
    "bartlett_bound",
    "bootstrap_ci",
    "chi_square_sf",
    "gamma_q",
    "ks_uniform",
    "median",
    "normal_sf",
    "permutation_test",
    "runs_test",
    "two_sided_normal_p",
    "wilson_interval",
]

_CONVERGED = 1e-14
_TINY = 1e-300
_MAX_ITER = 1000


# ---------------------------------------------------------------------------
# incomplete gamma -> chi-square tail
# ---------------------------------------------------------------------------

def _gamma_p_series(a: float, x: float) -> float:
    """Lower regularised incomplete gamma P(a, x) by series expansion."""
    total = 1.0 / a
    term = total
    ap = a
    for _ in range(_MAX_ITER):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * _CONVERGED:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_q_continued_fraction(a: float, x: float) -> float:
    """Upper regularised incomplete gamma Q(a, x) by modified Lentz."""
    b = x + 1.0 - a
    c = 1.0 / _TINY
    d = 1.0 / b if abs(b) > _TINY else 1.0 / _TINY
    h = d
    for i in range(1, _MAX_ITER):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _TINY:
            d = _TINY
        c = b + an / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _CONVERGED:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gamma_q(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a, x), clamped to [0, 1]."""
    if a <= 0.0:
        raise ValueError("gamma_q requires a > 0")
    if x < 0.0:
        raise ValueError("gamma_q requires x >= 0")
    if x == 0.0:
        return 1.0
    if x < a + 1.0:
        value = 1.0 - _gamma_p_series(a, x)
    else:
        value = _gamma_q_continued_fraction(a, x)
    return max(0.0, min(1.0, value))


def chi_square_sf(statistic: float, degrees_of_freedom: int) -> float:
    """Upper tail probability of a chi-square statistic."""
    if degrees_of_freedom < 1:
        return 1.0
    if statistic <= 0.0:
        return 1.0
    return gamma_q(degrees_of_freedom / 2.0, statistic / 2.0)


# ---------------------------------------------------------------------------
# normal tail
# ---------------------------------------------------------------------------

def normal_sf(z: float) -> float:
    """One-sided standard normal survival function."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def two_sided_normal_p(z: float) -> float:
    """Two-sided p-value for a standard normal z-score."""
    return min(1.0, 2.0 * normal_sf(abs(z)))


# ---------------------------------------------------------------------------
# Kolmogorov-Smirnov against Uniform(0, 1)
# ---------------------------------------------------------------------------

def _kolmogorov_sf(lam: float) -> float:
    """Asymptotic Kolmogorov distribution tail Q(lambda)."""
    if lam <= 0.0:
        return 1.0
    total = 0.0
    for k in range(1, 101):
        term = math.exp(-2.0 * k * k * lam * lam)
        total += ((-1.0) ** (k - 1)) * term
        if term < 1e-18:
            break
    return max(0.0, min(1.0, 2.0 * total))


def ks_uniform(sample: Sequence[float]) -> Dict[str, float]:
    """One-sample KS test of `sample` against Uniform(0, 1).

    Returns the statistic D and an asymptotic p-value with the Stephens
    small-sample correction. A small p-value means the sample is *not* uniform.
    """
    values = [float(v) for v in sample]
    count = len(values)
    if count < 5:
        return {"n": float(count), "statistic": 0.0, "p_value": 1.0}

    values.sort()
    statistic = 0.0
    for index, value in enumerate(values):
        statistic = max(
            statistic,
            (index + 1) / count - value,
            value - index / count,
        )

    root = math.sqrt(count)
    lam = (root + 0.12 + 0.11 / root) * statistic
    return {
        "n": float(count),
        "statistic": round(statistic, 6),
        "p_value": round(_kolmogorov_sf(lam), 6),
    }


# ---------------------------------------------------------------------------
# proportions
# ---------------------------------------------------------------------------

def wilson_interval(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval — stable for the small tail counts we care about."""
    if trials <= 0:
        return (0.0, 0.0)
    proportion = successes / trials
    denominator = 1.0 + (z * z) / trials
    centre = (proportion + (z * z) / (2.0 * trials)) / denominator
    spread = z * math.sqrt(
        proportion * (1.0 - proportion) / trials + (z * z) / (4.0 * trials * trials)
    ) / denominator
    return (max(0.0, centre - spread), min(1.0, centre + spread))


# ---------------------------------------------------------------------------
# serial dependence
# ---------------------------------------------------------------------------

def median(values: Sequence[float]) -> float:
    ordered = sorted(float(v) for v in values)
    count = len(ordered)
    if count == 0:
        return 0.0
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def autocorrelation(values: Sequence[float], max_lag: int = 10) -> Dict[int, float]:
    """Sample autocorrelation for lags 1..max_lag."""
    series = [float(v) for v in values]
    count = len(series)
    if count < 3:
        return {}

    mean = sum(series) / count
    variance = sum((v - mean) ** 2 for v in series)
    if variance <= 0.0:
        return {lag: 0.0 for lag in range(1, max_lag + 1)}

    result: Dict[int, float] = {}
    for lag in range(1, min(max_lag, count - 2) + 1):
        covariance = sum(
            (series[i] - mean) * (series[i + lag] - mean) for i in range(count - lag)
        )
        result[lag] = round(covariance / variance, 6)
    return result


def bartlett_bound(sample_size: int, z: float = 1.96) -> float:
    """Two-sided white-noise confidence bound for an autocorrelation."""
    if sample_size <= 0:
        return 0.0
    return z / math.sqrt(sample_size)


def runs_test(values: Sequence[float], threshold: Optional[float] = None) -> Dict[str, float]:
    """Wald-Wolfowitz runs test for clustering above/below a threshold.

    Exact ties with the threshold are dropped, which is the standard treatment
    and matters here because multipliers are rounded to two decimals.
    """
    series = [float(v) for v in values]
    cut = median(series) if threshold is None else float(threshold)
    signs = [v > cut for v in series if v != cut]

    above = sum(1 for s in signs if s)
    below = len(signs) - above
    total = above + below
    if above < 2 or below < 2:
        return {
            "runs": 0.0,
            "expected_runs": 0.0,
            "z_score": 0.0,
            "p_value": 1.0,
            "threshold": cut,
            "n": float(total),
        }

    runs = 1 + sum(1 for i in range(1, total) if signs[i] != signs[i - 1])
    product = 2.0 * above * below
    expected = product / total + 1.0
    variance = (product * (product - total)) / (total * total * (total - 1.0))
    if variance <= 0.0:
        return {
            "runs": float(runs),
            "expected_runs": round(expected, 4),
            "z_score": 0.0,
            "p_value": 1.0,
            "threshold": cut,
            "n": float(total),
        }

    z_score = (runs - expected) / math.sqrt(variance)
    return {
        "runs": float(runs),
        "expected_runs": round(expected, 4),
        "z_score": round(z_score, 4),
        "p_value": round(two_sided_normal_p(z_score), 6),
        "threshold": cut,
        "n": float(total),
    }


# ---------------------------------------------------------------------------
# resampling
# ---------------------------------------------------------------------------

def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float],
    iterations: int = 2000,
    alpha: float = 0.05,
    seed: int = 17,
) -> Tuple[float, float]:
    """Percentile bootstrap confidence interval. Deterministic for a given seed."""
    series = [float(v) for v in values]
    count = len(series)
    if count == 0 or iterations < 10:
        return (0.0, 0.0)

    rng = random.Random(seed)
    estimates: List[float] = []
    for _ in range(iterations):
        resample = [series[rng.randrange(count)] for _ in range(count)]
        estimates.append(float(statistic(resample)))

    estimates.sort()
    low_index = max(0, int((alpha / 2.0) * iterations))
    high_index = min(iterations - 1, int((1.0 - alpha / 2.0) * iterations))
    return (estimates[low_index], estimates[high_index])


def _rate_gap(flags: Sequence[bool], outcomes: Sequence[float]) -> float:
    """Mean outcome when flagged minus mean outcome when not flagged."""
    flagged = [o for flag, o in zip(flags, outcomes) if flag]
    unflagged = [o for flag, o in zip(flags, outcomes) if not flag]
    if not flagged or not unflagged:
        return 0.0
    return sum(flagged) / len(flagged) - sum(unflagged) / len(unflagged)


def permutation_test(
    flags: Sequence[bool],
    outcomes: Sequence[float],
    iterations: int = 2000,
    seed: int = 17,
) -> Dict[str, float]:
    """Permutation test that a signal separates outcomes better than chance.

    The pairing between signal and outcome is shuffled, which destroys any
    real timing relationship while preserving both marginal distributions.
    This is the check that stops a strategy being credited for having simply
    fired more often during a lucky stretch.
    """
    flag_list = [bool(f) for f in flags]
    outcome_list = [float(o) for o in outcomes]
    if len(flag_list) != len(outcome_list):
        raise ValueError("flags and outcomes must be the same length")

    observed = _rate_gap(flag_list, outcome_list)
    if not flag_list or observed == 0.0:
        return {"observed_gap": 0.0, "p_value": 1.0, "iterations": float(iterations)}

    rng = random.Random(seed)
    shuffled = list(flag_list)
    at_least_as_extreme = 0
    for _ in range(iterations):
        rng.shuffle(shuffled)
        if abs(_rate_gap(shuffled, outcome_list)) >= abs(observed):
            at_least_as_extreme += 1

    return {
        "observed_gap": round(observed, 6),
        "p_value": round((at_least_as_extreme + 1) / (iterations + 1), 6),
        "iterations": float(iterations),
    }
