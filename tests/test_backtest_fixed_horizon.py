from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.bridge import run_backtest_bridge_with_decisions


def _quote(ts_hour: int, price: float) -> dict:
    return {
        "ts_client": datetime(2026, 5, 22, ts_hour, 0, tzinfo=timezone.utc).isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "XYZ100",
        "venue_symbol": "XYZ100",
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
        "spread_bps": 1.0,
        "oracle_ts_ms": 1779415479000 + ts_hour * 3600 * 1000,
        "market_status": "open",
        "is_tradable": True,
    }


def test_backtest_fixed_horizon_uses_first_quote_after_horizon(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    signals_path = tmp_path / "signals.csv"
    pl.DataFrame([_quote(0, 100.0), _quote(1, 90.0), _quote(4, 110.0)]).write_parquet(quotes_path)
    signals_path.write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength\n"
        "2026-05-22T00:00:00+00:00,XYZ100,long,4h,1.0\n",
        encoding="utf-8",
    )

    metrics, _records, summary = run_backtest_bridge_with_decisions(
        quotes_path,
        signals_path,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )

    assert summary["exit_model"] == "fixed_horizon"
    assert metrics[0].trade_count == 1
    assert metrics[0].total_return > 0


def test_backtest_fixed_horizon_marks_missing_exit_as_stale(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    signals_path = tmp_path / "signals.csv"
    pl.DataFrame([_quote(0, 100.0), _quote(1, 90.0)]).write_parquet(quotes_path)
    signals_path.write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength\n"
        "2026-05-22T00:00:00+00:00,XYZ100,long,4h,1.0\n",
        encoding="utf-8",
    )

    metrics, _records, summary = run_backtest_bridge_with_decisions(
        quotes_path,
        signals_path,
        exit_model="fixed_horizon",
        holding_horizon_minutes=240,
    )

    assert summary["exit_model"] == "fixed_horizon"
    assert metrics[0].trade_count == 0
    assert metrics[0].stale_rejected_count == 1
