from __future__ import annotations

from datetime import datetime, timezone

from sis.models import InstrumentSpec
from sis.venues.trade_xyz.reference_data_rows import fee_snapshot_rows
from sis.venues.trade_xyz.reference_data_rows import fee_source_summary
from sis.venues.trade_xyz.reference_data_rows import registry_snapshot_rows
from sis.venues.trade_xyz.reference_data_rows import session_calendar_snapshot_rows


def _instrument(
    *,
    canonical_symbol: str = "NVDA",
    venue_symbol: str | None = None,
    fee_mode: str | None = "standard",
    taker_fee_bps: float | None = 9.0,
    maker_fee_bps: float | None = 3.0,
    external_session: str | None = "nasdaq_regular",
    internal_session: str | None = "trade_xyz_internal",
) -> InstrumentSpec:
    return InstrumentSpec(
        venue="trade_xyz",
        canonical_symbol=canonical_symbol,
        venue_symbol=venue_symbol or canonical_symbol,
        asset_class="equity",
        dex=None,
        coin=None,
        asset_id=130002,
        real_market_symbol=canonical_symbol,
        fee_mode=fee_mode,
        taker_fee_bps=taker_fee_bps,
        maker_fee_bps=maker_fee_bps,
        discovery_bound_bps=500.0,
        oi_cap_usd=1_000_000.0,
        external_session=external_session,
        internal_session=internal_session,
        active=True,
    )


def test_registry_snapshot_rows_apply_defaults_and_discovery_bound() -> None:
    rows = registry_snapshot_rows(
        [_instrument()],
        snapshot_ts=datetime(2026, 5, 26, 1, tzinfo=timezone.utc),
        source_url="data/registry.json",
        source_hash="hash",
    )

    assert rows == [
        {
            "schema_version": "instrument_registry_snapshot.v1",
            "snapshot_ts": "2026-05-26T01:00:00+00:00",
            "canonical_symbol": "NVDA",
            "venue_symbol": "NVDA",
            "dex": "xyz",
            "coin": "xyz:NVDA",
            "asset_id": 130002,
            "underlying": "NVDA",
            "asset_class": "equity",
            "max_leverage": None,
            "margin_mode": None,
            "discovery_bound_pct": 0.05,
            "discovery_bound_bps": 500.0,
            "open_interest_cap_usd": 1_000_000.0,
            "external_session_hours": "nasdaq_regular",
            "internal_session_hours": "trade_xyz_internal",
            "holiday_calendar_ref": None,
            "fee_mode": "standard",
            "tick_size": None,
            "lot_size": None,
            "min_order_size": None,
            "min_notional_usd": None,
            "source_url": "data/registry.json",
            "source_hash": "hash",
        }
    ]


def test_fee_rows_filter_incomplete_fee_specs_and_summary_tracks_unresolved() -> None:
    instruments = [
        _instrument(canonical_symbol="NVDA"),
        _instrument(canonical_symbol="TSLA", fee_mode="standard", taker_fee_bps=None),
    ]

    rows = fee_snapshot_rows(
        instruments,
        snapshot_ts=datetime(2026, 5, 26, 1, tzinfo=timezone.utc),
        source="data/registry.json",
        source_hash="hash",
    )
    summary = fee_source_summary(instruments, rows)

    assert len(rows) == 1
    assert rows[0]["schema_version"] == "fee_snapshot.v1"
    assert rows[0]["canonical_symbol"] == "NVDA"
    assert rows[0]["fee_tier"] is None
    assert rows[0]["builder_fee_bps"] is None
    assert summary["instrument_count"] == 2
    assert summary["fee_snapshot_count"] == 1
    assert summary["resolved_symbol_count"] == 1
    assert summary["unresolved_symbol_count"] == 1
    assert summary["unresolved_symbols"] == ["TSLA"]
    assert summary["fee_mode_counts"] == {"standard": 1}
    assert summary["fee_source_counts"] == {"data/registry.json": 1}
    assert summary["account_specific_fee_status"] == "not_collected_no_wallet_or_user_context"
    assert summary["account_specific_missing_field_counts"]["builder_fee_bps"] == 1
    assert "wallet/signing/exchange-write remain out of scope" in summary["notes"][1]


def test_session_rows_preserve_conservative_missing_field_semantics() -> None:
    rows = session_calendar_snapshot_rows(
        [_instrument(external_session=None, internal_session=None)],
        snapshot_ts=datetime(2026, 5, 26, 1, tzinfo=timezone.utc),
        source="data/registry.json",
        source_hash="hash",
    )

    row = rows[0]
    assert row["schema_version"] == "session_calendar_snapshot.v1"
    assert row["external_session_ref"] is None
    assert row["internal_session_ref"] is None
    assert row["external_session_open"] is None
    assert row["internal_session_open"] is None
    assert row["maintenance_window"] is None
    assert row["holiday_closure"] is None
    assert row["close_only_allowed"] is True
    assert row["data_status"] == "incomplete"
    assert row["missing_fields"] == [
        "external_session_ref",
        "internal_session_ref",
        "external_session_open",
        "internal_session_open",
        "maintenance_window",
        "holiday_closure",
    ]
    assert row["notes"] == [
        "registry_derived_session_refs_only",
        "do_not_treat_null_open_flags_as_observed_session_state",
    ]
