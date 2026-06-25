from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_execution_latency_queue_fields import (
    _trade_execution_latency_queue_fields,
)


def _execution(**overrides):
    defaults = {
        "max_latency_ms": None,
        "max_latency_ms_column": None,
        "latency_column": "latency_ms",
        "min_queue_position_score": None,
        "min_queue_position_score_column": None,
        "queue_position_score_column": "queue_position_score",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {
        "max_latency_ms": None,
        "min_queue_position_score": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_execution_latency_queue_fields_resolve_defaults() -> None:
    assert _trade_execution_latency_queue_fields(row={}, execution=_execution()) == {
        "max_latency_ms": None,
        "latency_ms": None,
        "min_queue_position_score": None,
        "queue_position_score": None,
    }


def test_trade_execution_latency_queue_fields_use_columns_overrides_and_regime() -> None:
    fields = _trade_execution_latency_queue_fields(
        row={
            "row_max_latency": 30.0,
            "latency_override": "12",
            "row_min_queue": 0.35,
            "queue_score": 0.7,
        },
        execution=_execution(
            max_latency_ms_column="row_max_latency",
            min_queue_position_score_column="row_min_queue",
            queue_position_score_column="queue_score",
        ),
        regime=_regime(
            max_latency_ms=100.0,
            min_queue_position_score=0.5,
        ),
        execution_overrides={
            "latency_column": "latency_override",
            "queue_position_score_column": "queue_score",
        },
    )

    assert fields == {
        "max_latency_ms": 30.0,
        "latency_ms": 12.0,
        "min_queue_position_score": 0.35,
        "queue_position_score": 0.7,
    }
