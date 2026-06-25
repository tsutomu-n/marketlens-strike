from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.cross_sectional_rank_selection import (
    _cross_sectional_rank_selection,
    _cross_sectional_selection_count,
)


def test_cross_sectional_selection_count_uses_fixed_or_fraction_count() -> None:
    assert _cross_sectional_selection_count(5, fixed_count=2, fraction=0.8) == 2
    assert _cross_sectional_selection_count(5, fixed_count=None, fraction=0.4) == 2
    assert _cross_sectional_selection_count(0, fixed_count=None, fraction=0.4) == 0
    assert _cross_sectional_selection_count(5, fixed_count=None, fraction=None) == 0


def test_cross_sectional_rank_selection_builds_percentiles_and_tail_ids() -> None:
    selection = _cross_sectional_rank_selection(
        [
            {"signal_id": "mid", "raw_score": 2.0},
            {"signal_id": "top", "raw_score": 3.0},
            {"signal_id": "bottom", "raw_score": 1.0},
            {"signal_id": "missing", "raw_score": None},
        ],
        long_top_n=1,
        long_top_fraction=None,
        short_bottom_n=1,
        short_bottom_fraction=None,
    )

    assert selection.percentile_by_id == {"top": 1.0, "mid": 0.5, "bottom": 0.0}
    assert selection.top_ids == {"top"}
    assert selection.bottom_ids == {"bottom"}
    assert selection.unscored_ids == {"missing"}


def test_cross_sectional_rank_selection_excludes_top_ids_from_bottom_ids() -> None:
    selection = _cross_sectional_rank_selection(
        [
            {"signal_id": "only", "raw_score": 1.0},
        ],
        long_top_n=1,
        long_top_fraction=None,
        short_bottom_n=1,
        short_bottom_fraction=None,
    )

    assert selection.percentile_by_id == {"only": 1.0}
    assert selection.top_ids == {"only"}
    assert selection.bottom_ids == set()
