"""Target construction.

The primary target is *moonshot within horizon*: for decision index ``i``, did
any of rounds ``i+1 .. i+horizon`` reach ``threshold``x?

Two details decide whether the whole suite is honest:

* The label reads strictly *forward* of the decision index. Round ``i`` itself
  is known at decision time and is never part of its own label.
* The final ``horizon`` rounds have an incomplete future, so their label is
  ``None`` and they are excluded from scoring. Treating them as negatives is the
  standard way to manufacture a flattering hit rate.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

DEFAULT_HORIZON = 10
DEFAULT_THRESHOLD = 20.0
LOW_THRESHOLD = 2.0


def horizon_labels(
    values: Sequence[float],
    horizon: int = DEFAULT_HORIZON,
    threshold: float = DEFAULT_THRESHOLD,
) -> List[Optional[int]]:
    """Return ``1``/``0``/``None`` per index in O(n).

    ``None`` marks an index whose horizon runs past the end of the tape.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    n = len(values)
    # next_hit[i] = smallest j >= i where values[j] >= threshold, else inf.
    next_hit: List[float] = [math.inf] * (n + 1)
    for i in range(n - 1, -1, -1):
        next_hit[i] = i if float(values[i]) >= threshold else next_hit[i + 1]

    labels: List[Optional[int]] = []
    for i in range(n):
        window_end = i + horizon
        if window_end >= n:
            labels.append(None)
            continue
        labels.append(1 if next_hit[i + 1] <= window_end else 0)
    return labels


def low_streaks(
    values: Sequence[float],
    low_threshold: float = LOW_THRESHOLD,
) -> List[int]:
    """Consecutive sub-``low_threshold`` rounds ending at each index, inclusive.

    Causal by construction: index ``i`` depends only on ``values[:i+1]``. This is
    the "dry phase" of the linguistics vocabulary expressed as a number.
    """
    streaks: List[int] = []
    run = 0
    for value in values:
        run = run + 1 if float(value) < low_threshold else 0
        streaks.append(run)
    return streaks


def base_rate(labels: Sequence[Optional[int]]) -> Optional[float]:
    """Mean of the scorable labels, or ``None`` when none are scorable."""
    scorable = [int(v) for v in labels if v is not None]
    if not scorable:
        return None
    return sum(scorable) / len(scorable)
