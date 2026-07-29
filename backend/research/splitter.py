"""Walk-forward folds with strict causality.

Expanding window: fold ``k`` trains on everything before its test range and is
evaluated only on that range. A strategy therefore never sees a round it is
scored on, and a parameter chosen on fold ``k`` cannot have been informed by
fold ``k+1``.

The warmup/normal/stress split already in ``momento.backtest`` is kept as a
secondary view so stress folds stay moonshot-heavy. It is deliberately not the
primary split, because a single fixed split cannot show whether an edge decays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

DEFAULT_FOLDS = 5
DEFAULT_MIN_TRAIN = 500


@dataclass(frozen=True)
class Fold:
    """Half-open index ranges over the chronologically sorted tape."""

    index: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int

    @property
    def train_size(self) -> int:
        return self.train_end - self.train_start

    @property
    def test_size(self) -> int:
        return self.test_end - self.test_start

    def as_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "train": [self.train_start, self.train_end],
            "test": [self.test_start, self.test_end],
            "train_size": self.train_size,
            "test_size": self.test_size,
        }


def walk_forward_folds(
    n_rounds: int,
    *,
    horizon: int,
    n_folds: int = DEFAULT_FOLDS,
    min_train: int = DEFAULT_MIN_TRAIN,
) -> List[Fold]:
    """Build expanding-window folds over the label-eligible prefix.

    Indices at or beyond ``n_rounds - horizon`` have no complete horizon, so they
    fall outside every fold.
    """
    if n_folds < 1:
        raise ValueError("n_folds must be >= 1")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    usable = n_rounds - horizon
    if usable <= min_train:
        return []

    step = (usable - min_train) // n_folds
    if step < 1:
        return []

    folds: List[Fold] = []
    for k in range(n_folds):
        test_start = min_train + k * step
        test_end = usable if k == n_folds - 1 else min_train + (k + 1) * step
        if test_end <= test_start:
            continue
        folds.append(
            Fold(
                index=k,
                train_start=0,
                train_end=test_start,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return folds


def assert_causal(folds: Sequence[Fold]) -> None:
    """Guard against a fold whose training window overlaps its test window.

    Cheap to call, and the one bug in this file that would invalidate every
    number the suite produces.
    """
    for fold in folds:
        if fold.train_end > fold.test_start:
            raise ValueError(
                f"fold {fold.index} leaks: train ends at {fold.train_end}, "
                f"test starts at {fold.test_start}"
            )
        if fold.test_end <= fold.test_start:
            raise ValueError(f"fold {fold.index} has an empty test range")


def phase_view(
    rounds: Sequence[Dict[str, Any]],
    warmup_pct: float = 0.1,
    stress_pct: float = 0.3,
) -> Dict[str, List[Dict[str, Any]]]:
    """Reuse the warmup/normal/stress split already defined in the backend.

    Falls back to an inline implementation when ``momento.backtest`` cannot be
    imported, which is what keeps this package DB-free: importing that module
    pulls in ``db`` and ``store``.
    """
    try:  # pragma: no cover - only when the DB stack is importable
        from momento.backtest import split_test_phases

        return split_test_phases(list(rounds), warmup_pct, stress_pct)
    except Exception:
        total = len(rounds)
        if not total:
            return {"warmup": [], "normal": [], "stress": []}
        warmup_end = int(total * warmup_pct)
        stress_start = int(total * (1 - stress_pct))
        return {
            "warmup": list(rounds[:warmup_end]),
            "normal": list(rounds[warmup_end:stress_start]),
            "stress": list(rounds[stress_start:]),
        }
