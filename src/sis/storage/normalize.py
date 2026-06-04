from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from sis.models import InstrumentSpec, QuoteLog
from sis.storage.jsonl_store import read_jsonl
from sis.storage.jsonl_store import write_json


QUOTE_LOG_ARROW_SCHEMA = pa.schema(
    [
        ("ts_client", pa.string()),
        ("venue", pa.string()),
        ("canonical_symbol", pa.string()),
        ("venue_symbol", pa.string()),
        ("source", pa.string()),
        ("raw_payload_sha256", pa.string()),
        ("recv_ts_ms", pa.int64()),
        ("source_ts_ms", pa.int64()),
        ("dex", pa.string()),
        ("coin", pa.string()),
        ("asset_id", pa.int64()),
        ("real_market_symbol", pa.string()),
        ("pair_index", pa.int64()),
        ("pair_id", pa.int64()),
        ("chain", pa.string()),
        ("mark_price", pa.float64()),
        ("index_price", pa.float64()),
        ("oracle_price", pa.float64()),
        ("best_bid", pa.float64()),
        ("best_ask", pa.float64()),
        ("bid_price", pa.float64()),
        ("ask_price", pa.float64()),
        ("mid_price", pa.float64()),
        ("last_trade_price", pa.float64()),
        ("exec_buy_price", pa.float64()),
        ("exec_sell_price", pa.float64()),
        ("spread_bps", pa.float64()),
        ("depth_10bps_usd", pa.float64()),
        ("depth_25bps_usd", pa.float64()),
        ("bid_depth_10bps_usd", pa.float64()),
        ("ask_depth_10bps_usd", pa.float64()),
        ("bid_depth_25bps_usd", pa.float64()),
        ("ask_depth_25bps_usd", pa.float64()),
        ("min_side_depth_10bps_usd", pa.float64()),
        ("funding_rate", pa.float64()),
        ("funding_interval_minutes", pa.int64()),
        ("open_interest_usd", pa.float64()),
        ("oi_cap_usd", pa.float64()),
        ("oi_cap_usage", pa.float64()),
        ("discovery_bound_pct", pa.float64()),
        ("bound_distance", pa.float64()),
        ("premium", pa.float64()),
        ("prev_day_price", pa.float64()),
        ("day_notional_volume", pa.float64()),
        ("fee_mode", pa.string()),
        ("taker_fee_bps", pa.float64()),
        ("maker_fee_bps", pa.float64()),
        ("fee_source", pa.string()),
        ("oracle_ts_ms", pa.int64()),
        ("oracle_ts_source", pa.string()),
        ("oracle_ts_status", pa.string()),
        ("oracle_ts_missing_reason", pa.string()),
        ("oracle_freshness_source_ts_ms", pa.int64()),
        ("oracle_freshness_recv_ts_ms", pa.int64()),
        ("oracle_freshness_lag_ms", pa.int64()),
        ("oracle_freshness_status", pa.string()),
        ("oracle_freshness_note", pa.string()),
        ("market_status", pa.string()),
        ("session_type", pa.string()),
        ("external_session_open", pa.bool_()),
        ("internal_session_open", pa.bool_()),
        ("maintenance_window", pa.bool_()),
        ("holiday_closure", pa.bool_()),
        ("is_tradable", pa.bool_()),
        ("source_confidence", pa.float64()),
        ("venue_quality_score", pa.float64()),
        ("block_reasons", pa.list_(pa.string())),
        ("raw_payload_ref", pa.string()),
    ]
)


def quote_log_identity(log: QuoteLog) -> tuple[str, str, str, str]:
    return (
        log.ts_client.isoformat(),
        log.venue.value,
        log.canonical_symbol,
        log.raw_payload_sha256,
    )


def collect_quote_logs(raw_root: Path) -> list[QuoteLog]:
    logs: list[QuoteLog] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in sorted(raw_root.glob("*/*.jsonl")):
        for row_index, row in enumerate(read_jsonl(path)):
            log = QuoteLog.model_validate(row)
            if log.raw_payload_ref is None:
                log = log.model_copy(update={"raw_payload_ref": f"{path}#row={row_index}"})
            key = quote_log_identity(log)
            if key in seen:
                continue
            seen.add(key)
            logs.append(log)
    return logs


def _instrument_by_symbol(
    instruments: list[InstrumentSpec] | None,
) -> dict[str, InstrumentSpec]:
    if instruments is None:
        return {}
    return {item.canonical_symbol.upper(): item for item in instruments}


def _ws_quote_from_row(
    row: dict[str, Any],
    *,
    instruments_by_symbol: dict[str, InstrumentSpec],
) -> QuoteLog | None:
    if row.get("message_kind") not in (None, "data"):
        return None
    subscription = row.get("subscription") or row.get("channel")
    canonical_symbol = row.get("canonical_symbol")
    instrument = (
        instruments_by_symbol.get(canonical_symbol.upper())
        if isinstance(canonical_symbol, str)
        else None
    )
    if subscription == "bbo":
        from sis.venues.trade_xyz.normalizer import quote_from_ws_bbo_row

        return quote_from_ws_bbo_row(
            row,
            asset_id=instrument.asset_id if instrument else None,
            real_market_symbol=instrument.real_market_symbol if instrument else None,
            fee_mode=instrument.fee_mode if instrument else None,
            taker_fee_bps=instrument.taker_fee_bps if instrument else None,
            maker_fee_bps=instrument.maker_fee_bps if instrument else None,
        )
    if subscription == "activeAssetCtx":
        from sis.venues.trade_xyz.normalizer import quote_from_ws_active_asset_ctx_row

        return quote_from_ws_active_asset_ctx_row(
            row,
            asset_id=instrument.asset_id if instrument else None,
            real_market_symbol=instrument.real_market_symbol if instrument else None,
        )
    return None


def _ws_subscription(row: dict[str, Any]) -> str:
    value = row.get("subscription") or row.get("channel") or "unknown"
    return value if isinstance(value, str) and value else "unknown"


def _is_control_ws_row(row: dict[str, Any]) -> bool:
    subscription = _ws_subscription(row)
    channel = row.get("channel")
    message_kind = row.get("message_kind")
    return (
        subscription == "__control__"
        or channel in {"subscriptionResponse", "pong"}
        or message_kind in {"control", "subscription_response", "pong"}
    )


def _is_malformed_supported_ws_row(row: dict[str, Any]) -> bool:
    data = row.get("payload")
    data = data.get("data") if isinstance(data, dict) else None
    if not isinstance(data, dict):
        return True
    subscription = _ws_subscription(row)
    if subscription == "bbo":
        bbo = data.get("bbo")
        return not isinstance(bbo, list) or len(bbo) < 2
    if subscription == "activeAssetCtx":
        return not isinstance(data.get("ctx"), dict)
    return False


@dataclass
class TradeXyzWsNormalizeStats:
    raw_ws_root: Path
    parquet_path: Path
    duckdb_path: Path
    quality_manifest_path: Path | None = None
    rest_parity_manifest_path: Path | None = None
    row_count_raw_seen: int = 0
    quote_count_written: int = 0
    bbo_quote_count: int = 0
    active_asset_ctx_quote_count: int = 0
    trade_row_count_skipped: int = 0
    control_row_count_skipped: int = 0
    duplicate_count_skipped: int = 0
    malformed_count: int = 0
    other_row_count_skipped: int = 0
    symbol_counts: dict[str, int] = field(default_factory=dict)
    subscriptions_included: set[str] = field(default_factory=set)
    subscriptions_excluded: set[str] = field(default_factory=set)

    def record_written(self, log: QuoteLog) -> None:
        self.quote_count_written += 1
        self.symbol_counts[log.canonical_symbol] = (
            self.symbol_counts.get(log.canonical_symbol, 0) + 1
        )
        if log.source == "trade_xyz_ws_bbo":
            self.bbo_quote_count += 1
            self.subscriptions_included.add("bbo")
        elif log.source == "trade_xyz_ws_activeAssetCtx":
            self.active_asset_ctx_quote_count += 1
            self.subscriptions_included.add("activeAssetCtx")

    def to_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "trade_xyz_ws_backtest_artifact_manifest.v1",
            "created_at": datetime.now(UTC).isoformat(),
            "raw_ws_root": str(self.raw_ws_root),
            "quality_manifest_path": str(self.quality_manifest_path)
            if self.quality_manifest_path
            else None,
            "rest_parity_manifest_path": str(self.rest_parity_manifest_path)
            if self.rest_parity_manifest_path
            else None,
            "symbols": sorted(self.symbol_counts),
            "symbol_counts": dict(sorted(self.symbol_counts.items())),
            "subscriptions_included": sorted(self.subscriptions_included),
            "subscriptions_excluded": sorted(self.subscriptions_excluded),
            "row_count_raw_seen": self.row_count_raw_seen,
            "quote_count_written": self.quote_count_written,
            "bbo_quote_count": self.bbo_quote_count,
            "active_asset_ctx_quote_count": self.active_asset_ctx_quote_count,
            "trade_row_count_skipped": self.trade_row_count_skipped,
            "control_row_count_skipped": self.control_row_count_skipped,
            "duplicate_count_skipped": self.duplicate_count_skipped,
            "malformed_count": self.malformed_count,
            "other_row_count_skipped": self.other_row_count_skipped,
            "event_time_policy": {
                "bbo": "Use source_ts_ms from payload.data.time for initial BBO-only bars.",
                "activeAssetCtx": (
                    "No source timestamp is present; recv_ts_ms is observation time only."
                ),
            },
            "oracle_timestamp_policy": (
                "Do not derive oracle_ts_ms from recv_ts_ms or source_ts_ms. "
                "Rows without explicit oracle timestamp fields keep oracle_ts_ms null."
            ),
            "fill_snapshot_policy": (
                "Only bbo rows are fill snapshot candidates. activeAssetCtx and trades do not "
                "populate fill bid/ask fields."
            ),
            "output_parquet_path": str(self.parquet_path),
            "output_duckdb_path": str(self.duckdb_path),
        }


def collect_trade_xyz_ws_quote_logs(
    raw_ws_root: Path,
    *,
    instruments: list[InstrumentSpec] | None = None,
) -> list[QuoteLog]:
    logs: list[QuoteLog] = []
    seen: set[tuple[str, str, str, str]] = set()
    instruments_by_symbol = _instrument_by_symbol(instruments)
    for path in sorted(raw_ws_root.rglob("*.jsonl")):
        for row_index, row in enumerate(read_jsonl(path)):
            log = _ws_quote_from_row(row, instruments_by_symbol=instruments_by_symbol)
            if log is None:
                continue
            if log.raw_payload_ref is None:
                log = log.model_copy(update={"raw_payload_ref": f"{path}#row={row_index}"})
            key = quote_log_identity(log)
            if key in seen:
                continue
            seen.add(key)
            logs.append(log)
    return logs


def _quote_log_row(item: QuoteLog) -> dict:
    row = item.model_dump(mode="json")
    row.pop("raw_payload", None)
    return row


def _write_quote_log_rows(
    rows: list[dict],
    *,
    writer: pq.ParquetWriter | None,
    parquet_path: Path,
) -> pq.ParquetWriter:
    table = pa.Table.from_pylist(rows, schema=QUOTE_LOG_ARROW_SCHEMA)
    if writer is None:
        writer = pq.ParquetWriter(parquet_path, QUOTE_LOG_ARROW_SCHEMA)
    writer.write_table(table)
    return writer


def _finish_duckdb(parquet_path: Path, duckdb_path: Path) -> None:
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(
            "CREATE OR REPLACE TABLE quotes AS SELECT * FROM read_parquet(?)", [str(parquet_path)]
        )


def _write_quote_logs(
    logs: list[QuoteLog],
    parquet_path: Path,
    duckdb_path: Path,
    *,
    chunk_size: int = 50_000,
) -> int:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    rows: list[dict] = []
    count = 0
    try:
        for item in logs:
            rows.append(_quote_log_row(item))
            if len(rows) >= chunk_size:
                writer = _write_quote_log_rows(rows, writer=writer, parquet_path=parquet_path)
                count += len(rows)
                rows = []
        if rows:
            writer = _write_quote_log_rows(rows, writer=writer, parquet_path=parquet_path)
            count += len(rows)
    finally:
        if writer is not None:
            writer.close()
    _finish_duckdb(parquet_path, duckdb_path)
    return count


def _write_trade_xyz_ws_quote_logs(
    raw_ws_root: Path,
    parquet_path: Path,
    duckdb_path: Path,
    *,
    instruments: list[InstrumentSpec] | None = None,
    manifest_path: Path | None = None,
    quality_manifest_path: Path | None = None,
    rest_parity_manifest_path: Path | None = None,
    chunk_size: int = 50_000,
) -> int:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    rows: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    instruments_by_symbol = _instrument_by_symbol(instruments)
    stats = TradeXyzWsNormalizeStats(
        raw_ws_root=raw_ws_root,
        parquet_path=parquet_path,
        duckdb_path=duckdb_path,
        quality_manifest_path=quality_manifest_path,
        rest_parity_manifest_path=rest_parity_manifest_path,
    )
    try:
        for path in sorted(raw_ws_root.rglob("*.jsonl")):
            for row_index, row in enumerate(read_jsonl(path)):
                stats.row_count_raw_seen += 1
                subscription = _ws_subscription(row)
                if _is_control_ws_row(row):
                    stats.control_row_count_skipped += 1
                    stats.subscriptions_excluded.add(subscription)
                    continue
                if subscription == "trades":
                    stats.trade_row_count_skipped += 1
                    stats.subscriptions_excluded.add(subscription)
                    continue
                if subscription not in {"bbo", "activeAssetCtx"}:
                    stats.other_row_count_skipped += 1
                    stats.subscriptions_excluded.add(subscription)
                    continue
                if row.get("message_kind") not in (None, "data") or _is_malformed_supported_ws_row(
                    row
                ):
                    stats.malformed_count += 1
                    stats.subscriptions_excluded.add(subscription)
                    continue
                log = _ws_quote_from_row(row, instruments_by_symbol=instruments_by_symbol)
                if log is None:
                    stats.other_row_count_skipped += 1
                    stats.subscriptions_excluded.add(subscription)
                    continue
                if log.raw_payload_ref is None:
                    log = log.model_copy(update={"raw_payload_ref": f"{path}#row={row_index}"})
                key = quote_log_identity(log)
                if key in seen:
                    stats.duplicate_count_skipped += 1
                    continue
                seen.add(key)
                rows.append(_quote_log_row(log))
                stats.record_written(log)
                if len(rows) >= chunk_size:
                    writer = _write_quote_log_rows(rows, writer=writer, parquet_path=parquet_path)
                    rows = []
        if rows:
            writer = _write_quote_log_rows(rows, writer=writer, parquet_path=parquet_path)
    finally:
        if writer is not None:
            writer.close()
    if stats.quote_count_written == 0:
        raise FileNotFoundError(f"No bbo or activeAssetCtx WS JSONL rows found under {raw_ws_root}")
    _finish_duckdb(parquet_path, duckdb_path)
    if manifest_path is not None:
        write_json(manifest_path, stats.to_manifest())
    return stats.quote_count_written


def normalize_quotes(raw_root: Path, parquet_path: Path, duckdb_path: Path) -> int:
    logs = collect_quote_logs(raw_root)
    if not logs:
        raise FileNotFoundError(f"No raw quote JSONL files found under {raw_root}")

    return _write_quote_logs(logs, parquet_path, duckdb_path)


def normalize_trade_xyz_ws_quotes(
    raw_ws_root: Path,
    parquet_path: Path,
    duckdb_path: Path,
    *,
    instruments: list[InstrumentSpec] | None = None,
    manifest_path: Path | None = None,
    quality_manifest_path: Path | None = None,
    rest_parity_manifest_path: Path | None = None,
) -> int:
    return _write_trade_xyz_ws_quote_logs(
        raw_ws_root,
        parquet_path,
        duckdb_path,
        instruments=instruments,
        manifest_path=manifest_path,
        quality_manifest_path=quality_manifest_path,
        rest_parity_manifest_path=rest_parity_manifest_path,
    )
