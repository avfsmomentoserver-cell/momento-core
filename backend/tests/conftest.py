"""Pytest configuration for the backend test suite.

Puts ``backend/`` on ``sys.path`` so tests import ``momento``, ``features`` and
``research`` by package name. This replaces the hardcoded
``sys.path.insert('/home/pirates/...')`` in the older scripts, which made them
unrunnable anywhere but one machine.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402  (import after sys.path setup)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def sample_rows():
    """Synthetic export rows covering low, mid and moonshot bands.

    Deliberately small and hand-checkable: the values below are verified against
    ``linguistics.to_points`` so a drift in either the vocabulary or the loader
    shows up as a failure here rather than as a puzzling backtest number.
    """
    return [
        # (id, timestamp, multiplier)
        (1, "2026-07-01T00:00:00.000+00:00", 1.00),
        (2, "2026-07-01T00:00:13.000+00:00", 1.45),
        (3, "2026-07-01T00:00:27.000+00:00", 2.30),
        (4, "2026-07-01T00:00:41.000+00:00", 1.10),
        (5, "2026-07-01T00:00:55.000+00:00", 24.50),
        (6, "2026-07-01T00:01:09.000+00:00", 3.75),
        (7, "2026-07-01T00:01:23.000+00:00", 1.02),
        (8, "2026-07-01T00:01:37.000+00:00", 112.00),
    ]


@pytest.fixture
def write_export(tmp_path, sample_rows):
    """Write an export CSV, computing the checksum columns from the vocabulary."""
    from momento import linguistics as ling

    def _write(name: str = "export.csv", rows=None, include_checksums: bool = True):
        rows = sample_rows if rows is None else rows
        path = tmp_path / name
        header = ["ID", "Timestamp", "Multiplier"]
        if include_checksums:
            header += ["Color", "Band", "Points", "Ingest Method"]

        lines = [",".join(header)]
        for round_id, timestamp, multiplier in rows:
            band = ling.band_for(multiplier)
            cells = [str(round_id), timestamp, f"{multiplier:.2f}"]
            if include_checksums:
                cells += [
                    band["color"],
                    band["key"],
                    f"{ling.to_points(multiplier):.3f}",
                    "file",
                ]
            lines.append(",".join(cells))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    return _write
