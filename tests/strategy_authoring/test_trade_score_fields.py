from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_score_fields import (
    _trade_score_fields,
)


def _spec(*, confidence: float = 0.8):
    return SimpleNamespace(rules=SimpleNamespace(confidence=confidence))


def test_trade_score_fields_preserve_rank_score_tail_bucket_and_source_values() -> None:
    fields = _trade_score_fields(
        spec=_spec(confidence=0.7),
        row={
            "source_confidence": "source-raw",
            "venue_quality_score": 0.9,
        },
        raw_score=0.86,
        rank=0.85,
    )

    assert fields == {
        "raw_score": 0.86,
        "rank_score": 0.85,
        "percentile_rank": 0.85,
        "tail_bucket": "top",
        "confidence": 0.7,
        "source_confidence": "source-raw",
        "venue_quality_score": 0.9,
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
    }


def test_trade_score_fields_preserve_none_rank_defaults() -> None:
    fields = _trade_score_fields(
        spec=_spec(),
        row={},
        raw_score=None,
        rank=None,
    )

    assert fields == {
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.8,
        "source_confidence": None,
        "venue_quality_score": None,
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
    }
