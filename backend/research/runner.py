"""Run the suite and emit a JSON artifact.

Usage::

    python -m research.runner ../clean_data.csv --json research-report.json
    python -m research.runner ../eagle-eye-export-*.csv --permutations 200

Run from ``backend/`` (or with ``backend/`` on ``PYTHONPATH``) so ``momento`` and
``features`` resolve. No database and no network are touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Sequence, Type

from .labels import DEFAULT_HORIZON, DEFAULT_THRESHOLD, horizon_labels
from .loader import load_exports, multipliers
from .metrics import paper_pnl, score_forecasts
from .significance import permutation_test
from .splitter import Fold, assert_causal, walk_forward_folds
from .strategies import STRATEGY_REGISTRY, DryStreakStrategy, ResearchStrategy

DEFAULT_CASHOUTS = (2.0, 5.0, 20.0)


def _collect(
    strategy_cls: Type[ResearchStrategy],
    values: Sequence[float],
    folds: Sequence[Fold],
    *,
    horizon: int,
    threshold: float,
) -> Dict[str, Any]:
    """Fit per fold and gather out-of-sample forecasts.

    The reference rate comes from each fold's *training* slice, never from its
    test labels, so the baseline gets no look at the answer.
    """
    labels = horizon_labels(values, horizon, threshold)

    probs: List[float] = []
    truths: List[int] = []
    outcomes: List[float] = []
    reference_numerator = 0.0
    per_fold: List[Dict[str, Any]] = []

    for fold in folds:
        strategy = strategy_cls(horizon=horizon, threshold=threshold)
        strategy.fit_on(list(values[fold.train_start : fold.train_end]))

        train_labels = [
            y for y in labels[fold.train_start : fold.train_end] if y is not None
        ]
        train_rate = (sum(train_labels) / len(train_labels)) if train_labels else 0.0

        # Forecast over the full prefix so causal features see real history at the
        # fold boundary, then keep only the test-range predictions.
        prefix_probs = strategy.predict_series(list(values[: fold.test_end]))

        fold_probs: List[float] = []
        fold_truths: List[int] = []
        for i in range(fold.test_start, fold.test_end):
            label = labels[i]
            if label is None:
                continue
            fold_probs.append(prefix_probs[i])
            fold_truths.append(int(label))
            window = values[i + 1 : i + 1 + horizon]
            outcomes.append(max(window) if window else 0.0)

        if not fold_truths:
            continue

        probs.extend(fold_probs)
        truths.extend(fold_truths)
        reference_numerator += train_rate * len(fold_truths)

        entry = fold.as_dict()
        entry["train_base_rate"] = train_rate
        entry["score"] = score_forecasts(
            fold_probs, fold_truths, reference_rate=train_rate, n_boot=0
        ).as_dict()
        if isinstance(strategy, DryStreakStrategy):
            entry["learned_table"] = strategy.learned_table()
        per_fold.append(entry)

    return {
        "probs": probs,
        "labels": truths,
        "outcomes": outcomes,
        "reference_rate": (reference_numerator / len(truths)) if truths else None,
        "folds": per_fold,
    }


def run_strategy(
    strategy_cls: Type[ResearchStrategy],
    values: Sequence[float],
    *,
    horizon: int = DEFAULT_HORIZON,
    threshold: float = DEFAULT_THRESHOLD,
    n_folds: int = 5,
    min_train: int = 500,
    decision_threshold: float = 0.5,
    n_boot: int = 500,
    permutations: int = 0,
    cashouts: Sequence[float] = DEFAULT_CASHOUTS,
) -> Dict[str, Any]:
    """Walk-forward evaluation of one strategy, with an optional permutation test."""
    folds = walk_forward_folds(
        len(values), horizon=horizon, n_folds=n_folds, min_train=min_train
    )
    assert_causal(folds)
    if not folds:
        return {
            "strategy": strategy_cls.name,
            "insufficient_data": True,
            "n_rounds": len(values),
            "min_train": min_train,
            "horizon": horizon,
        }

    collected = _collect(
        strategy_cls, values, folds, horizon=horizon, threshold=threshold
    )
    if not collected["labels"]:
        return {
            "strategy": strategy_cls.name,
            "insufficient_data": True,
            "reason": "no scorable decision points in any test range",
        }

    score = score_forecasts(
        collected["probs"],
        collected["labels"],
        reference_rate=collected["reference_rate"],
        decision_threshold=decision_threshold,
        n_boot=n_boot,
    )

    result: Dict[str, Any] = {
        "strategy": strategy_cls.name,
        "description": strategy_cls.description,
        "horizon": horizon,
        "threshold": threshold,
        "n_folds": len(folds),
        "pooled": score.as_dict(),
        "reference_rate_from_training": collected["reference_rate"],
        "per_fold": collected["folds"],
        "paper_pnl": [
            paper_pnl(
                collected["probs"],
                collected["outcomes"],
                cashout=cashout,
                decision_threshold=decision_threshold,
            )
            for cashout in cashouts
        ],
        "pnl_note": (
            "EV per unit staked is c-1 at every cashout target for a fair crash "
            "game, so a flat pnl column is the expected result."
        ),
    }

    if permutations > 0:

        def statistic(series: Sequence[float]) -> float:
            shuffled_folds = walk_forward_folds(
                len(series), horizon=horizon, n_folds=n_folds, min_train=min_train
            )
            gathered = _collect(
                strategy_cls,
                series,
                shuffled_folds,
                horizon=horizon,
                threshold=threshold,
            )
            if not gathered["labels"]:
                return float("nan")
            return score_forecasts(
                gathered["probs"],
                gathered["labels"],
                reference_rate=gathered["reference_rate"],
                n_boot=0,
            ).skill

        result["permutation_test"] = permutation_test(
            values, statistic, n_permutations=permutations
        ).as_dict()

    return result


def run_suite(
    paths: Sequence[str],
    *,
    horizon: int = DEFAULT_HORIZON,
    threshold: float = DEFAULT_THRESHOLD,
    n_folds: int = 5,
    min_train: int = 500,
    decision_threshold: float = 0.5,
    permutations: int = 0,
    n_boot: int = 500,
    strategies: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    rounds, report = load_exports(paths)
    values = multipliers(rounds)
    labels = horizon_labels(values, horizon, threshold)
    scorable = [y for y in labels if y is not None]

    names = list(strategies) if strategies else list(STRATEGY_REGISTRY)
    unknown = [n for n in names if n not in STRATEGY_REGISTRY]
    if unknown:
        raise SystemExit(
            f"unknown strategy {unknown}; available: {sorted(STRATEGY_REGISTRY)}"
        )

    return {
        "meta": {
            "suite": "momento-research",
            "purpose": (
                "Falsification harness. A null result is the expected and correct "
                "outcome and must not be tuned away."
            ),
            "target": f"moonshot >= {threshold}x within the next {horizon} rounds",
        },
        "load": report.as_dict(),
        "target_summary": {
            "horizon": horizon,
            "threshold": threshold,
            "scorable_decision_points": len(scorable),
            "excluded_incomplete_horizon": len(labels) - len(scorable),
            "base_rate": (sum(scorable) / len(scorable)) if scorable else None,
        },
        "strategies": [
            run_strategy(
                STRATEGY_REGISTRY[name],
                values,
                horizon=horizon,
                threshold=threshold,
                n_folds=n_folds,
                min_train=min_train,
                decision_threshold=decision_threshold,
                n_boot=n_boot,
                permutations=permutations,
            )
            for name in names
        ],
    }


def _fmt(value: Any, digits: int = 4) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
        return f"{value:.{digits}f}"
    return str(value)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Momento research suite")
    parser.add_argument("csv", nargs="+", help="one or more eagle-eye exports")
    parser.add_argument("--json", default="research-report.json")
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-train", type=int, default=500)
    parser.add_argument("--decision-threshold", type=float, default=0.5)
    parser.add_argument("--permutations", type=int, default=0)
    parser.add_argument("--bootstrap", type=int, default=500)
    parser.add_argument("--strategy", action="append", dest="strategies")
    args = parser.parse_args(argv)

    report = run_suite(
        args.csv,
        horizon=args.horizon,
        threshold=args.threshold,
        n_folds=args.folds,
        min_train=args.min_train,
        decision_threshold=args.decision_threshold,
        permutations=args.permutations,
        n_boot=args.bootstrap,
        strategies=args.strategies,
    )

    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)

    load = report["load"]
    target = report["target_summary"]
    print("=== momento research suite ===")
    print(
        f"rounds: {load['rows_out']} "
        f"(read {load['rows_read']}, dupe ids {load['duplicate_ids']})"
    )
    print(f"span: {load['span'][0]} -> {load['span'][1]}")
    print(f"id order == time order: {load['id_order_equals_time_order']}")
    print(f"target: {report['meta']['target']}")
    print(
        f"scorable points: {target['scorable_decision_points']} "
        f"(base rate {_fmt(target['base_rate'])})"
    )

    for entry in report["strategies"]:
        print(f"\n-- {entry['strategy']}")
        if entry.get("insufficient_data"):
            print(f"   insufficient data: {entry.get('reason', 'not enough rounds')}")
            continue
        pooled = entry["pooled"]
        ci = pooled.get("skill_ci", {}).get("ci") or [None, None]
        print(
            f"   brier {_fmt(pooled['brier'])} "
            f"vs reference {_fmt(pooled['reference_brier'])}"
        )
        print(
            f"   skill {_fmt(pooled['skill_score'])} "
            f"(95% CI {_fmt(ci[0])} .. {_fmt(ci[1])})"
        )
        hits = pooled.get("hits", {})
        print(
            f"   signals {hits.get('signals_fired')} "
            f"precision {_fmt(hits.get('precision'))} "
            f"recall {_fmt(hits.get('recall'))}"
        )
        perm = entry.get("permutation_test")
        if perm:
            print(
                f"   permutation: observed {_fmt(perm['observed'])} "
                f"vs null mean {_fmt(perm['null_mean'])}, "
                f"percentile {_fmt(perm['percentile_vs_null'], 1)}, "
                f"p={_fmt(perm['p_value_one_sided'])}"
            )
            print(f"   -> {perm['interpretation']}")

    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
