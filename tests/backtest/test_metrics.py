from __future__ import annotations

import polars as pl
import pytest

from sis.backtest.engine.metrics import calculate_metrics


def test_calculate_metrics_outputs_rev3_core_and_trade_xyz_fields() -> None:
    equity = pl.DataFrame({"equity": [10_000.0, 10_100.0, 10_050.0]})
    trades = pl.DataFrame({"net_pnl": [100.0, -25.0]})
    fills = pl.DataFrame(
        {
            "fee_amount": [1.0, 1.1, 1.0, 1.05],
            "extra_slippage_amount": [0.0, 0.0, 0.0, 0.0],
            "funding_amount_delta": [0.0, 0.0, 0.0, 0.0],
            "liquidity_flag": ["taker", "taker", "taker", "taker"],
            "fee_source": ["row", "row", "configs/fee_model.trade_xyz.yaml:standard", "row"],
        }
    )
    blocked = pl.DataFrame({"reason": ["fee_unresolved", "fee_unresolved", "is_tradable_false"]})

    metrics = calculate_metrics(
        initial_cash_usd=10_000,
        equity_curve=equity,
        trades=trades,
        fills=fills,
        blocked_events=blocked,
        end_open_position_count=0,
        end_unrealized_pnl=0,
    )

    assert metrics["net_return_after_cost"] == pytest.approx(0.005)
    assert metrics["trade_count"] == 2
    assert metrics["win_rate"] == 0.5
    assert metrics["profit_factor"] == 4.0
    assert metrics["fee_impact"] == 4.15
    assert metrics["fee_source_counts"] == {
        "configs/fee_model.trade_xyz.yaml:standard": 1,
        "row": 3,
    }
    assert metrics["fee_row_resolved_rate"] == 0.75
    assert metrics["fee_config_fallback_rate"] == 0.25
    assert metrics["fee_unresolved_rate_runtime"] == 0.0
    assert metrics["maker_fill_ratio"] == 0
    assert metrics["blocked_reason_counts"] == {
        "fee_unresolved": 2,
        "is_tradable_false": 1,
    }
