from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.signal_score_helpers import (
    _rank_score,
    _score_value,
    _tail_bucket,
)


def test_rank_score_clamps_to_unit_interval_and_preserves_missing() -> None:
    assert _rank_score(None) is None
    assert _rank_score(-1.0) == 0.0
    assert _rank_score(0.4) == 0.4
    assert _rank_score(2.0) == 1.0


def test_tail_bucket_preserves_boundary_behavior() -> None:
    assert _tail_bucket(None) == "none"
    assert _tail_bucket(0.8) == "top"
    assert _tail_bucket(0.2) == "bottom"
    assert _tail_bucket(0.5) == "middle"


def test_score_value_reads_numeric_raw_score_only() -> None:
    assert _score_value({"raw_score": 0.25}) == 0.25
    assert _score_value({"raw_score": "0.25"}) is None
    assert _score_value({}) is None
