import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate

from sis.models import AssetClass, InstrumentSpec, MarketSession, MarketStatus, QuoteLog, Venue


def load_schema(name: str) -> dict:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def test_trade_xyz_instrument_spec_matches_schema() -> None:
    item = InstrumentSpec(
        venue=Venue.TRADE_XYZ,
        canonical_symbol="SP500",
        venue_symbol="SP500",
        asset_class=AssetClass.INDEX,
        dex="xyz",
        coin="xyz:SP500",
        asset_id=None,
        real_market_symbol="SPY",
        fee_mode="unknown",
        api_readable=True,
        api_orderable=False,
        max_leverage=50,
        discovery_bound_bps=200,
    )
    validate(item.model_dump(mode="json"), load_schema("instrument_registry.schema.json"))


def test_quote_log_v2_accepts_hip3_fields() -> None:
    quote = QuoteLog(
        ts_client=datetime.now(timezone.utc),
        venue=Venue.TRADE_XYZ,
        canonical_symbol="SP500",
        venue_symbol="SP500",
        dex="xyz",
        coin="xyz:SP500",
        asset_id=100001,
        best_bid=5300.2,
        best_ask=5300.8,
        exec_buy_price=5300.8,
        exec_sell_price=5300.2,
        funding_rate=0.0001,
        funding_interval_minutes=60,
        fee_mode="standard",
        taker_fee_bps=9.0,
        maker_fee_bps=3.0,
        fee_source="instrument_registry",
        source_confidence=1.0,
        venue_quality_score=1.0,
        oracle_ts_ms=1770000000000,
        oracle_ts_source="oracleTs",
        oracle_ts_status="observed",
        source="test",
        raw_payload_sha256="abc123",
        raw_payload_ref="data/raw/example.jsonl",
        raw_payload={"pair": {"symbol": "SP500"}},
    )
    data = quote.model_dump(mode="json")
    validate(data, load_schema("quote_log_v2.schema.json"))


def test_trade_xyz_snapshot_schemas_accept_required_operational_fields() -> None:
    validate(
        {
            "schema_version": "funding_event.v1",
            "funding_event_ts": "2026-05-31T00:00:00+00:00",
            "canonical_symbol": "SP500",
            "funding_rate": 0.0001,
            "funding_interval_minutes": 60,
            "oracle_price_at_funding": 5300.0,
            "source_ts_ms": 1770000000000,
            "recv_ts_ms": 1770000001000,
            "raw_payload_sha256": "abc",
            "raw_payload_ref": "data/raw/funding/trade_xyz/2026-05-31.jsonl#row=0",
        },
        load_schema("funding_event.v1.schema.json"),
    )
    validate(
        {
            "schema_version": "fee_snapshot.v1",
            "snapshot_ts": "2026-05-31T00:00:00+00:00",
            "canonical_symbol": "SP500",
            "fee_mode": "standard",
            "taker_fee_bps": 9.0,
            "maker_fee_bps": 3.0,
            "source": "docs.trade.xyz",
            "source_hash": "abc",
        },
        load_schema("fee_snapshot.v1.schema.json"),
    )
    validate(
        {
            "schema_version": "instrument_registry_snapshot.v1",
            "snapshot_ts": "2026-05-31T00:00:00+00:00",
            "canonical_symbol": "SP500",
            "venue_symbol": "SP500",
            "dex": "xyz",
            "coin": "xyz:SP500",
            "asset_class": "index",
            "source_url": "https://docs.trade.xyz/consolidated-resources/specification-index",
            "source_hash": "abc",
        },
        load_schema("instrument_registry_snapshot.v1.schema.json"),
    )
    validate(
        {
            "schema_version": "session_calendar_snapshot.v1",
            "snapshot_ts": "2026-05-31T00:00:00+00:00",
            "canonical_symbol": "SP500",
            "venue_symbol": "SP500",
            "real_market_symbol": "SPY",
            "asset_class": "index",
            "timezone": None,
            "external_session_ref": "nyse_regular",
            "internal_session_ref": "trade_xyz_internal",
            "external_session_open": None,
            "internal_session_open": None,
            "maintenance_window": None,
            "holiday_closure": None,
            "close_only_allowed": True,
            "source": "data/registry/trade_xyz_instrument_registry.json",
            "source_hash": "abc",
            "data_status": "incomplete",
            "missing_fields": ["maintenance_window", "holiday_closure"],
            "notes": ["registry_derived_session_refs_only"],
        },
        load_schema("session_calendar_snapshot.v1.schema.json"),
    )


def test_quote_log_v2_requires_raw_hash() -> None:
    payload = {
        "ts_client": datetime.now(timezone.utc).isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "SP500",
        "venue_symbol": "SP500",
        "source": "test",
    }
    schema = load_schema("quote_log_v2.schema.json")
    try:
        validate(payload, schema)
    except Exception:
        pass
    else:
        raise AssertionError("quote_log_v2.schema.json should require raw_payload_sha256")


def test_archived_legacy_venue_not_in_active_seed() -> None:
    seed = json.loads(Path("configs/instrument_registry.seed.json").read_text(encoding="utf-8"))
    rows = seed.get("venues", {}).get("trade_xyz", [])
    assert rows
    dumped = json.dumps(rows)
    assert "gtrade" not in dumped
    assert "ostium" not in dumped
    assert "XAU" not in dumped


def test_market_session_model_exists() -> None:
    session = MarketSession(
        venue=Venue.TRADE_XYZ,
        canonical_symbol="SP500",
        market_status=MarketStatus.OPEN,
        is_tradable=True,
        session_source="trade_xyz_quote_feed",
    )
    assert session.market_status == MarketStatus.OPEN
    assert session.is_tradable is True
