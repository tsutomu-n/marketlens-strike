from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.models import InstrumentSpec


def registry_snapshot_rows(
    instruments: list[InstrumentSpec],
    *,
    snapshot_ts: datetime,
    source_url: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        discovery_bound_pct = (
            item.discovery_bound_bps / 10_000 if item.discovery_bound_bps is not None else None
        )
        rows.append(
            {
                "schema_version": "instrument_registry_snapshot.v1",
                "snapshot_ts": snapshot_ts.isoformat(),
                "canonical_symbol": item.canonical_symbol,
                "venue_symbol": item.venue_symbol,
                "dex": item.dex or "xyz",
                "coin": item.coin or f"xyz:{item.canonical_symbol}",
                "asset_id": item.asset_id,
                "underlying": item.real_market_symbol,
                "asset_class": item.asset_class.value,
                "max_leverage": item.max_leverage,
                "margin_mode": None,
                "discovery_bound_pct": discovery_bound_pct,
                "discovery_bound_bps": item.discovery_bound_bps,
                "open_interest_cap_usd": item.oi_cap_usd,
                "external_session_hours": item.external_session,
                "internal_session_hours": item.internal_session,
                "holiday_calendar_ref": None,
                "fee_mode": item.fee_mode,
                "tick_size": None,
                "lot_size": None,
                "min_order_size": None,
                "min_notional_usd": None,
                "source_url": source_url,
                "source_hash": source_hash,
            }
        )
    return rows


def fee_snapshot_rows(
    instruments: list[InstrumentSpec],
    *,
    snapshot_ts: datetime,
    source: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        if item.fee_mode is None or item.taker_fee_bps is None or item.maker_fee_bps is None:
            continue
        rows.append(
            {
                "schema_version": "fee_snapshot.v1",
                "snapshot_ts": snapshot_ts.isoformat(),
                "canonical_symbol": item.canonical_symbol,
                "venue_symbol": item.venue_symbol,
                "fee_mode": item.fee_mode,
                "fee_tier": None,
                "taker_fee_bps": item.taker_fee_bps,
                "maker_fee_bps": item.maker_fee_bps,
                "builder_fee_bps": None,
                "staking_discount_bps": None,
                "source": source,
                "source_hash": source_hash,
            }
        )
    return rows


def fee_source_summary(
    instruments: list[InstrumentSpec],
    fee_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    resolved_symbols = {str(row["canonical_symbol"]) for row in fee_rows}
    unresolved_symbols = [
        item.canonical_symbol
        for item in instruments
        if item.canonical_symbol not in resolved_symbols
    ]
    source_counts: dict[str, int] = {}
    mode_counts: dict[str, int] = {}
    for row in fee_rows:
        source = str(row.get("source") or "unknown")
        mode = str(row.get("fee_mode") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
    account_specific_missing_fields = [
        "fee_tier",
        "builder_fee_bps",
        "staking_discount_bps",
        "account_growth_mode",
    ]
    return {
        "instrument_count": len(instruments),
        "fee_snapshot_count": len(fee_rows),
        "resolved_symbol_count": len(resolved_symbols),
        "unresolved_symbol_count": len(unresolved_symbols),
        "unresolved_symbols": unresolved_symbols,
        "fee_mode_counts": mode_counts,
        "fee_source_counts": source_counts,
        "account_specific_fee_status": "not_collected_no_wallet_or_user_context",
        "account_specific_missing_fields": account_specific_missing_fields,
        "account_specific_missing_field_counts": {
            field: len(fee_rows) for field in account_specific_missing_fields
        },
        "notes": [
            "fee_snapshots are registry/config-derived unless source points to an observed fee feed",
            "wallet/signing/exchange-write remain out of scope for this pure backtest data path",
        ],
    }


def session_calendar_snapshot_rows(
    instruments: list[InstrumentSpec],
    *,
    snapshot_ts: datetime,
    source: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in instruments:
        missing_fields: list[str] = []
        if item.external_session is None:
            missing_fields.append("external_session_ref")
        if item.internal_session is None:
            missing_fields.append("internal_session_ref")
        missing_fields.extend(
            [
                "external_session_open",
                "internal_session_open",
                "maintenance_window",
                "holiday_closure",
            ]
        )
        notes = [
            "registry_derived_session_refs_only",
            "do_not_treat_null_open_flags_as_observed_session_state",
        ]
        rows.append(
            {
                "schema_version": "session_calendar_snapshot.v1",
                "snapshot_ts": snapshot_ts.isoformat(),
                "canonical_symbol": item.canonical_symbol,
                "venue_symbol": item.venue_symbol,
                "real_market_symbol": item.real_market_symbol,
                "asset_class": item.asset_class.value,
                "timezone": None,
                "external_session_ref": item.external_session,
                "internal_session_ref": item.internal_session,
                "external_session_open": None,
                "internal_session_open": None,
                "maintenance_window": None,
                "holiday_closure": None,
                "close_only_allowed": True,
                "source": source,
                "source_hash": source_hash,
                "data_status": "incomplete" if missing_fields else "registry_derived",
                "missing_fields": missing_fields,
                "notes": notes,
            }
        )
    return rows
