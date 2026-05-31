from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import (
    BacktestConfig,
    GateConfig,
    PeriodConfig,
    PositionSizingConfig,
)
from sis.backtest.engine.runner import BreakoutParameters, run_backtest
from sis.backtest.trade_xyz.cost_model import FeeResolution
from sis.backtest.trade_xyz.gates import evaluate_close_fill_gate, evaluate_open_fill_gate


def _fee() -> FeeResolution:
    return FeeResolution(taker_fee_bps=9, maker_fee_bps=3, source="row")


def test_open_fill_gate_prefers_fill_snapshot_fields() -> None:
    result = evaluate_open_fill_gate(
        {
            "is_tradable": True,
            "fill_is_tradable": False,
            "block_reasons": [],
            "fill_block_reasons": [],
            "market_status": "open",
            "fill_market_status": "open",
        },
        gates=GateConfig(),
        fee=_fee(),
        fill_price_resolved=True,
    )

    assert not result.allowed
    assert result.reasons == ["fill_row_is_tradable_false"]


def test_open_fill_gate_blocks_fill_snapshot_block_reasons_and_fee() -> None:
    result = evaluate_open_fill_gate(
        {
            "fill_is_tradable": True,
            "fill_block_reasons": ["HALT"],
            "fill_market_status": "open",
        },
        gates=GateConfig(),
        fee=FeeResolution.unresolved(),
        fill_price_resolved=True,
    )

    assert not result.allowed
    assert result.reasons == ["fill_fee_unresolved", "fill_row_block_reasons_non_empty"]


def test_close_fill_gate_allows_close_only_status() -> None:
    result = evaluate_close_fill_gate(
        {"fill_market_status": "close_only"},
        fee=_fee(),
        fill_price_resolved=True,
    )

    assert result.allowed


def test_runner_blocks_entry_when_fill_snapshot_is_not_tradable(tmp_path) -> None:
    frame = pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(4)],
            "symbol": ["SP500"] * 4,
            "close": [100.0, 101.0, 103.0, 104.0],
            "best_bid": [99.9, 100.9, 102.9, 103.9],
            "best_ask": [100.1, 101.1, 103.1, 104.1],
            "taker_fee_bps": [9.0] * 4,
            "maker_fee_bps": [3.0] * 4,
            "market_status": ["open"] * 4,
            "is_tradable": [True] * 4,
            "block_reasons": [[] for _ in range(4)],
            "fill_is_tradable": [True, True, True, False],
            "fill_market_status": ["open"] * 4,
            "fill_block_reasons": [[] for _ in range(4)],
        }
    )
    config = BacktestConfig(
        run_id="fill-snapshot-block",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 4, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )

    result = run_backtest(
        config=config,
        market_data=frame,
        out_dir=tmp_path,
        input_data_ref="fixture://fill-snapshot-block",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    assert pl.read_parquet(result.run_dir / "fills.parquet").is_empty()
    assert (
        "fill_row_is_tradable_false"
        in pl.read_parquet(result.run_dir / "blocked_events.parquet").get_column("reason").to_list()
    )
