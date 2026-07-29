"""Loader and export-invariant tests.

These are the tests that stop a corrupted export from silently entering a
backtest, so they assert the failure paths as carefully as the success path.
"""

from __future__ import annotations

import pytest

from momento import linguistics as ling
from research.loader import (
    ExportInvariantError,
    load_export,
    multipliers,
    parse_timestamp,
    validate_rounds,
)


def test_loads_and_reports_provenance(write_export):
    rounds, report = load_export(write_export())

    assert report.rows_read == 8
    assert report.rows_out == 8
    assert report.duplicate_ids == 0
    assert report.checksum_columns_present == ["Band", "Color", "Points"]
    assert sum(report.band_counts.values()) == 8
    assert multipliers(rounds)[:3] == [1.00, 1.45, 2.30]


def test_rows_are_sorted_by_timestamp_not_id(write_export):
    """ID order is not time order in these exports; chronological order wins."""
    rows = [
        (900, "2026-07-01T00:00:30.000+00:00", 2.0),
        (100, "2026-07-01T00:00:10.000+00:00", 3.0),
        (500, "2026-07-01T00:00:20.000+00:00", 4.0),
    ]
    rounds, report = load_export(write_export(rows=rows))

    assert [r["id"] for r in rounds] == [100, 500, 900]
    assert report.id_order_equals_time_order is True


def test_duplicate_ids_are_dropped_once(write_export, sample_rows):
    """The filtered >=10x export is a strict subset, so a merge must not
    double-count the rounds it shares with the full tape."""
    full = write_export("full.csv")
    subset = write_export("subset.csv", rows=[r for r in sample_rows if r[2] >= 10.0])

    from research.loader import load_exports

    rounds, report = load_exports([full, subset])

    assert report.rows_read == 10  # 8 + 2
    assert report.rows_out == 8
    assert report.duplicate_ids == 2
    assert len({r["id"] for r in rounds}) == 8


def test_points_invariant_holds_across_the_range(write_export):
    """Points == 100 + 30*log2(Multiplier), equivalently 100 + 43.28*ln(M)."""
    rounds, _ = load_export(write_export())

    for row in rounds:
        assert row["points"] == pytest.approx(
            ling.to_points(row["multiplier"]), abs=1e-9
        )

    assert ling.to_points(1.0) == pytest.approx(100.0, abs=1e-6)
    assert ling.to_points(2.0) == pytest.approx(130.0, abs=1e-6)
    assert ling.to_points(4.0) == pytest.approx(160.0, abs=1e-6)


def test_band_is_a_pure_function_of_multiplier(write_export):
    rounds, _ = load_export(write_export())

    for row in rounds:
        assert row["band"] == ling.band_for(row["multiplier"])["key"]

    assert ling.band_for(1.0)["key"] == "dust"
    assert ling.band_for(1.9999)["key"] == "low"
    assert ling.band_for(2.0)["key"] == "base"  # lower bound inclusive
    assert ling.band_for(20.0)["key"] == "moonshot"
    assert ling.band_for(10_000.0)["key"] == "cosmic"


def test_wrong_band_is_rejected():
    rounds = [{"id": 1, "multiplier": 24.5, "export_band": "high"}]

    with pytest.raises(ExportInvariantError, match="export declares"):
        validate_rounds(rounds)


def test_wrong_points_is_rejected():
    rounds = [{"id": 2, "multiplier": 2.0, "export_points": "999.0"}]

    with pytest.raises(ExportInvariantError, match="Points"):
        validate_rounds(rounds)


def test_colour_must_be_a_function_of_band():
    """Two different colours for the same band means the export is inconsistent."""
    rounds = [
        {"id": 1, "multiplier": 2.1, "export_color": "rgb(201,138,36)"},
        {"id": 2, "multiplier": 2.9, "export_color": "blue"},
    ]

    with pytest.raises(ExportInvariantError, match="not a function of Band"):
        validate_rounds(rounds)


def test_missing_essential_column_is_rejected(tmp_path):
    path = tmp_path / "broken.csv"
    path.write_text("ID,Multiplier\n1,2.0\n", encoding="utf-8")

    with pytest.raises(ExportInvariantError, match="missing essential column"):
        load_export(path)


def test_multiplier_below_one_is_rejected(tmp_path):
    path = tmp_path / "sub_one.csv"
    path.write_text(
        "ID,Timestamp,Multiplier\n1,2026-07-01T00:00:00+00:00,0.5\n", encoding="utf-8"
    )

    with pytest.raises(ExportInvariantError, match="outside the valid range"):
        load_export(path)


def test_reduced_schema_without_checksums_still_loads(write_export):
    rounds, report = load_export(write_export(include_checksums=False))

    assert report.rows_out == 8
    assert report.checksum_columns_present == []
    # Band and points are still derived, just not cross-checked.
    assert rounds[-1]["band"] == "cosmic"


@pytest.mark.parametrize(
    "raw",
    [
        "2026-07-01T00:00:00.000+00:00",
        "2026-07-01T00:00:00Z",
        "2026-07-01 00:00:00",
    ],
)
def test_timestamp_formats_normalise_to_utc(raw):
    parsed = parse_timestamp(raw)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_unparseable_timestamp_is_rejected():
    with pytest.raises(ExportInvariantError, match="unparseable timestamp"):
        parse_timestamp("not-a-date")
