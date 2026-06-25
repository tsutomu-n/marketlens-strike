from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidates import (
    _paper_preview_candidates,
    _paper_preview_selected_rows,
)

from .helpers import _write_data, _write_spec, load_authoring_spec


def test_paper_preview_selected_rows_keep_first_unblocked_long_or_short(tmp_path) -> None:
    frame = pl.DataFrame(
        [
            {
                "ts_signal": "2026-01-01T04:00:00+00:00",
                "signal_id": "sig-late",
                "side": "long",
                "block_reasons": [],
            },
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-none",
                "side": "none",
                "block_reasons": [],
            },
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-blocked",
                "side": "short",
                "block_reasons": ["risk_gate"],
            },
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-first",
                "side": "short",
                "block_reasons": [],
            },
        ]
    )

    selected = _paper_preview_selected_rows(frame)

    assert [row["signal_id"] for row in selected] == ["sig-first"]


def test_paper_preview_candidates_block_selected_ndx_candidate_without_promotion(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
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

    candidates, selected_ids, rejected_ids = _paper_preview_candidates(
        spec=spec,
        selected_rows=[row],
        selected=True,
        trial_id="trial-1",
        now=now,
        rejection_reasons=["unused"],
    )

    assert selected_ids == []
    assert rejected_ids == ["candidate-trial-1-sig-1"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.status == "blocked"
    assert candidate.signal_id == "sig-1"
    assert candidate.side == "long"
    assert candidate.entry_order_type == "limit"
    assert candidate.entry_time_in_force == "ioc"
    assert candidate.max_fill_fraction == 0.5
    assert candidate.depth_participation_rate == 0.25
    assert candidate.block_reasons == ["VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION"]


def test_paper_preview_candidates_build_no_signal_placeholder(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)

    candidates, selected_ids, rejected_ids = _paper_preview_candidates(
        spec=spec,
        selected_rows=[],
        selected=False,
        trial_id="trial-empty",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        rejection_reasons=["insufficient_trades_or_no_signal"],
    )

    assert selected_ids == []
    assert rejected_ids == ["candidate-trial-empty-no-signal"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.status == "no_signal"
    assert candidate.signal_id is None
    assert candidate.side == "none"
    assert candidate.block_reasons == ["insufficient_trades_or_no_signal"]
