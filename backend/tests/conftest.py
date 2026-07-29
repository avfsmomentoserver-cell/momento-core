"""Shared fixtures for the research suite.

The clean tape is loaded once per session because it is ~15k rows and several
tests are resampling-heavy.

The two synthetic generators here are the controls that make the suite
credible. A test battery that only ever reports "no edge" is indistinguishable
from one that is simply broken, so `synthetic_fair_tape` must be certified as
fair and `synthetic_dependent_tape` must be flagged.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List

import pytest

from research import loader


@pytest.fixture(scope="session")
def clean_tape() -> loader.LoadResult:
    """The validated full tape from the repository root."""
    try:
        return loader.load_clean_tape()
    except FileNotFoundError as exc:
        pytest.skip(f"clean export not available: {exc}")


@pytest.fixture(scope="session")
def rounds(clean_tape: loader.LoadResult) -> List[Dict[str, Any]]:
    return clean_tape.rounds


@pytest.fixture(scope="session")
def multipliers(clean_tape: loader.LoadResult) -> List[float]:
    return clean_tape.multipliers


def synthetic_fair_tape(
    count: int = 15000,
    house_edge: float = 0.01,
    seed: int = 4242,
) -> List[Dict[str, Any]]:
    """Generate a provably-fair crash tape as a positive control.

    Inverting `P(X >= x) = p / x` gives `X = p / U` for `U` uniform, clamped at
    1.0 so the instant-bust atom appears with probability `1 - p`.
    """
    rng = random.Random(seed)
    retained = 1.0 - house_edge
    tape: List[Dict[str, Any]] = []
    for index in range(count):
        draw = rng.random()
        multiplier = max(1.0, retained / draw) if draw > 0 else 1.0
        tape.append({"id": index, "multiplier": round(multiplier, 2), "created_at": None})
    return tape


def synthetic_dependent_tape(count: int = 15000, seed: int = 99) -> List[Dict[str, Any]]:
    """Generate a deliberately *unfair* tape as a negative control.

    Here a drought genuinely does build pressure: after 15 rounds without a 10x
    the next round is forced high. This is the tape the suite must flag, proving
    the tests have the power to detect a real edge.
    """
    rng = random.Random(seed)
    tape: List[Dict[str, Any]] = []
    since = 0
    for index in range(count):
        if since >= 15:
            multiplier = 25.0 + rng.random() * 50.0
            since = 0
        else:
            multiplier = max(1.0, 0.99 / max(rng.random(), 1e-9))
            since = 0 if multiplier >= 10.0 else since + 1
        tape.append({"id": index, "multiplier": round(multiplier, 2), "created_at": None})
    return tape
