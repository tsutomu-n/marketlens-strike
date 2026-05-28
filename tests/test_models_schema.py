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
        funding_rate=0.0001,
        fee_mode="standard",
        taker_fee_bps=9.0,
        maker_fee_bps=3.0,
        source="test",
        raw_payload_sha256="abc123",
        raw_payload_ref="data/raw/example.jsonl",
        raw_payload={"pair": {"symbol": "SP500"}},
    )
    data = quote.model_dump(mode="json")
    validate(data, load_schema("quote_log_v2.schema.json"))


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
