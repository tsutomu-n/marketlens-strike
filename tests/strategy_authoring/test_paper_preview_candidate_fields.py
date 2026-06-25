from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_fields import (
    _paper_preview_candidate_fields,
)

from .helpers import _write_spec, load_authoring_spec


def _spec(tmp_path: Path):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    return load_authoring_spec(spec_path)


def test_paper_preview_candidate_fields_use_selected_row_values(tmp_path) -> None:
    fields = _paper_preview_candidate_fields(
        spec=_spec(tmp_path),
        row={
            "execution_venue": "paper_venue",
            "execution_symbol": "PAPER",
            "real_market_symbol": "QQQ",
            "side": "short",
            "timeframe": "1h",
            "raw_score": 0.8,
            "rank_score": 0.9,
            "percentile_rank": 0.91,
            "tail_bucket": "top",
            "confidence": 0.77,
            "reason_codes": ["entry"],
            "position_weight": 0.2,
            "notional_usd": 2500.0,
            "feature_snapshot_ref": "feature-ref",
            "quote_ref": "quote-ref",
            "tracking_ref": "tracking-ref",
        },
        selected=True,
    )

    assert fields.execution_venue == "paper_venue"
    assert fields.execution_symbol == "PAPER"
    assert fields.real_market_symbol == "QQQ"
    assert fields.side == "short"
    assert fields.timeframe == "1h"
    assert fields.raw_score == 0.8
    assert fields.rank_score == 0.9
    assert fields.percentile_rank == 0.91
    assert fields.tail_bucket == "top"
    assert fields.confidence == 0.77
    assert fields.entry_reason_codes == ["entry"]
    assert fields.position_weight == 0.2
    assert fields.notional_usd == 2500.0
    assert fields.feature_snapshot_ref == "feature-ref"
    assert fields.quote_ref == "quote-ref"
    assert fields.tracking_ref == "tracking-ref"


def test_paper_preview_candidate_fields_use_neutral_placeholder_values(tmp_path) -> None:
    fields = _paper_preview_candidate_fields(spec=_spec(tmp_path), row={}, selected=False)

    assert fields.execution_venue == "trade_xyz"
    assert fields.execution_symbol == "XYZ100"
    assert fields.real_market_symbol == "QQQ"
    assert fields.side == "none"
    assert fields.timeframe == "4h"
    assert fields.raw_score is None
    assert fields.rank_score is None
    assert fields.percentile_rank is None
    assert fields.tail_bucket == "none"
    assert fields.confidence == 0.0
    assert fields.entry_reason_codes == []
    assert fields.position_weight is None
    assert fields.notional_usd is None
    assert fields.feature_snapshot_ref is None
    assert fields.quote_ref is None
    assert fields.tracking_ref is None
