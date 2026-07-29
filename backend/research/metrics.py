"""Scoring.

Every metric here is computed from forecasts recorded *before* the outcome was
known, which is the honest-accuracy rule the project already states.

The distinction that matters most: **calibration is not skill**. A forecaster
that always emits the base rate is perfectly calibrated and completely useless.
So ``score_forecasts`` always reports the Brier score *and* the skill score
against the base-rate reference, and the skill score carries a bootstrap
interval. A positive point estimate whose interval spans zero is not a finding.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


def brier_score(probs: Sequence[float], labels: Sequence[int]) -> float:
    """Mean squared error of probabilistic forecasts. Lower is better."""
    if len(probs) != len(labels):
        raise ValueError("probs and labels must be the same length")
    if not probs:
        return float("nan")
    return sum((float(p) - int(y)) ** 2 for p, y in zip(probs, labels)) / len(probs)


def skill_score(model_brier: float, reference_brier: float) -> float:
    """``1 - BS_model / BS_reference``. Positive means better than reference."""
    if not math.isfinite(model_brier) or not math.isfinite(reference_brier):
        return float("nan")
    if reference_brier <= 0:
        return float("nan")
    return 1.0 - (model_brier / reference_brier)


def log_loss(probs: Sequence[float], labels: Sequence[int], eps: float = 1e-15) -> float:
    if not probs:
        return float("nan")
    total = 0.0
    for p, y in zip(probs, labels):
        clipped = min(1.0 - eps, max(eps, float(p)))
        total += -(math.log(clipped) if int(y) == 1 else math.log(1.0 - clipped))
    return total / len(probs)


def calibration_bins(
    probs: Sequence[float],
    labels: Sequence[int],
    n_bins: int = 10,
) -> List[Dict[str, Any]]:
    """Reliability table. ``mean_predicted`` should track ``observed_rate``."""
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    buckets: List[Dict[str, Any]] = [
        {
            "bin": i,
            "lo": i / n_bins,
            "hi": (i + 1) / n_bins,
            "count": 0,
            "sum_predicted": 0.0,
            "positives": 0,
        }
        for i in range(n_bins)
    ]
    for p, y in zip(probs, labels):
        value = min(1.0, max(0.0, float(p)))
        bucket = buckets[min(n_bins - 1, int(value * n_bins))]
        bucket["count"] += 1
        bucket["sum_predicted"] += value
        bucket["positives"] += int(y)

    out: List[Dict[str, Any]] = []
    for bucket in buckets:
        count = bucket["count"]
        out.append(
            {
                "bin": bucket["bin"],
                "range": [round(bucket["lo"], 4), round(bucket["hi"], 4)],
                "count": count,
                "mean_predicted": (bucket["sum_predicted"] / count) if count else None,
                "observed_rate": (bucket["positives"] / count) if count else None,
            }
        )
    return out


def hit_rate(
    probs: Sequence[float],
    labels: Sequence[int],
    decision_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Confusion counts at a decision threshold, plus precision and recall."""
    tp = fp = tn = fn = 0
    for p, y in zip(probs, labels):
        predicted = float(p) >= decision_threshold
        actual = int(y) == 1
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1
    fired = tp + fp
    positives = tp + fn
    total = tp + fp + tn + fn
    return {
        "decision_threshold": decision_threshold,
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "signals_fired": fired,
        "precision": (tp / fired) if fired else None,
        "recall": (tp / positives) if positives else None,
        "accuracy": ((tp + tn) / total) if total else None,
    }


def max_drawdown(equity: Sequence[float]) -> float:
    """Largest peak-to-trough decline of an equity curve."""
    peak = -math.inf
    worst = 0.0
    for value in equity:
        peak = max(peak, float(value))
        worst = max(worst, peak - float(value))
    return worst


def paper_pnl(
    probs: Sequence[float],
    outcomes: Sequence[float],
    *,
    cashout: float,
    decision_threshold: float = 0.5,
    stake: float = 1.0,
) -> Dict[str, Any]:
    """Flat-stake paper P&L for "bet when the forecast fires, cash out at X".

    ``outcomes[i]`` is the multiplier actually realised for the round the signal
    at ``i`` refers to. A win pays ``stake * (cashout - 1)``; a loss costs
    ``stake``.

    Read the EV algebra before reading anything into the result: for a fair crash
    game with survival ``P(M >= x) = c/x``, expected value per unit staked is
    ``x * (c/x) - 1 = c - 1`` at *every* cashout target. The cashout column is
    therefore expected to be flat, and a non-flat column is evidence of either an
    exploitable structure or a data defect, with the second far more likely.
    """
    equity = [0.0]
    wins = losses = 0
    for p, outcome in zip(probs, outcomes):
        if float(p) < decision_threshold:
            continue
        if float(outcome) >= cashout:
            equity.append(equity[-1] + stake * (cashout - 1.0))
            wins += 1
        else:
            equity.append(equity[-1] - stake)
            losses += 1
    bets = wins + losses
    return {
        "cashout": cashout,
        "stake": stake,
        "bets": bets,
        "wins": wins,
        "losses": losses,
        "net": equity[-1],
        "ev_per_unit_staked": (equity[-1] / (bets * stake)) if bets else None,
        "max_drawdown": max_drawdown(equity),
    }


def bootstrap_skill_ci(
    probs: Sequence[float],
    labels: Sequence[int],
    reference: Sequence[float],
    *,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 20260729,
) -> Dict[str, Any]:
    """Percentile bootstrap interval for the skill score.

    Resamples decision points with replacement, paired: the model forecast, the
    reference forecast and the label move together, so the interval reflects
    uncertainty in the *difference* rather than in either score alone.
    """
    n = len(labels)
    if n == 0 or n_boot < 1:
        return {"point": float("nan"), "ci": [None, None], "n_boot": 0}

    point = skill_score(brier_score(probs, labels), brier_score(reference, labels))
    rng = random.Random(seed)
    draws: List[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        resampled = [labels[i] for i in idx]
        if len(set(resampled)) < 2:
            # A single-class resample makes the Brier reference degenerate; skip
            # rather than emit a misleading value.
            continue
        value = skill_score(
            brier_score([probs[i] for i in idx], resampled),
            brier_score([reference[i] for i in idx], resampled),
        )
        if math.isfinite(value):
            draws.append(value)

    if not draws:
        return {"point": point, "ci": [None, None], "n_boot": 0}

    draws.sort()
    lo_idx = max(0, int((alpha / 2) * len(draws)) - 1)
    hi_idx = min(len(draws) - 1, int((1 - alpha / 2) * len(draws)))
    return {
        "point": point,
        "ci": [draws[lo_idx], draws[hi_idx]],
        "n_boot": len(draws),
        "alpha": alpha,
    }


@dataclass
class ForecastScore:
    """Everything needed to judge one strategy on one evaluation set."""

    n: int = 0
    base_rate: Optional[float] = None
    brier: float = float("nan")
    reference_brier: float = float("nan")
    skill: float = float("nan")
    skill_ci: Dict[str, Any] = field(default_factory=dict)
    log_loss: float = float("nan")
    calibration: List[Dict[str, Any]] = field(default_factory=list)
    hits: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "base_rate": self.base_rate,
            "brier": self.brier,
            "reference_brier": self.reference_brier,
            "skill_score": self.skill,
            "skill_ci": self.skill_ci,
            "log_loss": self.log_loss,
            "calibration": self.calibration,
            "hits": self.hits,
        }


def score_forecasts(
    probs: Sequence[float],
    labels: Sequence[int],
    *,
    reference_rate: Optional[float] = None,
    decision_threshold: float = 0.5,
    n_boot: int = 500,
    n_bins: int = 10,
) -> ForecastScore:
    """Score a set of forecasts against the constant base-rate reference."""
    n = len(labels)
    if n == 0:
        return ForecastScore()

    observed = sum(int(y) for y in labels) / n
    # The reference should be fit on training data, not on the evaluation labels,
    # or the baseline gets a free look at the answer and skill is understated.
    rate = observed if reference_rate is None else float(reference_rate)
    reference = [rate] * n

    model_brier = brier_score(probs, labels)
    ref_brier = brier_score(reference, labels)

    return ForecastScore(
        n=n,
        base_rate=observed,
        brier=model_brier,
        reference_brier=ref_brier,
        skill=skill_score(model_brier, ref_brier),
        skill_ci=bootstrap_skill_ci(probs, labels, reference, n_boot=n_boot),
        log_loss=log_loss(probs, labels),
        calibration=calibration_bins(probs, labels, n_bins),
        hits=hit_rate(probs, labels, decision_threshold),
    )
