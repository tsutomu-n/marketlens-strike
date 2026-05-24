from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.paper.runner import run_paper_step
from sis.state.store import StateStore


def _write_inputs(data_dir) -> None:
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "venue_symbol": "QQQ/USD",
                "exec_buy_price": 100.0,
                "exec_sell_price": 99.9,
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
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc),
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "venue_symbol": "QQQ/USD",
                "exec_buy_price": 101.0,
                "exec_sell_price": 100.9,
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
    ).write_parquet(data_dir / "normalized/quotes.parquet")
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/signals.csv").write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength,strategy_name,reason\n"
        "2026-05-22T00:00:00+00:00,QQQ,long,4h,1.0,qqq_trend_rates_vix,test\n",
        encoding="utf-8",
    )
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,open_fee_bps,close_fee_bps,spread_p50_bps,holding_cost_4h_bps\n"
        "gtrade,QQQ,5,5,2,1\n",
        encoding="utf-8",
    )


def test_run_paper_step_writes_stateful_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_inputs(data_dir)
    state_path = data_dir / "state/marketlens.sqlite"

    summary = run_paper_step(data_dir, state_path=state_path)

    assert summary.orders_count == 1
    assert summary.fills_count == 1
    assert summary.open_positions == 1
    assert summary.orders_path.exists()
    assert summary.fills_path.exists()
    assert summary.positions_path.exists()
    assert summary.daily_pnl_path.exists()
    assert summary.report_path.exists()

    store = StateStore(state_path)
    payload = store.get_json("paper_last_run")
    assert isinstance(payload, dict)
    assert payload["orders_count"] == 1
    assert store.get_json("paper_positions")


def test_run_paper_step_restores_existing_positions(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_inputs(data_dir)
    state_path = data_dir / "state/marketlens.sqlite"
    store = StateStore(state_path)
    store.set_json(
        "paper_positions",
        [
            {
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "side": "long",
                "quantity": 1.0,
                "avg_entry_price": 99.0,
                "opened_at": "2026-05-21T00:00:00+00:00",
                "updated_at": "2026-05-21T00:00:00+00:00",
                "realized_pnl": 0.0,
            }
        ],
    )

    summary = run_paper_step(data_dir, state_path=state_path)

    assert summary.open_positions == 1
    positions = pl.read_parquet(summary.positions_path)
    assert positions.height == 1
    assert positions["quantity"][0] == 2.0
