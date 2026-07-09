from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.real_market_ticker_coverage_status import (
    build_real_market_ticker_coverage_status,
)


runner = CliRunner()


def _ms(ts: datetime) -> int:
    return int(ts.timestamp() * 1000)


def _write_candles(source_root: Path, *, row_count: int = 72) -> Path:
    base = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(row_count):
        ts = base + timedelta(minutes=5 * index)
        rows.append(
            {
                "symbol": "BTCUSDT",
                "ts": _ms(ts),
                "open": 60000.0 + index,
                "high": 60005.0 + index,
                "low": 59995.0 + index,
                "close": 60001.0 + index,
                "base_vol": 10.0,
                "quote_vol": 600_000.0,
            }
        )
    out = source_root / "data/candles_5m/date=2026-06-27"
    out.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(out / "candles.parquet")
    return source_root


def _write_tickers(
    source_root: Path,
    *,
    indices: list[int],
    include_bid_ask: bool = True,
) -> Path:
    base = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
    rows = []
    for index in indices:
        ts = base + timedelta(minutes=5 * index)
        ts_ms = _ms(ts)
        rows.append(
            {
                "exchange": "bitget",
                "market_type": "perp_linear",
                "symbol_native": "BTCUSDT",
                "symbol_canonical": "BTCUSDT",
                "ts_exchange_ms": ts_ms,
                "ts_received_ms": ts_ms,
                "source_channel": "rest_ticker",
                "last_px": 60000.0 + index,
                "bid_px": 59999.5 + index if include_bid_ask else None,
                "ask_px": 60000.5 + index if include_bid_ask else None,
                "bid_sz": 1.0,
                "ask_sz": 1.0,
                "mid_px": 60000.0 + index,
                "mark_px": 60000.2 + index,
                "index_px": 60000.0 + index,
                "funding_rate": 0.0001,
                "next_funding_time_ms": ts_ms + 28_800_000,
                "open_interest": 10_000.0,
                "volume_24h_base": 500.0,
                "volume_24h_quote": 30_000_000.0,
                "coverage_class": "native",
                "is_snapshot": True,
                "raw_ref": "bitget.mix.market.ticker",
                "ingested_at_ms": ts_ms,
                "run_id": "test",
            }
        )
    out = source_root / "data/ticker_rows/exchange=bitget/symbol=BTCUSDT/date=2026-06-27"
    out.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(out / "ticker_rows.parquet")
    return source_root


def test_ticker_coverage_status_reports_no_ticker_rows(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=30,
    )

    assert status["decision"] == "NO_TICKER_ROWS"
    assert status["coverage_passed"] is False
    assert status["ticker_covered_candidate_count"] == 0
    assert status["coverage_shortfall"] == 30
    assert status["diagnosis"] == "COLLECT_MORE_TICKER_ROWS"
    assert status["missing_reason_counts"]["HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE"] > 0
    assert "--append-existing" in status["next_actions"][0]["command"]


def test_ticker_coverage_status_rejects_future_only_rows(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")
    _write_tickers(source_root, indices=[71])

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=30,
    )

    assert status["decision"] == "COLLECT_TICKER_SNAPSHOTS"
    assert status["ticker_covered_candidate_count"] == 0
    assert status["diagnosis"] == "COLLECT_MORE_TICKER_ROWS"
    assert status["future_unmatured_ticker_row_count"] == 1
    assert status["missing_reason_counts"]["HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE"] > 0


def test_ticker_coverage_status_waits_for_horizon_maturity(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")
    _write_tickers(source_root, indices=[65])

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=1,
    )

    assert status["decision"] == "COLLECT_TICKER_SNAPSHOTS"
    assert status["diagnosis"] == "WAIT_FOR_HORIZON_MATURITY"
    assert status["future_unmatured_ticker_row_count"] == 1
    assert status["next_actions"][0]["key"] == "wait_for_horizon_then_append_public_ticker_snapshot"
    assert status["next_maturity_hint"]["remaining_seconds_until_latest_ticker_matures"] > 0


def test_ticker_coverage_status_reports_candles_not_advancing(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root", row_count=50)
    _write_tickers(source_root, indices=[60])

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=1,
    )

    assert status["decision"] == "COLLECT_TICKER_SNAPSHOTS"
    assert status["diagnosis"] == "CANDLES_NOT_ADVANCING"
    assert status["latest_candle_ts_ms"] < status["latest_ticker_ts_received_ms"]
    assert status["next_actions"][0]["key"] == "refresh_public_candles_and_ticker_snapshot"


def test_ticker_coverage_status_rejects_stale_rows(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")
    _write_tickers(source_root, indices=[0])

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=1,
        ticker_max_staleness_seconds=60,
    )

    assert status["decision"] == "COLLECT_TICKER_SNAPSHOTS"
    assert status["ticker_covered_candidate_count"] == 0
    assert status["diagnosis"] == "TICKER_ROWS_STALE"
    assert status["missing_reason_counts"]["TICKER_SOURCE_STALE"] > 0


def test_ticker_coverage_status_rejects_rows_without_bid_ask(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")
    _write_tickers(source_root, indices=list(range(12, 48)), include_bid_ask=False)

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=1,
    )

    assert status["decision"] == "COLLECT_TICKER_SNAPSHOTS"
    assert status["valid_bid_ask_row_count"] == 0
    assert status["diagnosis"] == "COLLECT_MORE_TICKER_ROWS"
    assert status["missing_reason_counts"]["HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE"] > 0


def test_ticker_coverage_status_ready_when_target_windows_are_covered(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")
    _write_tickers(source_root, indices=list(range(12, 48)))

    status = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at="2026-06-27T06:00:00Z",
        target_event_count=30,
    )

    assert status["decision"] == "READY_FOR_TICKER_REQUIRED_SAMPLE"
    assert status["coverage_passed"] is True
    assert status["diagnosis"] == "READY_FOR_TICKER_REQUIRED_SAMPLE"
    assert status["coverage_shortfall"] == 0
    assert status["ticker_covered_candidate_count"] >= 30
    assert "--require-ticker-coverage" in status["next_actions"][0]["command"]
    assert status["boundary_flags"]["paper_permission_granted"] is False
    assert status["boundary_flags"]["exchange_write_used"] is False


def test_ticker_coverage_status_cli_writes_artifacts(tmp_path: Path) -> None:
    source_root = _write_candles(tmp_path / "source_root")
    _write_tickers(source_root, indices=list(range(12, 48)))
    out = tmp_path / "status"

    result = runner.invoke(
        app,
        [
            "crypto-perp-real-market-ticker-coverage-status",
            "--source-root",
            str(source_root),
            "--target-event-count",
            "30",
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "decision=READY_FOR_TICKER_REQUIRED_SAMPLE" in result.stdout
    assert "coverage_passed=true" in result.stdout
    assert "diagnosis=READY_FOR_TICKER_REQUIRED_SAMPLE" in result.stdout
    assert "coverage_shortfall=0" in result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "profit_proven=false" in result.stdout
    payload = json.loads((out / "ticker_coverage_status.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crypto_perp_real_market_ticker_coverage_status.v1"
    assert payload["coverage_passed"] is True
    assert payload["latest_candle_ts_ms"] is not None
    assert payload["latest_matured_event_cutoff_ms"] is not None
    assert payload["matured_ticker_row_count"] >= 30
    assert (out / "ticker_coverage_status.md").exists()
