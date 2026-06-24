from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.bridge import BacktestMetrics as BridgeBacktestMetrics
from sis.backtest.costs import CostProfile
from sis.backtest.metrics import (
    BacktestMetrics,
    dominant_cost_source,
    metrics_for_group,
    metrics_from_returns,
)


def _quote(
    *,
    price: float,
    market_status: str = "open",
    is_tradable: bool = True,
    oracle_ts_ms: int | None = 1779415479000,
) -> dict[str, object]:
    return {
        "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
        "venue": "gtrade",
        "canonical_symbol": "SPY",
        "venue_symbol": "SPY/USD",
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
        "spread_bps": 2.0,
        "oracle_ts_ms": oracle_ts_ms,
        "market_status": market_status,
        "is_tradable": is_tradable,
    }


def test_bridge_reexports_backtest_metrics_for_compatibility() -> None:
    assert BridgeBacktestMetrics is BacktestMetrics


def test_metrics_from_returns_calculates_trade_summary() -> None:
    metrics = metrics_from_returns(
        venue="gtrade",
        symbol="SPY",
        returns=[0.10, -0.05, 0.02],
        equity=[1.0, 1.10, 1.045, 1.0659],
        cost_drag_bps=7.0,
        cost_source="matrix",
        stale_rejected=1,
        halt_rejected=2,
        candidate_count=4,
    )

    assert metrics.trade_count == 3
    assert metrics.total_return == pytest.approx(0.0659)
    assert metrics.max_drawdown == pytest.approx(1.045 / 1.10 - 1.0)
    assert metrics.win_rate == pytest.approx(2 / 3)
    assert metrics.profit_factor == pytest.approx(0.12 / 0.05)
    assert metrics.exposure_ratio == pytest.approx(0.75)
    assert metrics.cost_source == "matrix"
    assert metrics.stale_rejected_count == 1
    assert metrics.halt_rejected_count == 2


def test_metrics_for_group_accounts_for_costs_rejects_and_source() -> None:
    frame = pl.DataFrame(
        [
            _quote(price=100.0),
            _quote(price=101.0, oracle_ts_ms=None),
            _quote(price=102.0, market_status="closed", is_tradable=False),
            _quote(price=103.0),
        ]
    )
    cost_profiles = {
        ("gtrade", "SPY"): CostProfile(
            venue="gtrade",
            symbol="SPY",
            open_fee_bps=5.0,
            close_fee_bps=5.0,
            spread_p50_bps=9.0,
            spread_p90_bps=12.0,
            holding_cost_4h_bps=3.0,
            holding_cost_24h_bps=9.0,
            holding_cost_72h_bps=21.0,
        )
    }

    metrics = metrics_for_group(frame, cost_profiles)

    assert metrics.venue == "gtrade"
    assert metrics.canonical_symbol == "SPY"
    assert metrics.trade_count == 2
    assert metrics.cost_drag_bps == 30.0
    assert metrics.cost_source == "live_spread"
    assert metrics.stale_rejected_count == 1
    assert metrics.halt_rejected_count == 1


def test_dominant_cost_source_prefers_most_common_source() -> None:
    assert dominant_cost_source(["matrix", "spread", "matrix"]) == "matrix"
    assert dominant_cost_source([]) is None
