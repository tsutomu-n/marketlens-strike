from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.runner import BreakoutParameters, run_backtest
from sis.backtest.trade_xyz.ws_ingestion import build_bbo_bars_with_active_asset_state


def _ms(hour: int, minute: int = 0) -> int:
    return int(datetime(2026, 6, 2, hour, minute, tzinfo=timezone.utc).timestamp() * 1000)


def _bbo_row(hour: int, price: float) -> dict:
    return {
        "ts_client": datetime(2026, 6, 2, hour, tzinfo=timezone.utc).isoformat(),
        "source": "trade_xyz_ws_bbo",
        "canonical_symbol": "SP500",
        "source_ts_ms": _ms(hour),
        "recv_ts_ms": _ms(hour, 0) + 100,
        "mid_price": price,
        "best_bid": price - 0.1,
        "best_ask": price + 0.1,
        "exec_buy_price": price + 0.1,
        "exec_sell_price": price - 0.1,
        "spread_bps": 2.0,
        "taker_fee_bps": 9.0,
        "maker_fee_bps": 3.0,
        "fee_mode": "standard",
        "market_status": "open",
        "is_tradable": True,
        "block_reasons": [],
    }


def _state_row(hour: int, minute: int, mark_price: float) -> dict:
    return {
        "ts_client": datetime(2026, 6, 2, hour, minute, tzinfo=timezone.utc).isoformat(),
        "source": "trade_xyz_ws_activeAssetCtx",
        "canonical_symbol": "SP500",
        "recv_ts_ms": _ms(hour, minute),
        "mark_price": mark_price,
        "oracle_price": mark_price + 0.2,
        "index_price": mark_price + 0.1,
        "mid_price": mark_price,
        "funding_rate": 0.00001,
        "open_interest_usd": 1234.0,
        "oracle_ts_ms": None,
        "market_status": "unknown",
        "is_tradable": False,
        "block_reasons": ["BLOCK_NO_BBO_FILL_SNAPSHOT"],
    }


def test_build_bbo_bars_with_active_asset_state_uses_no_future_state() -> None:
    frame = pl.DataFrame(
        [
            _bbo_row(0, 100.0),
            _bbo_row(1, 101.0),
            _state_row(0, 30, 100.5),
            _state_row(1, 1, 999.0),
        ]
    )

    bars = build_bbo_bars_with_active_asset_state(frame, symbol="SP500", timeframe="1h")

    first = bars.row(0, named=True)
    second = bars.row(1, named=True)
    assert first["event_ts"] == datetime(2026, 6, 2, 1, tzinfo=timezone.utc)
    assert first["state_mark_price"] == 100.5
    assert first["state_observed_ts_ms"] == _ms(0, 30)
    assert first["state_oracle_price"] == 100.7
    assert first["fill_best_bid"] == 99.9
    assert first["fill_best_ask"] == 100.1
    assert first["exec_buy_price"] == 100.1
    assert first["exec_sell_price"] == 99.9
    assert second["event_ts"] == datetime(2026, 6, 2, 2, tzinfo=timezone.utc)
    assert second["state_mark_price"] == 999.0
    assert second["state_observed_ts_ms"] == _ms(1, 1)


def test_ws_bbo_bar_fixture_runs_minimal_backtest(tmp_path) -> None:
    frame = pl.DataFrame(
        [_bbo_row(hour, price) for hour, price in enumerate([100, 101, 103, 102, 99, 98])]
    )
    bars = build_bbo_bars_with_active_asset_state(frame, symbol="SP500", timeframe="1h")
    config = BacktestConfig(
        run_id="ws-smoke",
        strategy_id="sp500_ws_smoke",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            warmup_start_ts=datetime(2026, 6, 2, 1, tzinfo=timezone.utc),
            evaluation_start_ts=datetime(2026, 6, 2, 2, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 6, 2, 6, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )

    result = run_backtest(
        config=config,
        market_data=bars,
        out_dir=tmp_path,
        input_data_ref="fixture://trade_xyz_ws_bbo",
        breakout=BreakoutParameters(entry_lookback=2, exit_lookback=2),
    )

    assert result.run_dir == tmp_path / "ws-smoke"
    assert (result.run_dir / "backtest_run.json").exists()
    assert (result.run_dir / "fills.parquet").exists()
