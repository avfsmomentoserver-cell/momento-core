"""Full research report — one verdict from one tape.

`run_report` is the entry point for CI, the API and the audit trail. It loads a
tape, fits the house-edge law, runs every conformance and independence test,
backtests every registered strategy, and returns a single structured verdict.

The verdict has three possible values:

* `conforming_no_edge` — the tape matches an independent house-edge draw and no
  signal beats its base rate. Betting guidance is not a viable product; the
  defensible products are verification, compliance and harm reduction.
* `anomaly_detected` — the tape deviates from the fair law, or a signal
  survives every gate. This is an RNG or operator defect and should be handled
  as a security disclosure, not shipped as a subscription feature.
* `inconclusive` — not enough data, or the tape failed validation.

The asymmetry is deliberate. Declaring "no edge" requires only that the tests
fail to reject, while declaring an anomaly requires deviation on an independent
axis, because with this many tests a single low p-value is expected by chance.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import distribution, independence, loader, stats, strategies

logger = logging.getLogger("research.report")

__all__ = [
    "VERDICT_ANOMALY",
    "VERDICT_CONFORMING",
    "VERDICT_INCONCLUSIVE",
    "format_text",
    "run_report",
]

VERDICT_CONFORMING = "conforming_no_edge"
VERDICT_ANOMALY = "anomaly_detected"
VERDICT_INCONCLUSIVE = "inconclusive"

#: Below this, no test in this module is trustworthy.
MIN_ROUNDS = 500


def _conformance(multipliers: Sequence[float]) -> Dict[str, Any]:
    """Fit the fair law and test the tape against it on four axes."""
    edge = distribution.estimate_house_edge(multipliers)
    p = edge["p_estimate"]
    if p is None or p <= 0.0:
        return {"house_edge": edge, "note": "could not estimate p"}

    transform = distribution.probability_integral_transform(multipliers, p)

    return {
        "house_edge": edge,
        "survival_table": distribution.survival_table(multipliers, p),
        "band_goodness_of_fit": distribution.band_goodness_of_fit(multipliers, p),
        "uniformity_ks": stats.ks_uniform(transform),
        "tail_conformance": distribution.tail_conformance(multipliers),
    }


def _collect_deviations(conformance: Dict[str, Any], serial: Dict[str, Any]) -> List[str]:
    """Name every axis on which the tape departs from a fair independent draw."""
    deviations: List[str] = []

    gof = conformance.get("band_goodness_of_fit") or {}
    if gof.get("p_value") is not None and gof["p_value"] < 0.01:
        deviations.append(
            f"band distribution does not fit the fair law (chi-square p={gof['p_value']})"
        )

    ks = conformance.get("uniformity_ks") or {}
    if ks.get("p_value") is not None and ks["p_value"] < 0.01:
        deviations.append(
            f"probability integral transform is not uniform (KS p={ks['p_value']})"
        )

    tail = conformance.get("tail_conformance") or {}
    if tail.get("p_value") is not None and tail["p_value"] < 0.01:
        deviations.append(
            f"tail index {tail.get('tail_index')} differs from the theoretical 1.0"
        )

    if serial.get("serially_dependent"):
        deviations.append(
            f"rounds are serially dependent (Ljung-Box p={serial.get('ljung_box_p_value')})"
        )

    inconsistent = [
        row["threshold"]
        for row in (conformance.get("survival_table") or [])
        if not row["consistent"]
    ]
    if inconsistent:
        deviations.append(f"survival rate deviates at thresholds {inconsistent}")

    return deviations


def run_report(
    rounds: Optional[Sequence[Dict[str, Any]]] = None,
    root: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the full suite and return a structured verdict.

    Args:
        rounds: Pre-loaded rounds. When omitted, the clean root CSV is loaded.
        root: Repository root override, used by tests and the API.
        config: Passed through to the strategy backtests.
    """
    settings = dict(config or {})

    if rounds is None:
        load = loader.load_clean_tape(root=root)
        source = load.summary()
        rounds = load.rounds
        if not load.is_clean:
            return {
                "verdict": VERDICT_INCONCLUSIVE,
                "reason": "tape failed validation against the semantic layer",
                "source": source,
            }
    else:
        rounds = list(rounds)
        source = {"rounds": len(rounds), "source_files": ["supplied"]}

    if len(rounds) < MIN_ROUNDS:
        return {
            "verdict": VERDICT_INCONCLUSIVE,
            "reason": f"need at least {MIN_ROUNDS} rounds, got {len(rounds)}",
            "source": source,
        }

    multipliers = [float(r["multiplier"]) for r in rounds]

    conformance = _conformance(multipliers)
    serial = independence.serial_structure(multipliers)
    gaps = independence.gap_independence(multipliers)
    strategy_results = strategies.run_all(rounds, settings)

    deviations = _collect_deviations(conformance, serial)
    if gaps.get("drought_predicts_next_gap"):
        deviations.append("drought length predicts the next gap between moonshots")

    edge_claims = list(strategy_results["actionable_strategies"])

    # An anomaly needs corroboration: either a distributional deviation plus a
    # surviving signal, or two independent distributional deviations. A lone
    # low p-value across this many tests is expected under the null.
    if (deviations and edge_claims) or len(deviations) >= 2:
        verdict = VERDICT_ANOMALY
        reason = "tape deviates from an independent house-edge draw on multiple axes"
    elif deviations or edge_claims:
        verdict = VERDICT_INCONCLUSIVE
        reason = (
            "a single test flagged, which is expected by chance across this many "
            "tests; re-run on an independent tape before acting"
        )
    else:
        verdict = VERDICT_CONFORMING
        reason = (
            "tape is consistent with independent draws from a fixed house-edge "
            "distribution; no signal beat its base rate"
        )

    house_edge = (conformance.get("house_edge") or {}).get("house_edge")

    return {
        "verdict": verdict,
        "reason": reason,
        "source": source,
        "house_edge": house_edge,
        "deviations": deviations,
        "edge_claims": edge_claims,
        "conformance": conformance,
        "serial_structure": serial,
        "gap_independence": gaps,
        "strategies": strategy_results,
        "interpretation": _interpretation(verdict, house_edge),
    }


def _interpretation(verdict: str, house_edge: Optional[float]) -> str:
    if verdict == VERDICT_CONFORMING:
        edge_text = f"{house_edge:.2%}" if house_edge is not None else "the measured rate"
        return (
            "Every round is an independent draw, so no history-based signal can "
            f"shift the next outcome and every cashout target returns the same "
            f"expected value net of {edge_text}. Selling betting guidance on this "
            "tape would be selling a signal that provably does not exist. "
            "Verification, compliance and harm-reduction tooling are the "
            "defensible products."
        )
    if verdict == VERDICT_ANOMALY:
        return (
            "The tape deviates from a fair independent draw. Treat this as a "
            "potential RNG or operator defect: reproduce it on an independent "
            "sample and follow responsible disclosure. Do not ship it as a "
            "consumer betting feature."
        )
    return (
        "Not enough evidence either way. Collect more rounds, or investigate the "
        "single flagged test on an independent tape before drawing conclusions."
    )


def format_text(report: Dict[str, Any]) -> str:
    """Render a report as plain text for CI logs and audit artifacts."""
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("MOMENTO RESEARCH SUITE — EDGE FALSIFICATION REPORT")
    lines.append("=" * 72)

    source = report.get("source", {})
    lines.append(f"Source      : {', '.join(source.get('source_files', []))}")
    lines.append(f"Rounds      : {source.get('rounds')}")
    lines.append(f"Verdict     : {report.get('verdict')}")
    lines.append(f"Reason      : {report.get('reason')}")

    edge = report.get("house_edge")
    if edge is not None:
        lines.append(f"House edge  : {edge:.4%}")

    conformance = report.get("conformance", {})
    table = conformance.get("survival_table") or []
    if table:
        lines.append("")
        lines.append("Survival vs theoretical p/x:")
        lines.append(f"  {'>=x':>8} {'observed':>10} {'expected':>10} {'z':>8}  ok")
        for row in table:
            lines.append(
                f"  {row['threshold']:>8} {row['observed_rate']:>10.5f} "
                f"{row['expected_rate']:>10.5f} {row['z_score']:>8.2f}  "
                f"{'yes' if row['consistent'] else 'NO'}"
            )

    for result in report.get("strategies", {}).get("results", []):
        if result.get("strategy") == "cashout_target":
            lines.append("")
            lines.append("Return per unit staked by cashout target:")
            for row in (result.get("detail") or {}).get("targets", []):
                lines.append(
                    f"  {row['target']:>8}x  {row['return_per_unit']:>8.4f}  "
                    f"(hits {row['hits']})"
                )
            lines.append(f"  spread across targets: {result.get('return_spread')}")

    deviations = report.get("deviations") or []
    lines.append("")
    lines.append(f"Deviations found: {len(deviations)}")
    for item in deviations:
        lines.append(f"  - {item}")

    claims = report.get("edge_claims") or []
    lines.append(f"Strategies claiming an edge: {len(claims)}")
    for item in claims:
        lines.append(f"  - {item}")

    lines.append("")
    lines.append("Interpretation:")
    lines.append(f"  {report.get('interpretation')}")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    """CLI entry point: `python -m research.report`."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s :: %(message)s")
    report = run_report()
    print(format_text(report))

    artifact = loader.repo_root() / "research-report.json"
    artifact.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("wrote %s", artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
