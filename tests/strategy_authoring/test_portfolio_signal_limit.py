from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.portfolio_signal_limit import (
    _apply_portfolio_signal_limit,
)


def _spec(limit: int | None):
    return SimpleNamespace(
        rules=SimpleNamespace(
            portfolio=SimpleNamespace(max_signals_per_timestamp=limit),
        ),
    )


def test_portfolio_signal_limit_keeps_passthrough_and_top_ranked_rows() -> None:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = [
        {"signal_id": "hold", "ts_signal": ts, "side": "none", "rank_score": None},
        {"signal_id": "low", "ts_signal": ts, "side": "long", "rank_score": 0.2},
        {"signal_id": "missing-rank", "ts_signal": ts, "side": "short", "rank_score": None},
        {"signal_id": "high", "ts_signal": ts, "side": "long", "rank_score": 0.9},
        {"signal_id": "later", "ts_signal": later, "side": "long", "rank_score": 0.1},
    ]

    limited = _apply_portfolio_signal_limit(rows, _spec(1))

    assert [row["signal_id"] for row in limited] == ["hold", "high", "later"]


def test_portfolio_signal_limit_is_noop_without_limit() -> None:
    rows = [
        {"signal_id": "a", "ts_signal": "2026-01-01T00:00:00Z", "side": "long"},
        {"signal_id": "b", "ts_signal": "2026-01-01T00:00:00Z", "side": "short"},
    ]

    limited = _apply_portfolio_signal_limit(rows, _spec(None))

    assert limited is rows
