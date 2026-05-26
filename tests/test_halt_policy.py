from datetime import datetime

from sis.models import MarketStatus, QuoteLog, Venue
from sis.risk.halt_policy import CostContext, EventWindow, PositionContext, evaluate_halt_reasons


def _quote(**kwargs) -> QuoteLog:
    base = {
        # Fixed weekday timestamp to keep default halt-policy tests deterministic.
        "ts_client": datetime.fromisoformat("2026-05-22T14:00:00+00:00"),
        "venue": Venue.TRADE_XYZ,
        "canonical_symbol": "SP500",
        "venue_symbol": "SP500",
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
    policy = {"halt_policy": {"spread": {"max_spread_bps": {"SP500": 8}}}}
    assert "BLOCK_SPREAD_TOO_WIDE" in evaluate_halt_reasons(quote, policy)


def test_halt_reasons_block_mark_index_divergence() -> None:
    quote = _quote(mark_price=110, index_price=100)
    assert "BLOCK_MARK_INDEX_DIVERGENCE" in evaluate_halt_reasons(quote, {"halt_policy": {}})


def test_halt_reasons_block_session_end_near_for_indices() -> None:
    quote = _quote(ts_client=datetime.fromisoformat("2026-05-22T19:45:00+00:00"))
    policy = {"halt_policy": {"session": {"block_before_close_minutes": 30}}}
    assert "BLOCK_SESSION_END_NEAR" in evaluate_halt_reasons(quote, policy)


def test_halt_reasons_block_weekend_hold() -> None:
    quote = _quote(ts_client=datetime.fromisoformat("2026-05-23T16:00:00+00:00"))
    assert "BLOCK_WEEKEND_HOLD" in evaluate_halt_reasons(quote, {"halt_policy": {}})


def test_halt_reasons_block_near_liquidation_for_long_position() -> None:
    quote = _quote(mark_price=100)
    policy = {"halt_policy": {"liquidation": {"near_liquidation_bps": 100}}}
    position = PositionContext(side="long", liquidation_price=99.5, leverage=2)
    assert "BLOCK_NEAR_LIQUIDATION" in evaluate_halt_reasons(quote, policy, position)


def test_halt_reasons_allow_liquidation_distance_outside_threshold() -> None:
    quote = _quote(mark_price=100)
    policy = {"halt_policy": {"liquidation": {"near_liquidation_bps": 100}}}
    position = PositionContext(side="long", liquidation_price=95, leverage=2)
    assert "BLOCK_NEAR_LIQUIDATION" not in evaluate_halt_reasons(quote, policy, position)


def test_halt_reasons_block_event_window() -> None:
    quote = _quote(ts_client=datetime.fromisoformat("2026-05-22T14:00:00+00:00"))
    windows = [
        EventWindow(
            starts_at=datetime.fromisoformat("2026-05-22T13:30:00+00:00"),
            ends_at=datetime.fromisoformat("2026-05-22T14:15:00+00:00"),
            label="major_usd_event",
        )
    ]

    assert "BLOCK_EVENT_WINDOW" in evaluate_halt_reasons(quote, {"halt_policy": {}}, event_windows=windows)


def test_halt_reasons_block_cost_too_high() -> None:
    quote = _quote()
    cost = CostContext(total_cost_bps=35, max_cost_bps=20)

    assert "BLOCK_COST_TOO_HIGH" in evaluate_halt_reasons(quote, {"halt_policy": {}}, cost=cost)


def test_halt_reasons_block_registry_incomplete() -> None:
    quote = _quote()

    assert "BLOCK_REGISTRY_INCOMPLETE" in evaluate_halt_reasons(
        quote,
        {"halt_policy": {}},
        registry_complete=False,
    )
