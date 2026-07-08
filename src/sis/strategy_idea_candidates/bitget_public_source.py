from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import duckdb
import httpx
import polars as pl

from sis.crypto_perp.bitget.client import BitgetPublicClient, BitgetPublicClientConfig
from sis.crypto_perp.bitget.normalizers import (
    normalize_funding_history,
    normalize_mix_contracts,
    normalize_mix_history_candles,
    normalize_mix_tickers,
)
from sis.crypto_perp.bitget.public_api import BitgetPublicAPI
from sis.crypto_perp.funding_source import FUNDING_MANIFEST_SCHEMA_VERSION
from sis.strategy_inputs.io import write_json_artifact


BITGET_PUBLIC_SOURCE_SCHEMA_VERSION = "strategy_idea_candidates_bitget_public_source.v1"
TICKER_MANIFEST_SCHEMA_VERSION = "crypto_perp_ticker_manifest.v1"
BITGET_PUBLIC_BASE_URL = "https://api.bitget.com"
BITGET_HISTORY_CANDLES_LIMIT = 200
SUPPORTED_PRODUCT_TYPE = "USDT-FUTURES"
SUPPORTED_GRANULARITY = "5m"
PUBLIC_NETWORK_ENV_VAR = "SIS_ALLOW_PUBLIC_NETWORK"
GRANULARITY_MS = {SUPPORTED_GRANULARITY: 300_000}
SOURCE_ENDPOINT_IDS = [
    "bitget.mix.market.contracts",
    "bitget.mix.market.tickers",
    "bitget.mix.market.history_candles",
    "funding_history",
]
CURRENT_TICKER_SNAPSHOT_ONLY_GAP = "CURRENT_TICKER_SNAPSHOT_ONLY"
HISTORICAL_BID_ASK_TICKER_NOT_AVAILABLE_GAP = (
    "HISTORICAL_BID_ASK_TICKER_NOT_AVAILABLE_FROM_BITGET_PUBLIC_REST"
)
PRICE_CANDLES_NOT_BID_ASK_TICKER_GAP = "PRICE_MARK_INDEX_CANDLES_NOT_BID_ASK_TICKER_COVERAGE"


class BitgetPublicSourceRefreshError(ValueError):
    pass


class BitgetPublicSourceNetworkOptInError(BitgetPublicSourceRefreshError):
    pass


class BitgetPublicSourceOutputExistsError(BitgetPublicSourceRefreshError):
    pass


@dataclass(frozen=True)
class BitgetPublicSourceRefreshResult:
    source_root: Path
    manifest_path: Path
    manifest: dict[str, Any]


def refresh_bitget_public_source(
    *,
    symbols: list[str],
    out_dir: Path,
    product_type: str = SUPPORTED_PRODUCT_TYPE,
    granularity: str = SUPPORTED_GRANULARITY,
    limit: int = BITGET_HISTORY_CANDLES_LIMIT,
    network: bool = False,
    replace_existing: bool = False,
    append_existing: bool = False,
    base_url: str = BITGET_PUBLIC_BASE_URL,
    transport: httpx.AsyncBaseTransport | None = None,
    now: datetime | None = None,
) -> BitgetPublicSourceRefreshResult:
    if not _network_allowed(network):
        raise BitgetPublicSourceNetworkOptInError("public_network_opt_in_required")
    normalized_symbols = _normalize_symbols(symbols)
    _validate_request(
        symbols=normalized_symbols,
        product_type=product_type,
        granularity=granularity,
        limit=limit,
    )
    timestamp = _utc_now(now)
    source_root = out_dir / "source_root"
    manifest_path = out_dir / "bitget_public_source_refresh_manifest.json"
    _prepare_output(
        out_dir=out_dir,
        source_root=source_root,
        manifest_path=manifest_path,
        replace_existing=replace_existing,
        append_existing=append_existing,
    )
    return asyncio.run(
        _refresh_async(
            symbols=normalized_symbols,
            product_type=product_type,
            granularity=granularity,
            limit=limit,
            source_root=source_root,
            manifest_path=manifest_path,
            base_url=base_url,
            transport=transport,
            now=timestamp,
            append_existing=append_existing,
        )
    )


async def _refresh_async(
    *,
    symbols: list[str],
    product_type: str,
    granularity: str,
    limit: int,
    source_root: Path,
    manifest_path: Path,
    base_url: str,
    transport: httpx.AsyncBaseTransport | None,
    now: datetime,
    append_existing: bool,
) -> BitgetPublicSourceRefreshResult:
    client = BitgetPublicClient(BitgetPublicClientConfig(base_url=base_url, transport=transport))
    api = BitgetPublicAPI(client, category=product_type)
    contracts_result, tickers_result = await asyncio.gather(
        api.mix_contracts(product_type=product_type),
        api.mix_tickers(product_type=product_type),
    )
    contracts = _filter_by_symbol(
        normalize_mix_contracts(contracts_result.payload, product_type=product_type),
        symbols,
    )
    tickers = _filter_by_symbol(normalize_mix_tickers(tickers_result.payload), symbols)
    candles_by_symbol: dict[str, list[dict[str, Any]]] = {}
    funding_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        candles_by_symbol[symbol] = await _fetch_recent_candles(
            api=api,
            symbol=symbol,
            product_type=product_type,
            granularity=granularity,
            limit=limit,
            now=now,
        )
        funding_by_symbol[symbol] = await _fetch_funding_history(api=api, symbol=symbol)

    row_counts = _write_source_root(
        source_root=source_root,
        run_id=_run_id(now),
        generated_at_ms=_datetime_ms(now),
        product_type=product_type,
        contracts=contracts,
        tickers=tickers,
        candles_by_symbol=candles_by_symbol,
        funding_by_symbol=funding_by_symbol,
        append_existing=append_existing,
    )
    manifest = _manifest(
        source_root=source_root,
        run_id=_run_id(now),
        created_at=now,
        symbols=symbols,
        product_type=product_type,
        granularity=granularity,
        limit=limit,
        row_counts=row_counts,
        candles_by_symbol=candles_by_symbol,
        contracts=contracts,
        tickers=tickers,
        funding_by_symbol=funding_by_symbol,
    )
    write_json_artifact(manifest_path, manifest)
    return BitgetPublicSourceRefreshResult(
        source_root=source_root,
        manifest_path=manifest_path,
        manifest=manifest,
    )


async def _fetch_recent_candles(
    *,
    api: BitgetPublicAPI,
    symbol: str,
    product_type: str,
    granularity: str,
    limit: int,
    now: datetime,
) -> list[dict[str, Any]]:
    granularity_ms = GRANULARITY_MS[granularity]
    current_bucket_ms = _datetime_ms(now) // granularity_ms * granularity_ms
    end_ms = current_bucket_ms
    max_attempts = max(
        1,
        (limit + BITGET_HISTORY_CANDLES_LIMIT - 1) // BITGET_HISTORY_CANDLES_LIMIT + 2,
    )
    attempts = 0
    rows_by_ts: dict[int, dict[str, Any]] = {}
    while len(rows_by_ts) < limit and attempts < max_attempts:
        attempts += 1
        request_limit = min(BITGET_HISTORY_CANDLES_LIMIT, limit - len(rows_by_ts))
        start_ms = end_ms - granularity_ms * request_limit
        result = await api.mix_history_candles(
            symbol=symbol,
            product_type=product_type,
            granularity=granularity,
            start_ms=start_ms,
            end_ms=end_ms,
            limit=request_limit,
        )
        chunk = normalize_mix_history_candles(
            result.payload,
            symbol=symbol,
            granularity=granularity,
        )
        if not chunk:
            break
        for row in chunk:
            ts_ms = int(row["ts"])
            if ts_ms >= current_bucket_ms or ts_ms >= end_ms:
                continue
            rows_by_ts[ts_ms] = _candle_output_row(row)
        oldest_ts = min(int(row["ts"]) for row in chunk)
        if oldest_ts >= end_ms:
            break
        end_ms = oldest_ts
    return [rows_by_ts[ts] for ts in sorted(rows_by_ts)[-limit:]]


async def _fetch_funding_history(
    *,
    api: BitgetPublicAPI,
    symbol: str,
) -> list[dict[str, Any]]:
    result = await api.funding_history(symbol=symbol, limit=100)
    rows = normalize_funding_history(result.payload)
    return [row for row in rows if str(row.get("native_symbol", "")).upper() == symbol.upper()]


def _write_source_root(
    *,
    source_root: Path,
    run_id: str,
    generated_at_ms: int,
    product_type: str,
    contracts: list[dict[str, Any]],
    tickers: list[dict[str, Any]],
    candles_by_symbol: dict[str, list[dict[str, Any]]],
    funding_by_symbol: dict[str, list[dict[str, Any]]],
    append_existing: bool = False,
) -> dict[str, int]:
    data_dir = source_root / "data"
    snapshot_dir = source_root / "var/snapshots"
    data_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    candle_rows = [row for rows in candles_by_symbol.values() for row in rows]
    scanner_rows = _scanner_rows(run_id=run_id, candles_by_symbol=candles_by_symbol)
    _write_scanner_duckdb(
        data_dir / "scanner.duckdb",
        run_id=run_id,
        generated_at_ms=generated_at_ms,
        contracts=contracts,
        tickers=tickers,
        candle_rows=candle_rows,
        scanner_rows=scanner_rows,
    )
    candle_rows = _write_candles_parquet(
        data_dir / "candles_5m", candle_rows, append_existing=append_existing
    )
    ticker_rows = _ticker_rows(
        run_id=run_id,
        generated_at_ms=generated_at_ms,
        product_type=product_type,
        tickers=tickers,
    )
    ticker_rows = _write_ticker_rows_parquet(
        data_dir / "ticker_rows", ticker_rows, append_existing=append_existing
    )
    _write_ticker_manifest(
        data_dir / "ticker_manifest.json",
        run_id=run_id,
        generated_at_ms=generated_at_ms,
        product_type=product_type,
        ticker_rows=ticker_rows,
    )
    funding_rows = _funding_rows(
        run_id=run_id,
        product_type=product_type,
        funding_by_symbol=funding_by_symbol,
    )
    funding_rows = _write_funding_rows_parquet(
        data_dir / "funding_rows", funding_rows, append_existing=append_existing
    )
    _write_funding_manifest(
        data_dir / "funding_manifest.json",
        run_id=run_id,
        generated_at_ms=generated_at_ms,
        product_type=product_type,
        funding_rows=funding_rows,
    )
    _write_latest_snapshot(
        snapshot_dir / "latest.json",
        run_id=run_id,
        generated_at_ms=generated_at_ms,
        product_type=product_type,
        tickers=tickers,
        candles_by_symbol=candles_by_symbol,
    )
    return {
        "contracts": len(contracts),
        "tickers_snapshot": len(tickers),
        "ticker_rows": len(ticker_rows),
        "funding_rows": len(funding_rows),
        "candles_5m": len(candle_rows),
        "scanner_rows": len(scanner_rows),
    }


def _ticker_rows(
    *,
    run_id: str,
    generated_at_ms: int,
    product_type: str,
    tickers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        bid_px = _float_or_none(ticker.get("bid_price"))
        ask_px = _float_or_none(ticker.get("ask_price"))
        mid_px = (bid_px + ask_px) / 2 if bid_px is not None and ask_px is not None else None
        symbol = str(ticker["symbol"]).upper()
        rows.append(
            {
                "exchange": "bitget",
                "market_type": "perp_linear" if product_type == "USDT-FUTURES" else product_type,
                "symbol_native": symbol,
                "symbol_canonical": symbol,
                "ts_exchange_ms": _int_or_default(ticker.get("ts"), generated_at_ms),
                "ts_received_ms": generated_at_ms,
                "source_channel": "rest_ticker",
                "last_px": _float_or_none(ticker.get("last_price")),
                "bid_px": bid_px,
                "ask_px": ask_px,
                "bid_sz": _float_or_none(ticker.get("bid_size")),
                "ask_sz": _float_or_none(ticker.get("ask_size")),
                "mid_px": mid_px,
                "mark_px": _float_or_none(ticker.get("mark_price")),
                "index_px": _float_or_none(ticker.get("index_price")),
                "funding_rate": _float_or_none(ticker.get("funding_rate")),
                "next_funding_time_ms": _int_or_none(ticker.get("next_funding_time_ms")),
                "open_interest": _float_or_none(ticker.get("holding_amount")),
                "volume_24h_base": _float_or_none(ticker.get("base_volume_24h")),
                "volume_24h_quote": _float_or_none(ticker.get("usdt_volume_24h"))
                or _float_or_none(ticker.get("quote_volume_24h")),
                "coverage_class": "native",
                "is_snapshot": True,
                "raw_ref": "bitget.mix.market.tickers",
                "ingested_at_ms": generated_at_ms,
                "run_id": run_id,
            }
        )
    return rows


def _write_ticker_rows_parquet(
    base_dir: Path, ticker_rows: list[dict[str, Any]], *, append_existing: bool = False
) -> list[dict[str, Any]]:
    rows = [
        *_existing_parquet_rows(base_dir.glob("exchange=*/symbol=*/date=*/ticker_rows.parquet"))
    ]
    if not append_existing:
        rows = []
    rows = _dedupe_ticker_rows([*rows, *ticker_rows])
    if not rows:
        return []
    frame = pl.DataFrame(rows).with_columns(
        pl.from_epoch("ts_exchange_ms", time_unit="ms").dt.strftime("%Y-%m-%d").alias("date")
    )
    for keys, group in frame.partition_by(
        ["exchange", "symbol_canonical", "date"],
        as_dict=True,
    ).items():
        exchange, symbol, date = keys
        out_dir = base_dir / f"exchange={exchange}" / f"symbol={symbol}" / f"date={date}"
        out_dir.mkdir(parents=True, exist_ok=True)
        group.drop("date").write_parquet(out_dir / "ticker_rows.parquet")
    return rows


def _write_ticker_manifest(
    path: Path,
    *,
    run_id: str,
    generated_at_ms: int,
    product_type: str,
    ticker_rows: list[dict[str, Any]],
) -> None:
    fields_present = _fields_present(ticker_rows)
    supports_edge_action = {"bid_px", "ask_px"}.issubset(fields_present)
    supports_cost_adjusted_estimate = {
        "last_px",
        "bid_px",
        "ask_px",
        "funding_rate",
    }.issubset(fields_present)
    timestamp_values = [int(row["ts_exchange_ms"]) for row in ticker_rows]
    write_json_artifact(
        path,
        {
            "schema_version": TICKER_MANIFEST_SCHEMA_VERSION,
            "manifest_id": f"{run_id}-bitget-ticker-rows",
            "created_at": _serialize_datetime(
                datetime.fromtimestamp(generated_at_ms / 1000, tz=timezone.utc)
            ),
            "artifact": "ticker_rows",
            "version": 1,
            "exchange": "bitget",
            "market_type": "perp_linear" if product_type == "USDT-FUTURES" else product_type,
            "symbols": sorted({str(row["symbol_canonical"]) for row in ticker_rows}),
            "capture_mode": "rest_ticker",
            "coverage_class": "native" if ticker_rows else "absent",
            "supports_cost_adjusted_estimate": bool(
                ticker_rows and supports_cost_adjusted_estimate
            ),
            "supports_edge_action": bool(ticker_rows and supports_edge_action),
            "window": {
                "start_ms": min(timestamp_values) if timestamp_values else None,
                "end_ms": max(timestamp_values) if timestamp_values else None,
            },
            "row_count_total": len(ticker_rows),
            "row_count_after_dedupe": len(_dedupe_ticker_rows(ticker_rows)),
            "fields_present": sorted(fields_present),
            "warnings": _ticker_manifest_warnings(ticker_rows, fields_present),
            "raw_inputs": ["bitget.mix.market.tickers"],
            "network_attempted": True,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
    )


def _fields_present(rows: list[dict[str, Any]]) -> set[str]:
    candidate_fields = {
        "last_px",
        "bid_px",
        "ask_px",
        "bid_sz",
        "ask_sz",
        "mid_px",
        "mark_px",
        "index_px",
        "funding_rate",
        "next_funding_time_ms",
        "open_interest",
        "volume_24h_base",
        "volume_24h_quote",
    }
    return {field for field in candidate_fields if any(row.get(field) is not None for row in rows)}


def _dedupe_ticker_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row["exchange"]),
            str(row["symbol_canonical"]),
            _int_or_default(
                row.get("ts_received_ms"), _int_or_default(row.get("ts_exchange_ms"), 0)
            ),
            str(row["source_channel"]),
        )
        deduped[key] = row
    return sorted(
        deduped.values(),
        key=lambda row: (
            str(row["exchange"]),
            str(row["symbol_canonical"]),
            _int_or_default(row.get("ts_received_ms"), 0),
            _int_or_default(row.get("ts_exchange_ms"), 0),
            str(row["source_channel"]),
        ),
    )


def _ticker_manifest_warnings(rows: list[dict[str, Any]], fields_present: set[str]) -> list[str]:
    warnings: list[str] = []
    if rows and any(row.get("is_snapshot") is True for row in rows):
        warnings.append(CURRENT_TICKER_SNAPSHOT_ONLY_GAP)
    if rows:
        warnings.append(HISTORICAL_BID_ASK_TICKER_NOT_AVAILABLE_GAP)
    if rows and not {"bid_px", "ask_px"}.issubset(fields_present):
        warnings.append("BID_ASK_MISSING")
    if rows and "funding_rate" not in fields_present:
        warnings.append("FUNDING_RATE_MISSING")
    if not rows:
        warnings.append("TICKER_ROWS_EMPTY")
    return warnings


def _funding_rows(
    *,
    run_id: str,
    product_type: str,
    funding_by_symbol: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, symbol_rows in funding_by_symbol.items():
        for row in symbol_rows:
            funding_rate = _float_or_none(row.get("funding_rate"))
            funding_time_ms = _int_or_none(row.get("ts_event"))
            if funding_rate is None or funding_time_ms is None:
                continue
            rows.append(
                {
                    "exchange": "bitget",
                    "market_type": "perp_linear"
                    if product_type == "USDT-FUTURES"
                    else product_type,
                    "symbol_native": str(row.get("native_symbol") or symbol).upper(),
                    "symbol_canonical": symbol.upper(),
                    "funding_time_ms": funding_time_ms,
                    "available_at_ms": funding_time_ms,
                    "funding_rate": funding_rate,
                    "source_channel": "rest_funding_history",
                    "coverage_class": "historical_public_funding",
                    "raw_ref": "funding_history",
                    "run_id": run_id,
                }
            )
    return _dedupe_funding_rows(rows)


def _write_funding_rows_parquet(
    base_dir: Path, funding_rows: list[dict[str, Any]], *, append_existing: bool = False
) -> list[dict[str, Any]]:
    rows = [
        *_existing_parquet_rows(base_dir.glob("exchange=*/symbol=*/date=*/funding_rows.parquet"))
    ]
    if not append_existing:
        rows = []
    rows = _dedupe_funding_rows([*rows, *funding_rows])
    if not rows:
        return []
    frame = pl.DataFrame(rows).with_columns(
        pl.from_epoch("funding_time_ms", time_unit="ms").dt.strftime("%Y-%m-%d").alias("date")
    )
    for keys, group in frame.partition_by(
        ["exchange", "symbol_canonical", "date"],
        as_dict=True,
    ).items():
        exchange, symbol, date = keys
        out_dir = base_dir / f"exchange={exchange}" / f"symbol={symbol}" / f"date={date}"
        out_dir.mkdir(parents=True, exist_ok=True)
        group.drop("date").write_parquet(out_dir / "funding_rows.parquet")
    return rows


def _write_funding_manifest(
    path: Path,
    *,
    run_id: str,
    generated_at_ms: int,
    product_type: str,
    funding_rows: list[dict[str, Any]],
) -> None:
    timestamp_values = [int(row["funding_time_ms"]) for row in funding_rows]
    write_json_artifact(
        path,
        {
            "schema_version": FUNDING_MANIFEST_SCHEMA_VERSION,
            "manifest_id": f"{run_id}-bitget-funding-rows",
            "created_at": _serialize_datetime(
                datetime.fromtimestamp(generated_at_ms / 1000, tz=timezone.utc)
            ),
            "artifact": "funding_rows",
            "version": 1,
            "exchange": "bitget",
            "market_type": "perp_linear" if product_type == "USDT-FUTURES" else product_type,
            "symbols": sorted({str(row["symbol_canonical"]) for row in funding_rows}),
            "capture_mode": "rest_funding_history",
            "coverage_class": "historical_public_funding" if funding_rows else "absent",
            "supports_cost_adjusted_estimate": bool(funding_rows),
            "window": {
                "start_ms": min(timestamp_values) if timestamp_values else None,
                "end_ms": max(timestamp_values) if timestamp_values else None,
            },
            "row_count_total": len(funding_rows),
            "row_count_after_dedupe": len(_dedupe_funding_rows(funding_rows)),
            "fields_present": ["funding_rate"] if funding_rows else [],
            "warnings": [] if funding_rows else ["FUNDING_ROWS_EMPTY"],
            "raw_inputs": ["funding_history"],
            "network_attempted": True,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
    )


def _dedupe_funding_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row["exchange"]),
            str(row["symbol_canonical"]),
            int(row["funding_time_ms"]),
        )
        deduped[key] = row
    return list(deduped.values())


def _write_scanner_duckdb(
    path: Path,
    *,
    run_id: str,
    generated_at_ms: int,
    contracts: list[dict[str, Any]],
    tickers: list[dict[str, Any]],
    candle_rows: list[dict[str, Any]],
    scanner_rows: list[dict[str, Any]],
) -> None:
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    try:
        con.execute(
            """
            CREATE TABLE contracts (
              symbol TEXT,
              product_type TEXT,
              base_coin TEXT,
              quote_coin TEXT,
              symbol_type TEXT,
              symbol_status TEXT,
              min_trade_usdt DOUBLE,
              max_lever DOUBLE,
              is_rwa BOOLEAN,
              updated_at_ms BIGINT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE tickers_snapshot (
              run_id TEXT,
              symbol TEXT,
              ts BIGINT,
              last_price DOUBLE,
              change_24h DOUBLE,
              usdt_volume_24h DOUBLE,
              funding_rate DOUBLE,
              holding_amount DOUBLE
            )
            """
        )
        con.execute(
            """
            CREATE TABLE candles_5m (
              symbol TEXT,
              ts BIGINT,
              open DOUBLE,
              high DOUBLE,
              low DOUBLE,
              close DOUBLE,
              base_vol DOUBLE,
              quote_vol DOUBLE
            )
            """
        )
        con.execute(
            """
            CREATE TABLE scanner_rows (
              run_id TEXT,
              symbol TEXT,
              ts BIGINT,
              category TEXT,
              direction TEXT,
              label TEXT,
              priority_score DOUBLE,
              row_json JSON
            )
            """
        )
        if contracts:
            con.executemany(
                "INSERT INTO contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        str(row["symbol"]).upper(),
                        row.get("product_type"),
                        row.get("base_coin"),
                        row.get("quote_coin"),
                        row.get("symbol_type"),
                        row.get("symbol_status"),
                        _float_or_none(row.get("min_trade_usdt")),
                        _float_or_none(row.get("max_lever")),
                        _bool_or_none(row.get("is_rwa")),
                        generated_at_ms,
                    )
                    for row in contracts
                ],
            )
        if tickers:
            con.executemany(
                "INSERT INTO tickers_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        str(row["symbol"]).upper(),
                        _int_or_default(row.get("ts"), generated_at_ms),
                        _float_or_none(row.get("last_price")),
                        _float_or_none(row.get("change_24h")),
                        _float_or_none(row.get("usdt_volume_24h")),
                        _float_or_none(row.get("funding_rate")),
                        _float_or_none(row.get("holding_amount")),
                    )
                    for row in tickers
                ],
            )
        if candle_rows:
            con.executemany(
                "INSERT INTO candles_5m VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row["symbol"],
                        row["ts"],
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["base_vol"],
                        row["quote_vol"],
                    )
                    for row in candle_rows
                ],
            )
        if scanner_rows:
            con.executemany(
                "INSERT INTO scanner_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?::JSON)",
                [
                    (
                        row["run_id"],
                        row["symbol"],
                        row["ts"],
                        row["category"],
                        row["direction"],
                        row["label"],
                        row["priority_score"],
                        row["row_json"],
                    )
                    for row in scanner_rows
                ],
            )
    finally:
        con.close()


def _write_candles_parquet(
    base_dir: Path, candle_rows: list[dict[str, Any]], *, append_existing: bool = False
) -> list[dict[str, Any]]:
    rows = [*_existing_parquet_rows(base_dir.glob("date=*/candles.parquet"))]
    if not append_existing:
        rows = []
    rows = _dedupe_candle_rows([*rows, *candle_rows])
    if not rows:
        return []
    frame = pl.DataFrame(rows).with_columns(
        pl.from_epoch("ts", time_unit="ms").dt.strftime("%Y-%m-%d").alias("date")
    )
    for date, group in frame.partition_by("date", as_dict=True).items():
        date_value = date[0] if isinstance(date, tuple) else date
        out_dir = base_dir / f"date={date_value}"
        out_dir.mkdir(parents=True, exist_ok=True)
        group.drop("date").write_parquet(out_dir / "candles.parquet")
    return rows


def _write_latest_snapshot(
    path: Path,
    *,
    run_id: str,
    generated_at_ms: int,
    product_type: str,
    tickers: list[dict[str, Any]],
    candles_by_symbol: dict[str, list[dict[str, Any]]],
) -> None:
    ticker_by_symbol = {str(row["symbol"]).upper(): row for row in tickers}
    rows: list[dict[str, Any]] = []
    for symbol, candles in candles_by_symbol.items():
        latest = candles[-1] if candles else None
        ticker = ticker_by_symbol.get(symbol, {})
        rows.append(
            {
                "symbol": symbol,
                "ts": latest["ts"] if latest is not None else generated_at_ms,
                "close": str(latest["close"] if latest is not None else ticker.get("last_price")),
                "last_price": _float_or_none(ticker.get("last_price")),
                "funding_rate": _float_or_none(ticker.get("funding_rate")),
                "data_quality": "OK" if latest is not None else "MISSING",
            }
        )
    write_json_artifact(
        path,
        {
            "schemaVersion": 1,
            "runId": run_id,
            "generatedAt": generated_at_ms,
            "dataAsOf": max((int(row["ts"]) for row in rows), default=generated_at_ms),
            "source": {
                "exchange": "bitget",
                "productType": product_type,
                "dataSource": "bitget_public_rest",
                "isFallback": False,
                "endpointIds": SOURCE_ENDPOINT_IDS,
            },
            "rows": rows,
        },
    )


def _manifest(
    *,
    source_root: Path,
    run_id: str,
    created_at: datetime,
    symbols: list[str],
    product_type: str,
    granularity: str,
    limit: int,
    row_counts: dict[str, int],
    candles_by_symbol: dict[str, list[dict[str, Any]]],
    contracts: list[dict[str, Any]],
    tickers: list[dict[str, Any]],
    funding_by_symbol: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    known_gaps = [
        "ORDERBOOK_DEPTH_NOT_FETCHED",
        "MEASURED_SLIPPAGE_NOT_FETCHED",
        "WEBSOCKET_NOT_FETCHED",
        "DEEP_BACKFILL_NOT_FETCHED",
        CURRENT_TICKER_SNAPSHOT_ONLY_GAP,
        HISTORICAL_BID_ASK_TICKER_NOT_AVAILABLE_GAP,
        PRICE_CANDLES_NOT_BID_ASK_TICKER_GAP,
        "PAPER_LIVE_PERMISSION_NOT_GRANTED",
    ]
    contract_symbols = {str(row["symbol"]).upper() for row in contracts}
    ticker_symbols = {str(row["symbol"]).upper() for row in tickers}
    for symbol in symbols:
        if symbol not in contract_symbols:
            known_gaps.append(f"CONTRACT_MISSING:{symbol}")
        if symbol not in ticker_symbols:
            known_gaps.append(f"TICKER_MISSING:{symbol}")
        if not candles_by_symbol.get(symbol):
            known_gaps.append(f"CANDLES_5M_MISSING:{symbol}")
        if not funding_by_symbol.get(symbol):
            known_gaps.append(f"FUNDING_HISTORY_MISSING:{symbol}")
    return {
        "schema_version": BITGET_PUBLIC_SOURCE_SCHEMA_VERSION,
        "manifest_id": f"{run_id}-bitget-public-source",
        "created_at": _serialize_datetime(created_at),
        "run_id": run_id,
        "source_root": source_root.as_posix(),
        "product_type": product_type,
        "granularity": granularity,
        "limit": limit,
        "symbols": symbols,
        "network_attempted": True,
        "credentials_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "source_endpoint_ids": SOURCE_ENDPOINT_IDS,
        "row_counts": row_counts,
        "time_range": _time_range(candles_by_symbol),
        "known_gaps": known_gaps,
    }


def _scanner_rows(
    *,
    run_id: str,
    candles_by_symbol: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, candles in candles_by_symbol.items():
        if not candles:
            continue
        latest = candles[-1]
        row_json = {
            "symbol": symbol,
            "ts": latest["ts"],
            "close": latest["close"],
            "category": "LOW_PRIORITY",
            "direction": "FLAT",
            "label": "source_refresh_only",
            "priority_score": 0.0,
            "data_quality": "OK",
            "source": "bitget_public_rest",
        }
        rows.append(
            {
                "run_id": run_id,
                "symbol": symbol,
                "ts": latest["ts"],
                "category": "LOW_PRIORITY",
                "direction": "FLAT",
                "label": "source_refresh_only",
                "priority_score": 0.0,
                "row_json": json.dumps(row_json, sort_keys=True),
            }
        )
    return rows


def _time_range(candles_by_symbol: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    ranges: dict[str, dict[str, int]] = {}
    for symbol, rows in candles_by_symbol.items():
        if not rows:
            continue
        values = [int(row["ts"]) for row in rows]
        ranges[symbol] = {
            "min_ts_ms": min(values),
            "max_ts_ms": max(values),
            "row_count": len(values),
        }
    return ranges


def _filter_by_symbol(
    rows: list[dict[str, Any]],
    symbols: list[str],
) -> list[dict[str, Any]]:
    symbol_set = set(symbols)
    return [row for row in rows if str(row["symbol"]).upper() in symbol_set]


def _candle_output_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "symbol": row["symbol"].upper(),
        "ts": int(row["ts"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "base_vol": float(row["base_vol"]),
        "quote_vol": float(row["quote_vol"]),
    }


def _existing_parquet_rows(paths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths):
        rows.extend(pl.read_parquet(path).to_dicts())
    return rows


def _dedupe_candle_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["symbol"]).upper(), int(row["ts"]))
        deduped[key] = {**row, "symbol": str(row["symbol"]).upper()}
    return sorted(deduped.values(), key=lambda row: (str(row["symbol"]), int(row["ts"])))


def _prepare_output(
    *,
    out_dir: Path,
    source_root: Path,
    manifest_path: Path,
    replace_existing: bool,
    append_existing: bool,
) -> None:
    if replace_existing and append_existing:
        raise BitgetPublicSourceRefreshError(
            "--append-existing and --replace-existing are mutually exclusive"
        )
    if (
        not replace_existing
        and not append_existing
        and (manifest_path.exists() or source_root.exists())
    ):
        raise BitgetPublicSourceOutputExistsError(f"output already exists: {out_dir}")
    if replace_existing and manifest_path.exists():
        manifest_path.unlink()
    if replace_existing:
        scanner_db = source_root / "data/scanner.duckdb"
        if scanner_db.exists():
            scanner_db.unlink()
        for path in (source_root / "data/candles_5m").glob("date=*/candles.parquet"):
            path.unlink()
        for path in (source_root / "data/ticker_rows").glob(
            "exchange=*/symbol=*/date=*/ticker_rows.parquet"
        ):
            path.unlink()
        ticker_manifest = source_root / "data/ticker_manifest.json"
        if ticker_manifest.exists():
            ticker_manifest.unlink()
        for path in (source_root / "data/funding_rows").glob(
            "exchange=*/symbol=*/date=*/funding_rows.parquet"
        ):
            path.unlink()
        funding_manifest = source_root / "data/funding_manifest.json"
        if funding_manifest.exists():
            funding_manifest.unlink()


def _validate_request(
    *,
    symbols: list[str],
    product_type: str,
    granularity: str,
    limit: int,
) -> None:
    if not symbols:
        raise BitgetPublicSourceRefreshError("at least one --symbol is required")
    if product_type != SUPPORTED_PRODUCT_TYPE:
        raise BitgetPublicSourceRefreshError(
            f"product_type must be {SUPPORTED_PRODUCT_TYPE}: {product_type}"
        )
    if granularity != SUPPORTED_GRANULARITY:
        raise BitgetPublicSourceRefreshError(
            f"granularity must be {SUPPORTED_GRANULARITY}: {granularity}"
        )
    if limit <= 0:
        raise BitgetPublicSourceRefreshError("limit must be positive")


def _network_allowed(network: bool) -> bool:
    return network or os.getenv(PUBLIC_NETWORK_ENV_VAR) == "1"


def _normalize_symbols(symbols: list[str]) -> list[str]:
    return sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _datetime_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _run_id(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%SZ")


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    return float(value)


def _int_or_default(value: Any, default: int) -> int:
    if value is None or isinstance(value, bool):
        return default
    return int(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    return int(value)


def _bool_or_none(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None
