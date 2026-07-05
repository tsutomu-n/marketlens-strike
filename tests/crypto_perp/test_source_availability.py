from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.pre_actual_cash import _known_gaps_by_source, _source_availability_matrix
from sis.crypto_perp.source_availability import build_source_availability
from sis.crypto_perp.ticker_source import build_ticker_source_status
from .test_event_card import _event


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _cutoff_ms(event: CryptoPerpEvent) -> int:
    return int(event.information_cutoff_at.timestamp() * 1000)


def _write_event(path: Path, event: CryptoPerpEvent) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(event.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _write_ticker_source_root(
    source_root: Path,
    *,
    rows: list[dict[str, object]],
) -> Path:
    data_dir = source_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    rows_by_path: dict[Path, list[dict[str, object]]] = {}
    for row in rows:
        exchange = str(row.get("exchange", "bitget"))
        symbol = str(row.get("symbol_canonical", "BTCUSDT")).upper()
        ts_exchange_ms = int(row["ts_exchange_ms"])
        date = datetime.fromtimestamp(ts_exchange_ms / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
        out_dir = data_dir / "ticker_rows" / f"exchange={exchange}" / f"symbol={symbol}" / (
            f"date={date}"
        )
        rows_by_path.setdefault(out_dir / "ticker_rows.parquet", []).append(row)
    for parquet_path, partition_rows in rows_by_path.items():
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(partition_rows).write_parquet(parquet_path)
    ts_exchange_values = [int(row["ts_exchange_ms"]) for row in rows]
    manifest = {
        "schema_version": "crypto_perp_ticker_manifest.v1",
        "manifest_id": "ticker-manifest-test",
        "created_at": "2026-06-21T04:00:00Z",
        "artifact": "ticker_rows",
        "version": 1,
        "exchange": "bitget",
        "market_type": "perp_linear",
        "symbols": sorted({str(row["symbol_canonical"]).upper() for row in rows}),
        "capture_mode": "rest_ticker",
        "coverage_class": "native" if rows else "absent",
        "supports_cost_adjusted_estimate": bool(rows),
        "supports_edge_action": bool(rows),
        "window": {
            "start_ms": min(ts_exchange_values) if ts_exchange_values else None,
            "end_ms": max(ts_exchange_values) if ts_exchange_values else None,
        },
        "row_count_total": len(rows),
        "row_count_after_dedupe": len(rows),
        "fields_present": ["last_px", "bid_px", "ask_px", "mark_px", "index_px", "funding_rate"],
        "warnings": [],
        "raw_inputs": ["bitget.mix.market.tickers"],
        "network_attempted": True,
        "credentials_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    (data_dir / "ticker_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return source_root


def _ticker_row(
    *,
    ts_received_ms: int,
    ts_exchange_ms: int,
    symbol_canonical: str = "BTCUSDT",
) -> dict[str, object]:
    return {
        "exchange": "bitget",
        "market_type": "perp_linear",
        "symbol_native": symbol_canonical,
        "symbol_canonical": symbol_canonical,
        "ts_exchange_ms": ts_exchange_ms,
        "ts_received_ms": ts_received_ms,
        "source_channel": "rest_ticker",
        "last_px": 100.5,
        "bid_px": 100.4,
        "ask_px": 100.6,
        "bid_sz": 1.0,
        "ask_sz": 1.2,
        "mid_px": 100.5,
        "mark_px": 100.45,
        "index_px": 100.2,
        "funding_rate": 0.0002,
        "next_funding_time_ms": ts_exchange_ms + 28_800_000,
        "open_interest": 10_000.0,
        "volume_24h_base": 500.0,
        "volume_24h_quote": 50_000.0,
        "coverage_class": "native",
        "is_snapshot": True,
        "raw_ref": "bitget.mix.market.tickers",
        "ingested_at_ms": ts_received_ms,
        "run_id": "ticker-test",
    }


def _status_by_source(artifact):
    return {status.source_id: status for status in artifact.source_statuses}


def test_source_availability_marks_missing_sources_without_zero_fill() -> None:
    event = _event()

    artifact = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"trades": 0},
    )

    assert artifact.can_compute_trade_sign_imbalance is False
    assert artifact.can_compute_ofi is False
    assert artifact.can_compute_depth is False
    assert artifact.can_compute_actual_cash is False
    assert "TRADES_ROW_COUNT_ZERO" in artifact.known_gaps
    assert "BOOKS_SOURCE_MISSING" in artifact.known_gaps
    assert "ACTUAL_CASH_SOURCE_MISSING" in artifact.known_gaps


def test_source_availability_schema_accepts_artifact() -> None:
    artifact = build_source_availability(
        event=_event(),
        created_at="2026-06-27T10:00:00Z",
        available_sources={"books": True, "trades": True, "cash_ledger": True},
        row_counts={"books": 12, "trades": 20, "cash_ledger": 1},
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_source_availability.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(artifact.model_dump(mode="json"))
    assert artifact.can_compute_depth is True
    assert artifact.can_compute_trade_sign_imbalance is True
    assert artifact.can_compute_actual_cash is True


def test_ticker_source_selects_latest_received_row_before_cutoff(tmp_path: Path) -> None:
    event = _event()
    cutoff_ms = _cutoff_ms(event)
    source_root = _write_ticker_source_root(
        tmp_path / "source_root",
        rows=[
            _ticker_row(ts_received_ms=cutoff_ms - 600_000, ts_exchange_ms=cutoff_ms - 600_000),
            _ticker_row(ts_received_ms=cutoff_ms - 120_000, ts_exchange_ms=cutoff_ms - 120_000),
        ],
    )

    ticker_status = build_ticker_source_status(
        event=event,
        source_root=source_root,
        max_staleness_seconds=900,
    )
    artifact = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"ticker": ticker_status.row_count},
        source_refs=ticker_status.source_refs,
        source_metadata={"ticker": ticker_status.metadata},
        source_reasons={"ticker": ticker_status.reason},
    )

    status = _status_by_source(artifact)["ticker"]
    assert status.available is True
    assert status.row_count == 1
    assert status.reason == "available"
    assert status.metadata["ts_received_ms"] == cutoff_ms - 120_000
    assert status.metadata["ts_exchange_ms"] == cutoff_ms - 120_000
    assert status.metadata["staleness_seconds"] == 120
    assert status.metadata["exchange"] == "bitget"
    assert status.metadata["market_type"] == "perp_linear"
    assert status.metadata["symbol_canonical"] == "BTCUSDT"
    assert status.metadata["source_channel"] == "rest_ticker"
    assert status.metadata["coverage_class"] == "native"
    assert status.metadata["selected_parquet_path"].endswith("ticker_rows.parquet")
    assert status.metadata["manifest_path"].endswith("ticker_manifest.json")
    assert {ref["schema_version"] for ref in status.source_refs} == {
        "crypto_perp_ticker_manifest.v1",
        "ticker_rows.parquet",
    }


def test_ticker_source_rejects_future_received_row_even_when_exchange_time_is_old(
    tmp_path: Path,
) -> None:
    event = _event()
    cutoff_ms = _cutoff_ms(event)
    source_root = _write_ticker_source_root(
        tmp_path / "source_root",
        rows=[
            _ticker_row(ts_received_ms=cutoff_ms + 60_000, ts_exchange_ms=cutoff_ms - 60_000),
        ],
    )

    ticker_status = build_ticker_source_status(
        event=event,
        source_root=source_root,
        max_staleness_seconds=900,
    )

    assert ticker_status.row_count == 0
    assert ticker_status.reason == "TICKER_SOURCE_MISSING_BEFORE_CUTOFF"
    assert ticker_status.metadata["manifest_path"].endswith("ticker_manifest.json")
    assert "selected_parquet_path" not in ticker_status.metadata


def test_ticker_source_rejects_stale_received_row(tmp_path: Path) -> None:
    event = _event()
    cutoff_ms = _cutoff_ms(event)
    source_root = _write_ticker_source_root(
        tmp_path / "source_root",
        rows=[
            _ticker_row(ts_received_ms=cutoff_ms - 901_000, ts_exchange_ms=cutoff_ms - 901_000),
        ],
    )

    ticker_status = build_ticker_source_status(
        event=event,
        source_root=source_root,
        max_staleness_seconds=900,
    )
    artifact = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"ticker": ticker_status.row_count},
        source_refs=ticker_status.source_refs,
        source_metadata={"ticker": ticker_status.metadata},
        source_reasons={"ticker": ticker_status.reason},
    )

    status = _status_by_source(artifact)["ticker"]
    assert status.available is False
    assert status.reason == "TICKER_SOURCE_STALE"
    assert status.metadata["staleness_seconds"] == 901
    matrix = _source_availability_matrix([artifact])
    known_gaps = _known_gaps_by_source([artifact], [])
    assert matrix["events"][0]["sources"]["ticker"]["reason"] == "TICKER_SOURCE_STALE"
    assert "TICKER_SOURCE_STALE" in known_gaps["sources"]["ticker"]["reason_codes"]


def test_ticker_funding_rate_does_not_promote_funding_source(tmp_path: Path) -> None:
    event = _event().model_copy(
        update={
            "features_at_detection": _event().features_at_detection.model_copy(
                update={"funding_rate": ""}
            )
        }
    )
    cutoff_ms = _cutoff_ms(event)
    source_root = _write_ticker_source_root(
        tmp_path / "source_root",
        rows=[
            _ticker_row(ts_received_ms=cutoff_ms - 120_000, ts_exchange_ms=cutoff_ms - 120_000),
        ],
    )

    ticker_status = build_ticker_source_status(
        event=event,
        source_root=source_root,
        max_staleness_seconds=900,
    )
    artifact = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"ticker": ticker_status.row_count},
        source_refs=ticker_status.source_refs,
        source_metadata={"ticker": ticker_status.metadata},
        source_reasons={"ticker": ticker_status.reason},
    )

    statuses = _status_by_source(artifact)
    assert statuses["ticker"].available is True
    assert statuses["funding"].available is False
    assert statuses["funding"].reason == "FUNDING_SOURCE_MISSING"
    assert artifact.can_compute_cost_adjusted_estimate is False


def test_cost_adjusted_estimate_requires_bars_ticker_and_funding_separately() -> None:
    event = _event().model_copy(
        update={
            "features_at_detection": _event().features_at_detection.model_copy(
                update={"funding_rate": ""}
            )
        }
    )

    without_funding = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"bars": 10, "ticker": 1},
    )
    with_funding = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"bars": 10, "ticker": 1, "funding": 1},
    )

    assert without_funding.can_compute_cost_adjusted_estimate is False
    assert with_funding.can_compute_cost_adjusted_estimate is True


def test_crypto_perp_source_availability_cli_reads_ticker_source_root(tmp_path: Path) -> None:
    event = _event()
    cutoff_ms = _cutoff_ms(event)
    event_path = _write_event(tmp_path / "inputs/event.json", event)
    source_root = _write_ticker_source_root(
        tmp_path / "source_root",
        rows=[
            _ticker_row(ts_received_ms=cutoff_ms - 120_000, ts_exchange_ms=cutoff_ms - 120_000),
        ],
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "crypto-perp-source-availability",
            "--event",
            str(event_path),
            "--out",
            str(out_dir),
            "--ticker-source-root",
            str(source_root),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    payload = json.loads((out_dir / "source_availability.json").read_text(encoding="utf-8"))
    statuses = {status["source_id"]: status for status in payload["source_statuses"]}
    assert statuses["ticker"]["available"] is True
    assert statuses["ticker"]["row_count"] == 1
    assert statuses["ticker"]["reason"] == "available"
    assert statuses["ticker"]["metadata"]["ts_received_ms"] == cutoff_ms - 120_000


def test_crypto_perp_source_availability_cli_help_mentions_ticker_options() -> None:
    result = runner.invoke(
        app,
        ["crypto-perp-source-availability", "--help"],
        env={"COLUMNS": "200"},
        terminal_width=200,
    )

    assert result.exit_code == 0
    assert "--ticker-source-root" in result.stdout
    assert "--ticker-max-staleness-seconds" in result.stdout
