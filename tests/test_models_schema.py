import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate

from sis.models import AssetClass, InstrumentSpec, MarketSession, MarketStatus, QuoteLog, Venue


def load_schema(name: str) -> dict:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def test_instrument_spec_matches_schema() -> None:
    item = InstrumentSpec(
        venue=Venue.GTRADE,
        canonical_symbol="QQQ",
        venue_symbol="QQQ/USD",
        pair_index=87,
        asset_class=AssetClass.INDEX,
        api_readable=True,
        opening_fee_bps=3,
        max_open_interest="1000000",
        max_leverage=100,
    )
    validate(item.model_dump(mode="json"), load_schema("instrument_registry.schema.json"))


def test_quote_log_allows_null_bid_ask_and_raw_ref() -> None:
    quote = QuoteLog(
        ts_client=datetime.now(timezone.utc),
        venue=Venue.GTRADE,
        canonical_symbol="QQQ",
        venue_symbol="QQQ/USD",
        pair_index=87,
        bid_price=None,
        ask_price=None,
        source="test",
        raw_payload_sha256="abc123",
        raw_payload_ref="data/raw/example.jsonl",
    )
    data = quote.model_dump(mode="json")
    assert data["bid_price"] is None
    assert data["ask_price"] is None
    assert data["raw_payload_ref"] == "data/raw/example.jsonl"
    validate(data, load_schema("quote_log_v1.schema.json"))


def test_market_session_model_exists() -> None:
    session = MarketSession(
        venue=Venue.GTRADE,
        canonical_symbol="SPY",
        market_status=MarketStatus.OPEN,
        is_tradable=True,
        session_source="gtrade_sidecar_v1",
    )
    assert session.market_status == MarketStatus.OPEN
    assert session.is_tradable is True
