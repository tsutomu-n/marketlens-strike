from datetime import datetime, timezone

import polars as pl

from sis.backtest.bridge import run_backtest_bridge
from sis.backtest.costs import load_cost_profiles, round_trip_cost_bps


def test_round_trip_cost_bps_spread_priority_and_holding_horizon(tmp_path) -> None:
    cost_matrix = tmp_path / "venue_cost_matrix.csv"
    cost_matrix.write_text(
        "venue,symbol,open_fee_bps,close_fee_bps,spread_p50_bps,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps\n"
        "gtrade,SPY,5,5,3,7,1,2,4\n",
        encoding="utf-8",
    )
    profiles = load_cost_profiles(cost_matrix)

    total_live, source_live = round_trip_cost_bps(
        venue="gtrade",
        symbol="SPY",
        holding_horizon="1d",
        quote_spread_bps=2.5,
        cost_profiles=profiles,
    )
    assert total_live == 14.5
    assert source_live == "live_spread"

    total_p90, source_p90 = round_trip_cost_bps(
        venue="gtrade",
        symbol="SPY",
        holding_horizon="3d",
        quote_spread_bps=None,
        cost_profiles=profiles,
    )
    assert total_p90 == 21.0
    assert source_p90 == "matrix_spread_p90"


def test_backtest_bridge_uses_signal_timeframe_holding_cost_from_matrix(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    signals_path = tmp_path / "signals.csv"
    cost_matrix_path = tmp_path / "venue_cost_matrix.csv"

    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "mark_price": 100.0,
                "index_price": 100.0,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779415479000,
                "market_status": "open",
                "is_tradable": True,
            },
            {
                "ts_client": datetime(2026, 5, 23, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "mark_price": 101.0,
                "index_price": 101.0,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779501879000,
                "market_status": "open",
                "is_tradable": True,
            },
        ]
    ).write_parquet(quotes_path)

    signals_path.write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength\n"
        "2026-05-22T00:00:00+00:00,SPY,long,1d,1.0\n",
        encoding="utf-8",
    )

    cost_matrix_path.write_text(
        "venue,symbol,open_fee_bps,close_fee_bps,spread_p50_bps,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps\n"
        "gtrade,SPY,5,5,3,7,1,11,33\n",
        encoding="utf-8",
    )

    metrics = run_backtest_bridge(
        quotes_path, signals_path=signals_path, cost_matrix_path=cost_matrix_path
    )

    assert len(metrics) == 1
    assert metrics[0].trade_count == 1
    assert metrics[0].cost_drag_bps == 23.0
    assert metrics[0].cost_source == "live_spread"
