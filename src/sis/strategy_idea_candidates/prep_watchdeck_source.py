from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import duckdb
import polars as pl


@dataclass(frozen=True)
class PrepWatchdeckSourceRef:
    source_id: str
    path: str
    status: str
    detail: str | None = None


@dataclass(frozen=True)
class PrepWatchdeckContract:
    symbol: str
    product_type: str
    min_trade_usdt: float | None = None
    max_leverage: float | None = None


@dataclass(frozen=True)
class PrepWatchdeckTicker:
    symbol: str
    ts_ms: int
    last_price: float | None = None
    bid_price: float | None = None
    ask_price: float | None = None
    funding_rate: float | None = None
    quote_volume_24h: float | None = None


@dataclass(frozen=True)
class PrepWatchdeckBundle:
    root: Path
    symbols: list[str]
    contracts_by_symbol: dict[str, PrepWatchdeckContract] = field(default_factory=dict)
    tickers_by_symbol: dict[str, PrepWatchdeckTicker] = field(default_factory=dict)
    candles_by_symbol: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    source_quality_by_symbol: dict[str, str] = field(default_factory=dict)
    snapshot_source: dict[str, Any] = field(default_factory=dict)
    sources: list[PrepWatchdeckSourceRef] = field(default_factory=list)
    source_statuses: list[str] = field(default_factory=list)


def load_prep_watchdeck_source(root: Path, *, symbols: list[str]) -> PrepWatchdeckBundle:
    normalized_symbols = _normalize_symbols(symbols)
    contracts: dict[str, PrepWatchdeckContract] = {}
    tickers: dict[str, PrepWatchdeckTicker] = {}
    candles: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in normalized_symbols}
    quality: dict[str, str] = {}
    snapshot_source: dict[str, Any] = {}
    sources: list[PrepWatchdeckSourceRef] = []
    statuses: list[str] = []

    scanner_db = root / "data/scanner.duckdb"
    if scanner_db.exists():
        try:
            scanner = _read_scanner_duckdb(scanner_db, normalized_symbols)
        except Exception as exc:
            if _is_duckdb_lock_error(exc):
                statuses.append("SOURCE_LOCKED")
                sources.append(_source_ref("scanner.duckdb", scanner_db, "SOURCE_LOCKED", exc))
            else:
                statuses.append("SOURCE_ERROR")
                sources.append(_source_ref("scanner.duckdb", scanner_db, "SOURCE_ERROR", exc))
        else:
            contracts.update(scanner.contracts_by_symbol)
            tickers.update(scanner.tickers_by_symbol)
            _merge_candles(candles, scanner.candles_by_symbol)
            quality.update(scanner.source_quality_by_symbol)
            sources.append(_source_ref("scanner.duckdb", scanner_db, "READ"))

    parquet_dir = root / "data/candles_5m"
    if parquet_dir.exists():
        try:
            parquet_candles = _read_candles_parquet(parquet_dir, normalized_symbols)
        except Exception as exc:
            statuses.append("SOURCE_ERROR")
            sources.append(_source_ref("candles_5m_parquet", parquet_dir, "SOURCE_ERROR", exc))
        else:
            _merge_candles(candles, parquet_candles)
            sources.append(_source_ref("candles_5m_parquet", parquet_dir, "READ"))

    latest_snapshot = root / "var/snapshots/latest.json"
    if latest_snapshot.exists():
        try:
            snapshot_source, snapshot_quality = _read_latest_snapshot(latest_snapshot)
        except Exception as exc:
            statuses.append("SOURCE_ERROR")
            sources.append(
                _source_ref("latest_snapshot_json", latest_snapshot, "SOURCE_ERROR", exc)
            )
        else:
            quality.update({k: v for k, v in snapshot_quality.items() if k in normalized_symbols})
            sources.append(_source_ref("latest_snapshot_json", latest_snapshot, "READ"))

    service_db = root / "var/watchdeck.duckdb"
    if service_db.exists():
        try:
            service = _read_service_duckdb(service_db, normalized_symbols)
        except Exception as exc:
            if _is_duckdb_lock_error(exc):
                statuses.append("SOURCE_LOCKED")
                sources.append(_source_ref("watchdeck.duckdb", service_db, "SOURCE_LOCKED", exc))
            else:
                statuses.append("SOURCE_ERROR")
                sources.append(_source_ref("watchdeck.duckdb", service_db, "SOURCE_ERROR", exc))
        else:
            contracts.update(service.contracts_by_symbol)
            tickers.update(service.tickers_by_symbol)
            sources.append(_source_ref("watchdeck.duckdb", service_db, "READ"))

    candles = {
        symbol: _dedupe_sort_candles(rows)
        for symbol, rows in candles.items()
        if _dedupe_sort_candles(rows)
    }
    if any(ref.status == "READ" for ref in sources):
        statuses.append("SOURCE_AVAILABLE")
    return PrepWatchdeckBundle(
        root=root,
        symbols=normalized_symbols,
        contracts_by_symbol=contracts,
        tickers_by_symbol=tickers,
        candles_by_symbol=candles,
        source_quality_by_symbol=quality,
        snapshot_source=snapshot_source,
        sources=sources,
        source_statuses=list(dict.fromkeys(statuses)),
    )


def _read_scanner_duckdb(path: Path, symbols: list[str]) -> PrepWatchdeckBundle:
    with duckdb.connect(str(path), read_only=True) as con:
        tables = {str(row[0]) for row in con.execute("SHOW TABLES").fetchall()}
        contracts = (
            _read_scanner_contracts(con, symbols) if "contracts" in tables else {}
        )
        tickers = (
            _read_scanner_tickers(con, symbols) if "tickers_snapshot" in tables else {}
        )
        candles = _read_scanner_candles(con, symbols) if "candles_5m" in tables else {}
        quality = (
            _read_scanner_quality(con, symbols) if "scanner_rows" in tables else {}
        )
    return PrepWatchdeckBundle(
        root=path.parent,
        symbols=symbols,
        contracts_by_symbol=contracts,
        tickers_by_symbol=tickers,
        candles_by_symbol=candles,
        source_quality_by_symbol=quality,
    )


def _read_service_duckdb(path: Path, symbols: list[str]) -> PrepWatchdeckBundle:
    with duckdb.connect(str(path), read_only=True) as con:
        tables = {str(row[0]) for row in con.execute("SHOW TABLES").fetchall()}
        contracts = _read_service_contracts(con, symbols) if "instruments" in tables else {}
        tickers = _read_service_tickers(con, symbols) if "ticker_latest" in tables else {}
    return PrepWatchdeckBundle(
        root=path.parent,
        symbols=symbols,
        contracts_by_symbol=contracts,
        tickers_by_symbol=tickers,
    )


def _read_scanner_contracts(
    con: duckdb.DuckDBPyConnection, symbols: list[str]
) -> dict[str, PrepWatchdeckContract]:
    rows = con.execute(
        f"""
        SELECT symbol, product_type, min_trade_usdt, max_lever
        FROM contracts
        WHERE symbol IN ({_placeholders(symbols)})
        """,
        symbols,
    ).fetchall()
    return {
        str(row[0]).upper(): PrepWatchdeckContract(
            symbol=str(row[0]).upper(),
            product_type=str(row[1]),
            min_trade_usdt=_float_or_none(row[2]),
            max_leverage=_float_or_none(row[3]),
        )
        for row in rows
    }


def _read_service_contracts(
    con: duckdb.DuckDBPyConnection, symbols: list[str]
) -> dict[str, PrepWatchdeckContract]:
    rows = con.execute(
        f"""
        SELECT symbol, product_type, min_trade_num, max_leverage
        FROM instruments
        WHERE symbol IN ({_placeholders(symbols)})
        """,
        symbols,
    ).fetchall()
    return {
        str(row[0]).upper(): PrepWatchdeckContract(
            symbol=str(row[0]).upper(),
            product_type=str(row[1]),
            min_trade_usdt=_float_or_none(row[2]),
            max_leverage=_float_or_none(row[3]),
        )
        for row in rows
    }


def _read_scanner_tickers(
    con: duckdb.DuckDBPyConnection, symbols: list[str]
) -> dict[str, PrepWatchdeckTicker]:
    rows = con.execute(
        f"""
        SELECT symbol, ts, last_price, funding_rate, usdt_volume_24h
        FROM (
          SELECT *,
                 ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
          FROM tickers_snapshot
          WHERE symbol IN ({_placeholders(symbols)})
        )
        WHERE rn = 1
        """,
        symbols,
    ).fetchall()
    return {
        str(row[0]).upper(): PrepWatchdeckTicker(
            symbol=str(row[0]).upper(),
            ts_ms=int(row[1]),
            last_price=_float_or_none(row[2]),
            funding_rate=_float_or_none(row[3]),
            quote_volume_24h=_float_or_none(row[4]),
        )
        for row in rows
    }


def _read_service_tickers(
    con: duckdb.DuckDBPyConnection, symbols: list[str]
) -> dict[str, PrepWatchdeckTicker]:
    rows = con.execute(
        f"""
        SELECT symbol, ts_ms, last_price, bid_price, ask_price, funding_rate, quote_volume_24h
        FROM ticker_latest
        WHERE symbol IN ({_placeholders(symbols)})
        """,
        symbols,
    ).fetchall()
    return {
        str(row[0]).upper(): PrepWatchdeckTicker(
            symbol=str(row[0]).upper(),
            ts_ms=int(row[1]),
            last_price=_float_or_none(row[2]),
            bid_price=_float_or_none(row[3]),
            ask_price=_float_or_none(row[4]),
            funding_rate=_float_or_none(row[5]),
            quote_volume_24h=_float_or_none(row[6]),
        )
        for row in rows
    }


def _read_scanner_candles(
    con: duckdb.DuckDBPyConnection, symbols: list[str]
) -> dict[str, list[dict[str, Any]]]:
    rows = con.execute(
        f"""
        SELECT symbol, ts, open, high, low, close, base_vol, quote_vol
        FROM candles_5m
        WHERE symbol IN ({_placeholders(symbols)})
        ORDER BY symbol, ts
        """,
        symbols,
    ).fetchall()
    candles: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    for row in rows:
        candles.setdefault(str(row[0]).upper(), []).append(_candle_row(row))
    return candles


def _read_scanner_quality(
    con: duckdb.DuckDBPyConnection, symbols: list[str]
) -> dict[str, str]:
    rows = con.execute(
        f"""
        SELECT symbol, row_json::VARCHAR
        FROM (
          SELECT *,
                 ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
          FROM scanner_rows
          WHERE symbol IN ({_placeholders(symbols)})
        )
        WHERE rn = 1
        """,
        symbols,
    ).fetchall()
    result: dict[str, str] = {}
    for symbol, raw_json in rows:
        try:
            payload = json.loads(str(raw_json))
        except json.JSONDecodeError:
            continue
        quality = payload.get("data_quality")
        if quality is not None:
            result[str(symbol).upper()] = str(quality)
    return result


def _read_candles_parquet(base_dir: Path, symbols: list[str]) -> dict[str, list[dict[str, Any]]]:
    paths = sorted(base_dir.glob("date=*/candles.parquet"))
    candles: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    if not paths:
        return candles
    symbol_set = set(symbols)
    for path in paths:
        frame = pl.read_parquet(path)
        if "symbol" not in frame.columns:
            continue
        frame = frame.filter(pl.col("symbol").str.to_uppercase().is_in(symbols))
        for row in frame.to_dicts():
            symbol = str(row["symbol"]).upper()
            if symbol not in symbol_set:
                continue
            candles.setdefault(symbol, []).append(
                {
                    "symbol": symbol,
                    "ts": int(row["ts"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "base_vol": float(row.get("base_vol") or 0.0),
                    "quote_vol": float(row.get("quote_vol") or 0.0),
                }
            )
    return candles


def _read_latest_snapshot(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    source = payload.get("source") if isinstance(payload, dict) else {}
    rows = payload.get("rows") if isinstance(payload, dict) else []
    quality: dict[str, str] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = row.get("symbol")
            data_quality = row.get("data_quality") or row.get("dataQuality")
            if symbol and data_quality:
                quality[str(symbol).upper()] = str(data_quality)
    return dict(source) if isinstance(source, dict) else {}, quality


def _source_ref(
    source_id: str, path: Path, status: str, exc: Exception | None = None
) -> PrepWatchdeckSourceRef:
    return PrepWatchdeckSourceRef(
        source_id=source_id,
        path=path.as_posix(),
        status=status,
        detail=str(exc) if exc is not None else None,
    )


def _normalize_symbols(symbols: list[str]) -> list[str]:
    return sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})


def _placeholders(values: list[str]) -> str:
    if not values:
        return "NULL"
    return ", ".join("?" for _item in values)


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    return float(value)


def _candle_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "symbol": str(row[0]).upper(),
        "ts": int(row[1]),
        "open": float(row[2]),
        "high": float(row[3]),
        "low": float(row[4]),
        "close": float(row[5]),
        "base_vol": float(row[6] or 0.0),
        "quote_vol": float(row[7] or 0.0),
    }


def _merge_candles(
    target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]
) -> None:
    for symbol, rows in source.items():
        target.setdefault(symbol, []).extend(rows)


def _dedupe_sort_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_ts = {int(row["ts"]): row for row in rows}
    return [by_ts[ts] for ts in sorted(by_ts)]


def _is_duckdb_lock_error(exc: Exception) -> bool:
    return "Could not set lock on file" in str(exc)
