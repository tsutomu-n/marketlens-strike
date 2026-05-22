from datetime import datetime, timezone

import polars as pl

from sis.backtest.bridge import run_backtest_bridge, write_backtest_report


def test_backtest_bridge_runs_virtual_execution_from_quotes(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "exec_buy_price": 100.0,
                "exec_sell_price": 99.9,
                "mark_price": None,
                "mid_price": 100.0,
                "oracle_price": 100.0,
                "index_price": None,
                "spread_bps": 1.0,
                "oracle_ts_ms": 1779415479000,
                "market_status": "open",
                "is_tradable": True,
            },
            {
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "exec_buy_price": 105.0,
                "exec_sell_price": 104.9,
                "mark_price": None,
                "mid_price": 105.0,
                "oracle_price": 105.0,
                "index_price": None,
                "spread_bps": 1.0,
                "oracle_ts_ms": 1779429879000,
                "market_status": "open",
                "is_tradable": True,
            },
        ]
    ).write_parquet(quotes_path)

    metrics = run_backtest_bridge(quotes_path)

    assert len(metrics) == 1
    assert metrics[0].trade_count == 1
    assert metrics[0].total_return > 0
    assert metrics[0].cost_drag_bps == 1.0


def test_backtest_report_writes_metrics_table(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    report_path = tmp_path / "backtest_report.md"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "exec_buy_price": None,
                "exec_sell_price": None,
                "mark_price": 100.0,
                "mid_price": None,
                "oracle_price": None,
                "index_price": 100.0,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779415479000,
                "market_status": "open",
                "is_tradable": True,
            },
            {
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "exec_buy_price": None,
                "exec_sell_price": None,
                "mark_price": 101.0,
                "mid_price": None,
                "oracle_price": None,
                "index_price": 101.0,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779429879000,
                "market_status": "open",
                "is_tradable": True,
            },
        ]
    ).write_parquet(quotes_path)

    metrics = run_backtest_bridge(quotes_path)
    write_backtest_report(metrics, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "Backtest Bridge Report" in text
    assert "SPY" in text
