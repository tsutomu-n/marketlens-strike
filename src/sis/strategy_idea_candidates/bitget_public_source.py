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
    normalize_mix_contracts,
    normalize_mix_history_candles,
    normalize_mix_tickers,
)
from sis.crypto_perp.bitget.public_api import BitgetPublicAPI
from sis.strategy_inputs.io import write_json_artifact


BITGET_PUBLIC_SOURCE_SCHEMA_VERSION = "strategy_idea_candidates_bitget_public_source.v1"
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
]


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
    for symbol in symbols:
        candles_by_symbol[symbol] = await _fetch_recent_candles(
            api=api,
            symbol=symbol,
            product_type=product_type,
            granularity=granularity,
            limit=limit,
            now=now,
        )

    row_counts = _write_source_root(
        source_root=source_root,
        run_id=_run_id(now),
        generated_at_ms=_datetime_ms(now),
        product_type=product_type,
        contracts=contracts,
        tickers=tickers,
        candles_by_symbol=candles_by_symbol,
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


def _write_source_root(
    *,
    source_root: Path,
    run_id: str,
    generated_at_ms: int,
    product_type: str,
    contracts: list[dict[str, Any]],
    tickers: list[dict[str, Any]],
    candles_by_symbol: dict[str, list[dict[str, Any]]],
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
    _write_candles_parquet(data_dir / "candles_5m", candle_rows)
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
        "candles_5m": len(candle_rows),
        "scanner_rows": len(scanner_rows),
    }


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


def _write_candles_parquet(base_dir: Path, candle_rows: list[dict[str, Any]]) -> None:
    if not candle_rows:
        return
    frame = pl.DataFrame(candle_rows).with_columns(
        pl.from_epoch("ts", time_unit="ms").dt.strftime("%Y-%m-%d").alias("date")
    )
    for date, group in frame.partition_by("date", as_dict=True).items():
        date_value = date[0] if isinstance(date, tuple) else date
        out_dir = base_dir / f"date={date_value}"
        out_dir.mkdir(parents=True, exist_ok=True)
        group.drop("date").write_parquet(out_dir / "candles.parquet")


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
) -> dict[str, Any]:
    known_gaps = [
        "ORDERBOOK_DEPTH_NOT_FETCHED",
        "MEASURED_SLIPPAGE_NOT_FETCHED",
        "WEBSOCKET_NOT_FETCHED",
        "DEEP_BACKFILL_NOT_FETCHED",
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


def _prepare_output(
    *,
    out_dir: Path,
    source_root: Path,
    manifest_path: Path,
    replace_existing: bool,
) -> None:
    if not replace_existing and (manifest_path.exists() or source_root.exists()):
        raise BitgetPublicSourceOutputExistsError(f"output already exists: {out_dir}")
    if replace_existing and manifest_path.exists():
        manifest_path.unlink()
    if replace_existing:
        scanner_db = source_root / "data/scanner.duckdb"
        if scanner_db.exists():
            scanner_db.unlink()
        for path in (source_root / "data/candles_5m").glob("date=*/candles.parquet"):
            path.unlink()


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


def _bool_or_none(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None
