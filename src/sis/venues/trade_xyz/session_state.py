from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from sis.market_calendar import market_session_state
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import collect_quote_logs
from sis.venues.trade_xyz.registry import load_trade_xyz_registry

EASTERN = ZoneInfo("America/New_York")

INDEX_23H_SYMBOLS = {"SP500", "XYZ100"}
EQUITY_24H_SYMBOLS = {"AAPL", "AMD", "AMZN", "EWJ", "GOOGL", "META", "MSFT", "NVDA", "TSLA"}


@dataclass(frozen=True)
class TradeXyzSpecSessionState:
    session_type: str
    external_session_open: bool
    internal_session_open: bool
    maintenance_window: bool
    source: str
    data_status: str
    notes: list[str]


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.from_dicts(rows, infer_schema_length=None) if rows else pl.DataFrame()
    frame.write_parquet(path)


def _is_between_weekly(
    value: datetime,
    *,
    start_weekday: int,
    start_time: time,
    end_weekday: int,
    end_time: time,
) -> bool:
    weekday = value.weekday()
    current = (weekday, value.time())
    start = (start_weekday, start_time)
    end = (end_weekday, end_time)
    return current >= start or current < end if start > end else start <= current < end


def _is_index_maintenance_window(value_et: datetime) -> bool:
    return value_et.weekday() in {0, 1, 2, 3} and time(17, 0) <= value_et.time() < time(18, 0)


def _spec_session_state(
    symbol: str, ts: datetime, *, holiday_closure: bool | None
) -> TradeXyzSpecSessionState | None:
    normalized_symbol = symbol.upper()
    ts_et = ts.astimezone(EASTERN)
    holiday = bool(holiday_closure)
    if normalized_symbol in INDEX_23H_SYMBOLS:
        within_week = _is_between_weekly(
            ts_et,
            start_weekday=6,
            start_time=time(18, 0),
            end_weekday=4,
            end_time=time(17, 0),
        )
        maintenance = within_week and _is_index_maintenance_window(ts_et)
        external_open = within_week and not maintenance and not holiday
        internal_open = within_week and (maintenance or holiday)
        return TradeXyzSpecSessionState(
            session_type="regular" if external_open else "closed",
            external_session_open=external_open,
            internal_session_open=internal_open,
            maintenance_window=maintenance,
            source="docs_trade_xyz_specification_index",
            data_status="spec_derived",
            notes=[
                "trade_xyz_spec_external_23h_5d_sunday_18_to_friday_17_et",
                "trade_xyz_spec_daily_maintenance_monday_to_thursday_17_to_18_et",
                "holiday_closure_uses_exchange_calendar_proxy",
            ],
        )
    if normalized_symbol in EQUITY_24H_SYMBOLS:
        within_week = _is_between_weekly(
            ts_et,
            start_weekday=6,
            start_time=time(20, 0),
            end_weekday=4,
            end_time=time(20, 0),
        )
        external_open = within_week and not holiday
        internal_open = not external_open
        return TradeXyzSpecSessionState(
            session_type="regular" if external_open else "closed",
            external_session_open=external_open,
            internal_session_open=internal_open,
            maintenance_window=False,
            source="docs_trade_xyz_specification_index",
            data_status="spec_derived",
            notes=[
                "trade_xyz_spec_external_24h_5d_sunday_20_to_friday_20_et",
                "internal_session_derived_as_not_external_open_for_supported_equity_symbols",
                "holiday_closure_uses_exchange_calendar_proxy",
            ],
        )
    return None


def build_trade_xyz_session_state_observations(
    *,
    data_dir: Path,
    registry_path: Path | None = None,
    raw_quotes_root: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    effective_registry_path = (
        registry_path or data_dir / "registry/trade_xyz_instrument_registry.json"
    )
    effective_raw_quotes_root = raw_quotes_root or data_dir / "raw/quotes"
    instruments = {
        item.canonical_symbol.upper(): item
        for item in load_trade_xyz_registry(effective_registry_path)
    }
    logs = [
        log
        for log in collect_quote_logs(effective_raw_quotes_root)
        if log.venue.value == "trade_xyz"
    ]
    if not logs:
        raise FileNotFoundError(
            f"No Trade[XYZ] quote JSONL rows found under {effective_raw_quotes_root}"
        )

    rows: list[dict[str, Any]] = []
    missing_field_counts: dict[str, int] = defaultdict(int)
    status_counts: dict[str, int] = defaultdict(int)
    for log in sorted(logs, key=lambda item: (item.canonical_symbol, item.ts_client)):
        symbol = log.canonical_symbol.upper()
        instrument = instruments.get(symbol)
        state = market_session_state("trade_xyz", symbol, log.ts_client)
        spec_state = _spec_session_state(
            symbol, log.ts_client, holiday_closure=state.holiday_closure
        )
        missing_fields: list[str] = []
        if spec_state is None:
            internal_session_open = None
            maintenance_window = None
            external_session_open = state.external_session_open
            session_type = state.session_type
            source = "exchange_calendars"
            data_status = state.data_status
            notes = [
                *state.notes,
                "maintenance_window_not_observed_from_exchange_calendar",
                "internal_session_open_not_observed_from_exchange_calendar",
            ]
            missing_fields = ["internal_session_open", "maintenance_window"]
        else:
            internal_session_open = spec_state.internal_session_open
            maintenance_window = spec_state.maintenance_window
            external_session_open = spec_state.external_session_open
            session_type = spec_state.session_type
            source = spec_state.source
            data_status = spec_state.data_status
            notes = [*state.notes, *spec_state.notes]
        for field in missing_fields:
            missing_field_counts[field] += 1
        status_counts[session_type] += 1
        rows.append(
            {
                "schema_version": "session_state_observation.v1",
                "observed_ts": log.ts_client.astimezone(UTC).isoformat(),
                "canonical_symbol": symbol,
                "venue_symbol": instrument.venue_symbol if instrument else log.venue_symbol,
                "real_market_symbol": instrument.real_market_symbol if instrument else None,
                "asset_class": instrument.asset_class.value if instrument else "unknown",
                "calendar": state.calendar,
                "session_type": session_type,
                "external_session_open": external_session_open,
                "internal_session_open": internal_session_open,
                "maintenance_window": maintenance_window,
                "holiday_closure": state.holiday_closure,
                "source": source,
                "data_status": data_status,
                "missing_fields": missing_fields,
                "notes": notes,
                "raw_payload_ref": log.raw_payload_ref,
            }
        )

    generated = generated_at or datetime.now(UTC)
    raw_path = data_dir / f"raw/sessions/trade_xyz_state/{generated.date().isoformat()}.jsonl"
    parquet_path = data_dir / "normalized/session_state_observations.parquet"
    manifest_path = data_dir / "manifests/session_state_manifest.json"
    _write_jsonl(rows, raw_path)
    _write_parquet(rows, parquet_path)

    manifest = {
        "schema_version": "session_state_manifest.v1",
        "generated_at": generated.isoformat(),
        "registry_path": str(effective_registry_path),
        "raw_quotes_root": str(effective_raw_quotes_root),
        "raw_artifact_path": str(raw_path),
        "artifact_path": str(parquet_path),
        "row_count": len(rows),
        "symbol_count": len({row["canonical_symbol"] for row in rows}),
        "session_type_counts": dict(sorted(status_counts.items())),
        "missing_field_counts": dict(sorted(missing_field_counts.items())),
        "calendar_source": "exchange_calendars+docs_trade_xyz_specification_index",
        "notes": [
            "holiday_closure uses exchange_calendars as a proxy",
            "internal_session_open and maintenance_window are spec-derived for supported Trade[XYZ] symbols",
            "unsupported symbols retain null session fields and are counted in missing_field_counts",
        ],
    }
    write_json(manifest_path, manifest)
    return manifest
