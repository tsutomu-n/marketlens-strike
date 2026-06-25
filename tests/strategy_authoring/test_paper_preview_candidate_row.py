from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_row import (
    _paper_preview_candidate_row,
)

from .helpers import _write_data, _write_spec, load_authoring_spec


def _spec(tmp_path):
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def test_paper_preview_candidate_row_marks_selected_but_blocked_row_rejected(
    tmp_path,
) -> None:
    row = {
        "signal_id": "sig-1",
        "execution_venue": "trade_xyz",
        "execution_symbol": "XYZ100",
        "real_market_symbol": "QQQ",
        "side": "long",
        "timeframe": "4h",
        "raw_score": 0.8,
        "rank_score": 0.9,
        "percentile_rank": 0.9,
        "tail_bucket": "top",
        "confidence": 0.75,
        "reason_codes": ["entry"],
        "bracket_type": "none",
        "entry_order_type": "limit",
        "entry_limit_offset_bps": 5.0,
        "entry_time_in_force": "ioc",
        "max_fill_fraction": 0.5,
        "depth_participation_rate": 0.25,
        "position_weight": 0.2,
    }

    result = _paper_preview_candidate_row(
        spec=_spec(tmp_path),
        row=row,
        selected=True,
        trial_id="trial-1",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        rejection_reasons=["unused"],
    )

    assert result.selected is False
    assert result.candidate.candidate_id == "candidate-trial-1-sig-1"
    assert result.candidate.status == "blocked"
    assert result.candidate.signal_id == "sig-1"
    assert result.candidate.entry_order_type == "limit"
    assert result.candidate.block_reasons == [
        "VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION"
    ]


def test_paper_preview_candidate_row_builds_no_signal_placeholder(tmp_path) -> None:
    result = _paper_preview_candidate_row(
        spec=_spec(tmp_path),
        row={},
        selected=False,
        trial_id="trial-empty",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        rejection_reasons=["insufficient_trades_or_no_signal"],
    )

    assert result.selected is False
    assert result.candidate.candidate_id == "candidate-trial-empty-no-signal"
    assert result.candidate.status == "no_signal"
    assert result.candidate.signal_id is None
    assert result.candidate.side == "none"
    assert result.candidate.block_reasons == ["insufficient_trades_or_no_signal"]
