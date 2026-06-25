from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.cross_sectional_rank_application import (
    _apply_cross_sectional_rank_result,
)
from sis.research.strategy_lab.authoring.compiler.cross_sectional_rank_selection import (
    _CrossSectionalRankSelection,
)
from sis.research.strategy_lab.authoring.io import load_authoring_spec, template_yaml


def _spec(tmp_path, *, min_long_score: float | None = None, max_short_score: float | None = None):
    cross_sectional_lines = [
        "  cross_sectional:",
        "    long_top_n: 1",
        "    short_bottom_n: 1",
    ]
    if min_long_score is not None:
        cross_sectional_lines.append(f"    min_long_score: {min_long_score}")
    if max_short_score is not None:
        cross_sectional_lines.append(f"    max_short_score: {max_short_score}")
    spec_path = tmp_path / "cross-sectional-rank-application.yaml"
    spec_path.write_text(
        template_yaml()
        .replace("  side: long", "  side: auto")
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n" + "\n".join(cross_sectional_lines),
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def _row(signal_id: str, *, raw_score: float | None):
    return {
        "signal_id": signal_id,
        "ts_signal": "2026-01-01T00:00:00+00:00",
        "execution_symbol": "XYZ100",
        "side": "none",
        "raw_score": raw_score,
        "reason_codes": ["base_reason"],
        "block_reasons": [],
        "confidence": 0.7,
        "position_weight": 1.0,
        "notional_usd": 1000.0,
    }


def _selection(
    *,
    top_ids: set[str] | None = None,
    bottom_ids: set[str] | None = None,
    unscored_ids: set[str] | None = None,
):
    return _CrossSectionalRankSelection(
        percentile_by_id={"top": 1.0, "bottom": 0.0, "middle": 0.5, "weak": 0.75},
        top_ids=top_ids or set(),
        bottom_ids=bottom_ids or set(),
        unscored_ids=unscored_ids or set(),
    )


def test_cross_sectional_rank_result_applies_top_selection(tmp_path) -> None:
    row = _row("top", raw_score=0.9)

    updated = _apply_cross_sectional_rank_result(
        row=row,
        rank_selection=_selection(top_ids={"top"}),
        spec=_spec(tmp_path),
    )

    assert updated["side"] == "long"
    assert updated["signal_id"] != "top"
    assert updated["rank_score"] == 1.0
    assert updated["percentile_rank"] == 1.0
    assert updated["tail_bucket"] == "top"
    assert updated["reason_codes"] == ["base_reason", "cross_sectional_top"]


def test_cross_sectional_rank_result_applies_bottom_selection(tmp_path) -> None:
    row = _row("bottom", raw_score=-0.5)

    updated = _apply_cross_sectional_rank_result(
        row=row,
        rank_selection=_selection(bottom_ids={"bottom"}),
        spec=_spec(tmp_path),
    )

    assert updated["side"] == "short"
    assert updated["signal_id"] != "bottom"
    assert updated["rank_score"] == 0.0
    assert updated["tail_bucket"] == "bottom"
    assert updated["reason_codes"] == ["base_reason", "cross_sectional_bottom"]


def test_cross_sectional_rank_result_blocks_unscored_rows(tmp_path) -> None:
    row = _row("missing", raw_score=None)

    updated = _apply_cross_sectional_rank_result(
        row=row,
        rank_selection=_selection(unscored_ids={"missing"}),
        spec=_spec(tmp_path),
    )

    assert updated["side"] == "none"
    assert updated["confidence"] == 0.0
    assert updated["block_reasons"] == ["cross_sectional_score_missing"]


def test_cross_sectional_rank_result_blocks_weak_top_after_annotations(tmp_path) -> None:
    row = _row("weak", raw_score=0.1)

    updated = _apply_cross_sectional_rank_result(
        row=row,
        rank_selection=_selection(top_ids={"weak"}),
        spec=_spec(tmp_path, min_long_score=0.2),
    )

    assert updated["side"] == "none"
    assert updated["rank_score"] == 0.75
    assert updated["percentile_rank"] == 0.75
    assert updated["block_reasons"] == ["cross_sectional_long_score_threshold"]


def test_cross_sectional_rank_result_blocks_weak_bottom_after_annotations(tmp_path) -> None:
    row = _row("weak", raw_score=0.1)

    updated = _apply_cross_sectional_rank_result(
        row=row,
        rank_selection=_selection(bottom_ids={"weak"}),
        spec=_spec(tmp_path, max_short_score=0.0),
    )

    assert updated["side"] == "none"
    assert updated["rank_score"] == 0.75
    assert updated["percentile_rank"] == 0.75
    assert updated["block_reasons"] == ["cross_sectional_short_score_threshold"]


def test_cross_sectional_rank_result_blocks_middle_rows_after_annotations(tmp_path) -> None:
    row = _row("middle", raw_score=0.4)

    updated = _apply_cross_sectional_rank_result(
        row=row,
        rank_selection=_selection(top_ids={"top"}, bottom_ids={"bottom"}),
        spec=_spec(tmp_path),
    )

    assert updated["side"] == "none"
    assert updated["rank_score"] == 0.5
    assert updated["tail_bucket"] == "middle"
    assert updated["block_reasons"] == ["cross_sectional_rank_filter"]
