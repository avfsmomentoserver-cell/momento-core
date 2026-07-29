"""Parse eagle-eye CSV exports into the round dicts the analysis layer consumes.

The export schema is ``ID,Timestamp,Multiplier,Color,Band,Points,Ingest Method``.
Only ``ID``, ``Timestamp`` and ``Multiplier`` carry information: ``Band`` and
``Color`` are bucketings of ``Multiplier``, and ``Points`` is a log rescaling of
it. Those three are therefore treated as *checksums* rather than features. They
are validated on load and must never be handed to a model alongside
``Multiplier``, which would triple the apparent feature count and inflate any
feature-importance reading.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from momento import linguistics as ling

# Columns that must be present for the file to be usable at all.
ESSENTIAL_COLUMNS: Tuple[str, ...] = ("ID", "Timestamp", "Multiplier")

# Validated as checksums when present, tolerated when absent so a hand-cleaned
# export with a reduced schema still loads.
CHECKSUM_COLUMNS: Tuple[str, ...] = ("Band", "Color", "Points")

# to_points rounds to 3 dp, so 0.01 absorbs the rounding without hiding a
# genuine formula mismatch.
POINTS_TOLERANCE = 0.01

_TS_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


class ExportInvariantError(ValueError):
    """Raised when an export violates a structural invariant.

    Loud by design: a silent coercion here becomes an unexplainable backtest
    result three modules downstream.
    """


@dataclass
class LoadReport:
    """Provenance for a single load, suitable for committing as an artifact."""

    sources: List[str] = field(default_factory=list)
    rows_read: int = 0
    rows_out: int = 0
    duplicate_ids: int = 0
    id_order_equals_time_order: bool = True
    span: Tuple[Optional[str], Optional[str]] = (None, None)
    band_counts: Dict[str, int] = field(default_factory=dict)
    checksum_columns_present: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sources": list(self.sources),
            "rows_read": self.rows_read,
            "rows_out": self.rows_out,
            "duplicate_ids": self.duplicate_ids,
            "id_order_equals_time_order": self.id_order_equals_time_order,
            "span": list(self.span),
            "band_counts": dict(self.band_counts),
            "checksum_columns_present": list(self.checksum_columns_present),
        }


def parse_timestamp(raw: Any) -> datetime:
    """Parse an export timestamp into a UTC-aware datetime."""
    text = str(raw).strip()
    if not text:
        raise ExportInvariantError("empty timestamp")

    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    parsed: Optional[datetime] = None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        for fmt in _TS_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        raise ExportInvariantError(f"unparseable timestamp: {text!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalise_header(fieldnames: Optional[Sequence[str]]) -> Dict[str, str]:
    """Map stripped header names to their raw form in the file."""
    if not fieldnames:
        raise ExportInvariantError("CSV has no header row")
    return {str(name).strip(): str(name) for name in fieldnames if name is not None}


def _parse_row(
    raw: Dict[str, Any],
    header: Dict[str, str],
    path: Path,
    line_no: int,
    checksums: Sequence[str],
) -> Dict[str, Any]:
    def cell(col: str) -> Any:
        return raw.get(header[col]) if col in header else None

    where = f"{path.name}:{line_no}"

    try:
        round_id = int(str(cell("ID")).strip())
    except (TypeError, ValueError):
        raise ExportInvariantError(f"{where}: non-integer ID {cell('ID')!r}") from None

    try:
        multiplier = float(str(cell("Multiplier")).strip())
    except (TypeError, ValueError):
        raise ExportInvariantError(
            f"{where}: non-numeric Multiplier {cell('Multiplier')!r}"
        ) from None

    if not math.isfinite(multiplier) or multiplier < 1.0:
        raise ExportInvariantError(
            f"{where}: Multiplier {multiplier!r} outside the valid range (>= 1.0)"
        )

    timestamp = parse_timestamp(cell("Timestamp"))
    band = ling.band_for(multiplier)

    row: Dict[str, Any] = {
        "id": round_id,
        "multiplier": multiplier,
        "ts": timestamp,
        # created_at mirrors the SQLite column name so these dicts drop straight
        # into the same call sites as db-sourced rounds.
        "created_at": timestamp.isoformat(),
        "band": band["key"],
        "band_label": band["label"],
        "points": ling.to_points(multiplier),
        "source": "csv",
    }
    for col in checksums:
        row[f"export_{col.lower()}"] = cell(col)
    if "Ingest Method" in header:
        row["ingest_method"] = cell("Ingest Method")
    return row


def _read_rows(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = _normalise_header(reader.fieldnames)

        missing = [col for col in ESSENTIAL_COLUMNS if col not in header]
        if missing:
            raise ExportInvariantError(
                f"{path.name}: missing essential column(s) {missing}; "
                f"found {sorted(header)}"
            )
        present = [col for col in CHECKSUM_COLUMNS if col in header]

        rows: List[Dict[str, Any]] = []
        for line_no, raw in enumerate(reader, start=2):
            rows.append(_parse_row(raw, header, path, line_no, present))
    return rows, present


def validate_rounds(rounds: Sequence[Dict[str, Any]]) -> None:
    """Assert the export invariants. Raises on the first violation.

    Three invariants, each cheap and each protecting a real failure mode:

    1. ``Band`` matches ``linguistics.band_for`` — a drifted band definition
       would silently relabel the target class.
    2. ``Points == 100 + 30*log2(Multiplier)`` — the export's own arithmetic
       agreeing with ours proves neither side has been rescaled.
    3. ``Color`` is a function of ``Band`` — one colour per band, no more. This
       is checked structurally rather than against the linguistics hex values,
       because the export emits ``rgb(...)`` while the vocabulary stores hex.
       What matters is that the mapping is deterministic, not its notation.
    """
    colour_by_band: Dict[str, Any] = {}

    for row in rounds:
        multiplier = float(row["multiplier"])
        expected_band = ling.band_for(multiplier)

        declared_band = row.get("export_band")
        if declared_band is not None and str(declared_band).strip():
            got = str(declared_band).strip().lower()
            if got not in (expected_band["key"], expected_band["label"].lower()):
                raise ExportInvariantError(
                    f"round {row['id']}: Multiplier {multiplier} is band "
                    f"{expected_band['key']!r} but export declares {got!r}"
                )

        declared_points = row.get("export_points")
        if declared_points is not None and str(declared_points).strip():
            try:
                observed = float(str(declared_points).strip())
            except ValueError:
                raise ExportInvariantError(
                    f"round {row['id']}: non-numeric Points {declared_points!r}"
                ) from None
            expected = ling.to_points(multiplier)
            if abs(observed - expected) > POINTS_TOLERANCE:
                raise ExportInvariantError(
                    f"round {row['id']}: Points {observed} != "
                    f"100 + 30*log2({multiplier}) = {expected}"
                )

        declared_colour = row.get("export_color")
        if declared_colour is not None and str(declared_colour).strip():
            colour = str(declared_colour).strip()
            seen = colour_by_band.setdefault(expected_band["key"], colour)
            if seen != colour:
                raise ExportInvariantError(
                    f"round {row['id']}: band {expected_band['key']!r} maps to "
                    f"both {seen!r} and {colour!r}; Color is not a function of Band"
                )


def load_exports(
    paths: Iterable[Any],
    *,
    validate: bool = True,
) -> Tuple[List[Dict[str, Any]], LoadReport]:
    """Load one or more exports into a single ascending, deduplicated tape.

    Rows are deduplicated by ``ID``, keeping first occurrence. That is what makes
    the filtered >=10x export safe to pass alongside the full tape: it is a
    strict subset, so merging the two must not double-count its rounds.

    Ordering is by timestamp, not ID. ID order is not guaranteed to be time order
    in these exports, and every downstream index assumes chronological order.
    """
    report = LoadReport()
    merged: Dict[int, Dict[str, Any]] = {}
    checksums: List[str] = []

    path_list = [Path(p) for p in paths]
    if not path_list:
        raise ExportInvariantError("no input paths given")

    for path in path_list:
        if not path.is_file():
            raise ExportInvariantError(f"no such export: {path}")
        rows, present = _read_rows(path)
        report.sources.append(str(path))
        report.rows_read += len(rows)
        for col in present:
            if col not in checksums:
                checksums.append(col)
        for row in rows:
            if row["id"] in merged:
                report.duplicate_ids += 1
                continue
            merged[row["id"]] = row

    rounds = sorted(merged.values(), key=lambda r: (r["ts"], r["id"]))
    if not rounds:
        raise ExportInvariantError("export(s) contained no usable rows")

    if validate:
        validate_rounds(rounds)

    ids = [r["id"] for r in rounds]
    report.rows_out = len(rounds)
    report.checksum_columns_present = checksums
    report.id_order_equals_time_order = all(a < b for a, b in zip(ids, ids[1:]))
    report.span = (rounds[0]["created_at"], rounds[-1]["created_at"])
    for row in rounds:
        report.band_counts[row["band"]] = report.band_counts.get(row["band"], 0) + 1

    return rounds, report


def load_export(
    path: Any, *, validate: bool = True
) -> Tuple[List[Dict[str, Any]], LoadReport]:
    """Convenience wrapper around :func:`load_exports` for a single file."""
    return load_exports([path], validate=validate)


def multipliers(rounds: Sequence[Dict[str, Any]]) -> List[float]:
    """Extract the multiplier series — the only informative column."""
    return [float(r["multiplier"]) for r in rounds]
