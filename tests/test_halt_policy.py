from datetime import datetime, timezone

from sis.models import MarketStatus, QuoteLog, Venue
from sis.risk.halt_policy import evaluate_halt_reasons


def _quote(**kwargs) -> QuoteLog:
    base = {
        "ts_client": datetime.now(timezone.utc),
        "venue": Venue.GTRADE,
        "canonical_symbol": "SPY",
        "venue_symbol": "SPY/USD",
        "market_status": MarketStatus.OPEN,
        "is_tradable": True,
        "source": "test",
        "raw_payload_sha256": "abc123",
    }
    base.update(kwargs)
    return QuoteLog(**base)


def test_halt_reasons_block_closed_market() -> None:
    quote = _quote(market_status=MarketStatus.CLOSED, is_tradable=False)
    assert evaluate_halt_reasons(quote, {"halt_policy": {}}) == ["BLOCK_MARKET_CLOSED"]


def test_halt_reasons_block_wide_spread() -> None:
    quote = _quote(spread_bps=20)
    policy = {"halt_policy": {"spread": {"max_spread_p90_bps": {"SPY": 8}}}}
    assert "BLOCK_SPREAD_TOO_WIDE" in evaluate_halt_reasons(quote, policy)


def test_halt_reasons_block_mark_index_divergence() -> None:
    quote = _quote(mark_price=110, index_price=100)
    assert "BLOCK_MARK_INDEX_DIVERGENCE" in evaluate_halt_reasons(quote, {"halt_policy": {}})
