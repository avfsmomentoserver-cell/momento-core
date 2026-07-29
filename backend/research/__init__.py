"""Momento research suite: offline hypothesis testing against CSV exports.

CSV-first and DB-free by design. Every module runs from a file path with no
network and no SQLite tape, so a result can be reproduced from the repo alone.
Strategies implement ``features.base.BaseFeature``, so a hypothesis that survives
the significance test ports into ``backend/features/`` unchanged.

The governing rule is causality: the feature for decision index ``i`` may read
rounds ``0..i`` only, and the label reads ``i+1..i+horizon``. Nothing here is
permitted to read a round it is being scored on.
"""

from __future__ import annotations

from .labels import base_rate, horizon_labels, low_streaks
from .loader import (
    ExportInvariantError,
    LoadReport,
    load_export,
    load_exports,
    multipliers,
    validate_rounds,
)
from .metrics import (
    ForecastScore,
    brier_score,
    calibration_bins,
    hit_rate,
    max_drawdown,
    paper_pnl,
    score_forecasts,
    skill_score,
)
from .significance import PermutationResult, permutation_test
from .splitter import Fold, assert_causal, walk_forward_folds
from .strategies import (
    STRATEGY_REGISTRY,
    BaseRateStrategy,
    DryStreakStrategy,
    ResearchStrategy,
)

__all__ = [
    "STRATEGY_REGISTRY",
    "BaseRateStrategy",
    "DryStreakStrategy",
    "ExportInvariantError",
    "Fold",
    "ForecastScore",
    "LoadReport",
    "PermutationResult",
    "ResearchStrategy",
    "assert_causal",
    "base_rate",
    "brier_score",
    "calibration_bins",
    "hit_rate",
    "horizon_labels",
    "load_export",
    "load_exports",
    "low_streaks",
    "max_drawdown",
    "multipliers",
    "paper_pnl",
    "permutation_test",
    "score_forecasts",
    "skill_score",
    "validate_rounds",
    "walk_forward_folds",
]
