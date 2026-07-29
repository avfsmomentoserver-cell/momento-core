"""Research suite API — edge falsification and tape verification.

These endpoints expose the research suite to the operator console so a verdict
can be produced from the UI and archived, rather than living only in CI logs.

The suite is intentionally read-only and stateless: it reads a tape, computes,
and returns. It never writes rounds and never influences the live forecast
engine, so a report can be re-run at any time and produce the same answer from
the same data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ... import db
from ..deps import source_param

logger = logging.getLogger("momento.api.research")

router = APIRouter(tags=["research"])

#: Reports on the full tape are CPU-bound; cap what a single request can pull.
MAX_LIVE_ROUNDS = 50000


def _load_research():
    """Import the research package lazily so the API boots without it."""
    try:
        from research import loader, report
    except ImportError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=503,
            detail=f"research suite unavailable: {exc}",
        ) from exc
    return loader, report


def _live_rounds(source: str, limit: int) -> List[Dict[str, Any]]:
    """Pull rounds from the live tape, oldest first."""
    rows = db.query(
        """SELECT id, multiplier, created_at
           FROM rounds
           WHERE source = ?
           ORDER BY id ASC
           LIMIT ?""",
        (source, min(limit, MAX_LIVE_ROUNDS)),
    )
    return [
        {
            "id": row["id"],
            "multiplier": float(row["multiplier"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.get("/research/tape")
async def inspect_tape() -> Dict[str, Any]:
    """Validate the root export against the semantic layer.

    Returns row counts, duplicate counts and any field that disagrees with
    `momento.linguistics`. A clean result is the precondition for trusting any
    other research output.
    """
    loader, _ = _load_research()
    try:
        result = loader.load_clean_tape()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except loader.TruncatedExportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.summary()


@router.get("/research/report")
async def research_report(
    tape: str = Query(
        "csv",
        pattern="^(csv|live)$",
        description="'csv' reads the validated root export, 'live' reads the database.",
    ),
    source: str = Query("aviator", description="Live tape source, ignored when tape=csv."),
    limit: int = Query(20000, ge=500, le=MAX_LIVE_ROUNDS),
    horizon: int = Query(10, ge=1, le=100),
    lookback: int = Query(40, ge=10, le=500),
    permutations: int = Query(400, ge=100, le=2000),
) -> Dict[str, Any]:
    """Run the full falsification suite and return a single verdict.

    Verdicts:

    * `conforming_no_edge` — the tape is consistent with independent draws from
      a fixed house-edge distribution and no signal beat its base rate.
    * `anomaly_detected` — the tape deviates on multiple axes. Treat as a
      potential RNG defect and follow responsible disclosure.
    * `inconclusive` — insufficient or unvalidated data.
    """
    _, report_module = _load_research()
    config = {"horizon": horizon, "lookback": lookback, "permutations": permutations}

    if tape == "live":
        rounds = _live_rounds(source, limit)
        if len(rounds) < report_module.MIN_ROUNDS:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"live tape has {len(rounds)} rounds for source '{source}', "
                    f"need at least {report_module.MIN_ROUNDS}"
                ),
            )
        return report_module.run_report(rounds=rounds, config=config)

    try:
        return report_module.run_report(config=config)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/research/cashout-profile")
async def cashout_profile(
    tape: str = Query("csv", pattern="^(csv|live)$"),
    source: str = Query("aviator"),
    limit: int = Query(20000, ge=500, le=MAX_LIVE_ROUNDS),
) -> Dict[str, Any]:
    """Empirical return per unit staked at each fixed cashout target.

    This is the clearest single view of why exit choice cannot create an edge:
    return is `target * P(X >= target)`, which is constant when survival follows
    `p / x`. Suitable for direct rendering on the Round Testing screen.
    """
    loader, _ = _load_research()
    from research import distribution

    if tape == "live":
        multipliers = [r["multiplier"] for r in _live_rounds(source, limit)]
    else:
        try:
            multipliers = loader.load_clean_tape().multipliers
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    if len(multipliers) < 500:
        raise HTTPException(status_code=422, detail="need at least 500 rounds")

    profile = distribution.cashout_expected_values(multipliers)
    edge = distribution.estimate_house_edge(multipliers)
    return {
        "house_edge": edge,
        "profile": profile,
        "note": (
            "Return per unit staked is target * P(X >= target). Under a fair "
            "crash curve this equals the retained fraction for every target, so "
            "no cashout choice changes expected value."
        ),
    }


@router.get("/research/independence")
async def independence_check(
    tape: str = Query("csv", pattern="^(csv|live)$"),
    source: str = Query("aviator"),
    limit: int = Query(20000, ge=500, le=MAX_LIVE_ROUNDS),
    horizon: int = Query(10, ge=1, le=100),
    lookback: int = Query(40, ge=10, le=500),
    permutations: int = Query(
        400,
        ge=100,
        le=2000,
        description=(
            "Permutation iterations per signal. Each one reshuffles the full "
            "outcome vector, so high values make the request slow. 400 still "
            "resolves the 0.01 significance threshold."
        ),
    ),
) -> Dict[str, Any]:
    """Test whether accumulated pressure predicts a release.

    Powers the Bird's Eye view of the accumulation hypothesis: each signal is
    reported with its lift, Wilson intervals and permutation p-value, so a
    plausible-looking lift can be read against its own noise.
    """
    loader, _ = _load_research()
    from research import independence

    if tape == "live":
        rounds = _live_rounds(source, limit)
    else:
        try:
            rounds = loader.load_clean_tape().rounds
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    if len(rounds) < 500:
        raise HTTPException(status_code=422, detail="need at least 500 rounds")

    multipliers = [float(r["multiplier"]) for r in rounds]
    return {
        "pressure_release": independence.test_pressure_release(
            rounds, lookback=lookback, horizon=horizon, permutations=permutations
        ),
        "serial_structure": independence.serial_structure(multipliers),
        "gap_independence": independence.gap_independence(multipliers),
    }
