from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import duckdb
import httpx
from jsonschema import Draft202012Validator
import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.strategy_idea_candidates.authoring_bridge import (
    build_strategy_idea_candidate_authoring_bridge,
)
from sis.strategy_idea_candidates.bitget_public_source import (
    BITGET_HISTORY_CANDLES_LIMIT,
    refresh_bitget_public_source,
)
from sis.strategy_idea_candidates.prep_watchdeck_source import load_prep_watchdeck_source
from support.cli import normalized_stdout

from .test_authoring_bridge import _candidate, _write_candidate_inputs


runner = CliRunner()
FIVE_MINUTES_MS = 300_000
REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _candle_row(ts_ms: int, index: int) -> list[str]:
    close = 100.0 + index
    return [
        str(ts_ms),
        f"{close - 1.0:.2f}",
        f"{close + 1.0:.2f}",
        f"{close - 2.0:.2f}",
        f"{close:.2f}",
        f"{10.0 + index:.2f}",
        f"{1000.0 + index:.2f}",
    ]


def _contracts_payload() -> dict[str, Any]:
    return {
        "code": "00000",
        "data": [
            {
                "symbol": "BTCUSDT",
                "productType": "USDT-FUTURES",
                "baseCoin": "BTC",
                "quoteCoin": "USDT",
                "symbolType": "perpetual",
                "symbolStatus": "normal",
                "minTradeUSDT": "5",
                "maxLever": "75",
                "isRwa": "false",
            }
        ],
    }


def _tickers_payload() -> dict[str, Any]:
    return {
        "code": "00000",
        "data": [
            {
                "symbol": "BTCUSDT",
                "ts": "1781726700000",
                "lastPr": "100.5",
                "bidPr": "100.4",
                "askPr": "100.6",
                "bidSz": "2.5",
                "askSz": "3.5",
                "change24h": "0.02",
                "baseVolume": "100",
                "quoteVolume": "10000",
                "usdtVolume": "1000000",
                "indexPrice": "100.2",
                "fundingRate": "0.0002",
                "markPrice": "100.45",
                "holdingAmount": "10",
            }
        ],
    }


def _funding_history_payload() -> dict[str, Any]:
    return {
        "code": "00000",
        "msg": "success",
        "data": {
            "resultList": [
                {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0002",
                    "fundingRateTimestamp": "1781712000000",
                },
                {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0001",
                    "fundingRateTimestamp": "1781683200000",
                },
            ]
        },
    }


def _source_transport(
    *,
    now: datetime,
    history_requests: list[httpx.Request],
    include_open_candle: bool = False,
) -> httpx.MockTransport:
    current_bucket = _utc_ms(now) // FIVE_MINUTES_MS * FIVE_MINUTES_MS

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v2/mix/market/contracts":
            return httpx.Response(200, json=_contracts_payload())
        if path == "/api/v2/mix/market/tickers":
            return httpx.Response(200, json=_tickers_payload())
        if path == "/api/v3/market/history-fund-rate":
            return httpx.Response(200, json=_funding_history_payload())
        if path == "/api/v2/mix/market/history-candles":
            history_requests.append(request)
            query = parse_qs(request.url.query.decode("ascii"))
            limit = int(query["limit"][0])
            end_ms = int(query["endTime"][0])
            start_ms = end_ms - FIVE_MINUTES_MS * limit
            rows = [
                _candle_row(start_ms + FIVE_MINUTES_MS * index, index) for index in range(limit)
            ]
            if include_open_candle:
                rows.append(_candle_row(current_bucket, 999))
            return httpx.Response(200, json={"code": "00000", "data": rows})
        return httpx.Response(404, json={"code": "404", "msg": f"unexpected {path}"})

    return httpx.MockTransport(handler)


def test_refresh_generates_prep_watchdeck_compatible_source_root(tmp_path: Path) -> None:
    now = datetime(2026, 6, 17, 12, 3, tzinfo=timezone.utc)
    history_requests: list[httpx.Request] = []

    result = refresh_bitget_public_source(
        symbols=["BTCUSDT"],
        product_type="USDT-FUTURES",
        granularity="5m",
        limit=8,
        out_dir=tmp_path / "bitget_source",
        network=True,
        transport=_source_transport(
            now=now,
            history_requests=history_requests,
            include_open_candle=True,
        ),
        now=now,
    )

    source = load_prep_watchdeck_source(result.source_root, symbols=["BTCUSDT"])
    assert source.contracts_by_symbol["BTCUSDT"].product_type == "USDT-FUTURES"
    assert source.tickers_by_symbol["BTCUSDT"].funding_rate == 0.0002
    assert len(source.candles_by_symbol["BTCUSDT"]) == 8
    assert max(row["ts"] for row in source.candles_by_symbol["BTCUSDT"]) < (
        _utc_ms(now) // FIVE_MINUTES_MS * FIVE_MINUTES_MS
    )
    assert (result.source_root / "data/scanner.duckdb").exists()
    assert list((result.source_root / "data/candles_5m").glob("date=*/candles.parquet"))
    assert (result.source_root / "var/snapshots/latest.json").exists()

    with duckdb.connect(str(result.source_root / "data/scanner.duckdb"), read_only=True) as con:
        assert {row[0] for row in con.execute("SHOW TABLES").fetchall()} >= {
            "contracts",
            "tickers_snapshot",
            "candles_5m",
            "scanner_rows",
        }

    parquet = pl.read_parquet(
        next((result.source_root / "data/candles_5m").glob("date=*/candles.parquet"))
    )
    assert parquet.height == 8

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["network_attempted"] is True
    assert manifest["credentials_used"] is False
    assert manifest["exchange_write_used"] is False
    assert "bitget.mix.market.history_candles" in manifest["source_endpoint_ids"]
    assert manifest["row_counts"]["ticker_rows"] == 1
    assert manifest["row_counts"]["funding_rows"] == 2
    assert manifest["row_counts"]["candles_5m"] == 8
    assert manifest["source_root"] == result.source_root.as_posix()
    assert "ORDERBOOK_DEPTH_NOT_FETCHED" in manifest["known_gaps"]

    ticker_manifest_path = result.source_root / "data/ticker_manifest.json"
    ticker_manifest = json.loads(ticker_manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(
        json.loads(
            (REPO_ROOT / "schemas/crypto_perp_ticker_manifest.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    ).validate(ticker_manifest)
    assert ticker_manifest["exchange"] == "bitget"
    assert ticker_manifest["coverage_class"] == "native"
    assert ticker_manifest["supports_cost_adjusted_estimate"] is True
    assert ticker_manifest["supports_edge_action"] is True
    assert ticker_manifest["row_count_after_dedupe"] == 1
    assert ticker_manifest["exchange_write_used"] is False
    assert ticker_manifest["live_order_submitted"] is False

    ticker_parquet = next(
        (result.source_root / "data/ticker_rows").glob(
            "exchange=bitget/symbol=BTCUSDT/date=*/ticker_rows.parquet"
        )
    )
    ticker_rows = pl.read_parquet(ticker_parquet)
    assert ticker_rows.height == 1
    ticker = ticker_rows.row(0, named=True)
    assert ticker["source_channel"] == "rest_ticker"
    assert ticker["coverage_class"] == "native"
    assert ticker["is_snapshot"] is True
    assert ticker["bid_px"] == 100.4
    assert ticker["ask_px"] == 100.6
    assert ticker["mid_px"] == 100.5
    assert ticker["mark_px"] == 100.45
    assert ticker["index_px"] == 100.2
    assert ticker["funding_rate"] == 0.0002

    funding_manifest_path = result.source_root / "data/funding_manifest.json"
    funding_manifest = json.loads(funding_manifest_path.read_text(encoding="utf-8"))
    assert funding_manifest["schema_version"] == "crypto_perp_funding_manifest.v1"
    assert funding_manifest["exchange"] == "bitget"
    assert funding_manifest["coverage_class"] == "historical_public_funding"
    assert funding_manifest["supports_cost_adjusted_estimate"] is True
    assert funding_manifest["row_count_after_dedupe"] == 2
    assert funding_manifest["exchange_write_used"] is False
    assert funding_manifest["live_order_submitted"] is False

    funding_parquet = next(
        (result.source_root / "data/funding_rows").glob(
            "exchange=bitget/symbol=BTCUSDT/date=*/funding_rows.parquet"
        )
    )
    funding_rows = pl.read_parquet(funding_parquet).sort("funding_time_ms")
    assert funding_rows.height == 2
    funding = funding_rows.row(-1, named=True)
    assert funding["source_channel"] == "rest_funding_history"
    assert funding["coverage_class"] == "historical_public_funding"
    assert funding["funding_time_ms"] == 1781712000000
    assert funding["available_at_ms"] == 1781712000000
    assert funding["funding_rate"] == 0.0002


def test_refresh_paginates_history_candles_beyond_single_request_limit(tmp_path: Path) -> None:
    now = datetime(2026, 6, 17, 12, 3, tzinfo=timezone.utc)
    history_requests: list[httpx.Request] = []

    result = refresh_bitget_public_source(
        symbols=["BTCUSDT"],
        product_type="USDT-FUTURES",
        granularity="5m",
        limit=BITGET_HISTORY_CANDLES_LIMIT + 5,
        out_dir=tmp_path / "bitget_source",
        network=True,
        transport=_source_transport(now=now, history_requests=history_requests),
        now=now,
    )

    source = load_prep_watchdeck_source(result.source_root, symbols=["BTCUSDT"])
    assert len(history_requests) == 2
    assert len(source.candles_by_symbol["BTCUSDT"]) == BITGET_HISTORY_CANDLES_LIMIT + 5


def test_generated_source_root_can_feed_authoring_bridge(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 6, 17, 12, 3, tzinfo=timezone.utc)
    history_requests: list[httpx.Request] = []
    source_result = refresh_bitget_public_source(
        symbols=["BTCUSDT"],
        product_type="USDT-FUTURES",
        granularity="5m",
        limit=8,
        out_dir=tmp_path / "bitget_source",
        network=True,
        transport=_source_transport(now=now, history_requests=history_requests),
        now=now,
    )
    candidate_set_path, export_manifest_path, ledger_path = _write_candidate_inputs(
        tmp_path,
        [
            _candidate("cand-001-momentum", family="perp_momentum_continuation"),
            _candidate(
                "cand-rejected", family="perp_funding_rate_carry_filter", decision="REJECTED"
            ),
        ],
    )

    bridge_result = build_strategy_idea_candidate_authoring_bridge(
        candidate_set_path=candidate_set_path,
        export_manifest_path=export_manifest_path,
        ledger_path=ledger_path,
        prep_watchdeck_root=source_result.source_root,
        out_dir=tmp_path / "bridge_out",
        replace_existing=False,
    )

    assert bridge_result.manifest.candidates[0].status == "BRIDGED"
    assert bridge_result.manifest.summary["bridged_count"] == 1


def test_bitget_source_refresh_cli_blocks_without_network_opt_in(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("SIS_ALLOW_PUBLIC_NETWORK", raising=False)
    out_dir = tmp_path / "bitget_source"

    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-bitget-source-refresh",
            "--symbol",
            "BTCUSDT",
            "--out",
            str(out_dir),
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "network_attempted=false" in stdout
    assert "status=blocked" in stdout
    assert "block_reason=public_network_opt_in_required" in stdout
    assert not out_dir.exists()


def test_bitget_source_refresh_cli_help() -> None:
    result = runner.invoke(app, ["strategy-idea-candidates-bitget-source-refresh", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--symbol" in stdout
    assert "--product-type" in stdout
    assert "--granularity" in stdout
    assert "--network" in stdout
