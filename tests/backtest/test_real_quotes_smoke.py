from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import pytest


def _ms(hour: int, minute: int = 0) -> int:
    return int(datetime(2026, 6, 2, hour, minute, tzinfo=timezone.utc).timestamp() * 1000)


def _ws_bbo_row(hour: int, price: float) -> dict:
    return {
        "ts_client": datetime(2026, 6, 2, hour, tzinfo=timezone.utc).isoformat(),
        "source": "trade_xyz_ws_bbo",
        "canonical_symbol": "SP500",
        "source_ts_ms": _ms(hour),
        "recv_ts_ms": _ms(hour) + 100,
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
        "mark_price": None,
        "oracle_price": None,
        "index_price": None,
        "funding_rate": None,
        "open_interest_usd": None,
    }


def _ws_state_row(hour: int, minute: int, mark_price: float) -> dict:
    return {
        "ts_client": datetime(2026, 6, 2, hour, minute, tzinfo=timezone.utc).isoformat(),
        "source": "trade_xyz_ws_activeAssetCtx",
        "canonical_symbol": "SP500",
        "source_ts_ms": None,
        "recv_ts_ms": _ms(hour, minute),
        "mid_price": mark_price,
        "best_bid": None,
        "best_ask": None,
        "exec_buy_price": None,
        "exec_sell_price": None,
        "spread_bps": None,
        "taker_fee_bps": 9.0,
        "maker_fee_bps": 3.0,
        "fee_mode": "standard",
        "market_status": "unknown",
        "is_tradable": False,
        "block_reasons": ["BLOCK_NO_BBO_FILL_SNAPSHOT"],
        "mark_price": mark_price,
        "oracle_price": mark_price + 0.2,
        "index_price": mark_price + 0.1,
        "funding_rate": 0.00001,
        "open_interest_usd": 1234.0,
    }


def test_ws_bbo_state_smoke_script_handles_active_asset_ctx_without_source_ts(tmp_path) -> None:
    input_path = tmp_path / "ws_quotes.parquet"
    pl.DataFrame(
        [
            *[_ws_bbo_row(hour, price) for hour, price in enumerate([100, 101, 103, 102, 99, 98])],
            _ws_state_row(0, 30, 100.5),
            _ws_state_row(1, 1, 101.5),
        ]
    ).write_parquet(input_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_trade_xyz_backtest_smoke.py",
            "--input",
            str(input_path),
            "--funding-events",
            "",
            "--symbol",
            "SP500",
            "--timeframe",
            "1h",
            "--event-time-source",
            "source_ts_ms",
            "--out",
            str(tmp_path / "runs"),
            "--entry-lookback",
            "2",
            "--exit-lookback",
            "2",
            "--ws-bbo-state",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    run_dir = Path(completed.stdout.strip().splitlines()[-1])

    assert run_dir.exists()
    assert (run_dir / "fills.parquet").exists()
    run = json.loads((run_dir / "backtest_run.json").read_text(encoding="utf-8"))
    assert run["smoke_only"] is True
    assert run["usable_for_strategy_selection"] is False


def test_real_normalized_quotes_smoke_script_when_available(tmp_path) -> None:
    input_path = Path("data/normalized/quotes.parquet")
    if not input_path.exists():
        pytest.skip("data/normalized/quotes.parquet is not available")

    raw = pl.read_parquet(input_path)
    if "canonical_symbol" not in raw.columns:
        pytest.skip("normalized quotes do not include canonical_symbol")
    if raw.filter(pl.col("canonical_symbol") == "SP500").is_empty():
        pytest.skip("SP500 rows are not available in normalized quotes")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_trade_xyz_backtest_smoke.py",
            "--input",
            str(input_path),
            "--symbol",
            "SP500",
            "--timeframe",
            "1h",
            "--close-source",
            "mid_price",
            "--event-time-source",
            "ts_client",
            "--out",
            str(tmp_path),
            "--auto-small-lookback",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    run_dir = Path(completed.stdout.strip().splitlines()[-1])

    assert run_dir.exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "backtest_report.html").exists()
    assert (run_dir / "data_manifest.json").exists()

    candidate = json.loads((run_dir / "candidate_result.json").read_text(encoding="utf-8"))
    assert candidate["smoke_only"] is True
    assert candidate["usable_for_strategy_selection"] is False

    manifest = json.loads((run_dir / "data_manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_data_ref"] == str(input_path)
    assert manifest["input_file_sha256"]
    assert manifest["close_source"] == "mid_price"
    assert manifest["bar_builder"] == "quote_bar_v1"
