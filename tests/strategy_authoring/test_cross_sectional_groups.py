from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.cross_sectional_groups import (
    _cross_sectional_candidate_groups,
)


def _row(signal_id: str, *, side: str = "long", ts: str = "2026-01-01", group=None):
    return {
        "signal_id": signal_id,
        "side": side,
        "ts_signal": ts,
        "_cross_sectional_group": group,
    }


def test_cross_sectional_candidate_groups_without_group_column() -> None:
    rows = [
        _row("hold", side="none"),
        _row("a", ts="2026-01-01"),
        _row("b", ts="2026-01-02"),
    ]

    grouped = _cross_sectional_candidate_groups(rows, group_column=None)

    assert grouped.passthrough_rows == [rows[0]]
    assert grouped.missing_group_rows == []
    assert grouped.candidates_by_key == {
        ("2026-01-01", None): [rows[1]],
        ("2026-01-02", None): [rows[2]],
    }


def test_cross_sectional_candidate_groups_tracks_groups_and_missing_group_rows() -> None:
    rows = [
        _row("hold", side="none", group="ignored"),
        _row("growth-a", ts="2026-01-01", group="growth"),
        _row("missing", ts="2026-01-01", group=" "),
        _row("value-a", ts="2026-01-01", group="value"),
        _row("growth-b", ts="2026-01-02", group="growth"),
    ]

    grouped = _cross_sectional_candidate_groups(rows, group_column="sector")

    assert grouped.passthrough_rows == [rows[0]]
    assert grouped.missing_group_rows == [rows[2]]
    assert grouped.candidates_by_key == {
        ("2026-01-01", "growth"): [rows[1]],
        ("2026-01-01", "value"): [rows[3]],
        ("2026-01-02", "growth"): [rows[4]],
    }
