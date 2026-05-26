from __future__ import annotations

from sis.execution.trade_xyz_adapter import TradeXyzOrderIntent, TradeXyzSafetyAdapter


class _FakeExchange:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def read_account_state(
        self, master_address: str, subaccount_address: str | None = None
    ) -> dict:
        self.calls.append("read_account_state")
        return {
            "master_address": master_address,
            "subaccount_address": subaccount_address,
            "equity": 1000.0,
        }

    def schedule_cancel(self, deadline_ts_ms: int) -> dict:
        self.calls.append("schedule_cancel")
        return {"status": "ok", "deadline_ts_ms": deadline_ts_ms}

    def place_limit_order(self, payload: dict) -> dict:
        self.calls.append("place_limit_order")
        return {"status": "accepted", "cloid": payload["cloid"]}

    def order_status_by_cloid(self, cloid: str) -> dict:
        self.calls.append("order_status_by_cloid")
        return {
            "status": "open",
            "order_id": "ord-1",
            "symbol": "SP500",
            "side": "buy",
            "quantity": 1.0,
        }

    def cancel_by_cloid(self, cloid: str) -> dict:
        self.calls.append("cancel_by_cloid")
        return {"status": "canceled", "cloid": cloid}

    def close_position_reduce_only(self, payload: dict) -> dict:
        self.calls.append("close_position_reduce_only")
        return {"status": "accepted", "cloid": payload["cloid"]}


def test_trade_xyz_adapter_blocks_non_post_only_order() -> None:
    adapter = TradeXyzSafetyAdapter(_FakeExchange())

    result = adapter.place_limit_order(
        TradeXyzOrderIntent(
            canonical_symbol="SP500",
            side="long",
            quantity=1.0,
            limit_price=100.0,
            cloid="cloid-1",
            notional_usd=25.0,
            leverage=1.0,
            post_only=False,
            reduce_only=False,
            tif="Alo",
        )
    )

    assert result.success is False
    assert result.status == "blocked_market_order"


def test_trade_xyz_adapter_schedule_order_status_and_cancel_by_cloid() -> None:
    exchange = _FakeExchange()
    adapter = TradeXyzSafetyAdapter(exchange)

    scheduled = adapter.schedule_cancel(deadline_ts_ms=1_717_000_000_000)
    submitted = adapter.place_limit_order(
        TradeXyzOrderIntent(
            canonical_symbol="SP500",
            side="long",
            quantity=1.0,
            limit_price=100.0,
            cloid="cloid-2",
            notional_usd=25.0,
            leverage=1.0,
        )
    )
    status = adapter.order_status_by_cloid("cloid-2")
    canceled = adapter.cancel_by_cloid("cloid-2")

    assert scheduled.success is True
    assert submitted.success is True
    assert status.status == "open"
    assert canceled.success is True
    assert exchange.calls == [
        "schedule_cancel",
        "place_limit_order",
        "order_status_by_cloid",
        "cancel_by_cloid",
    ]


def test_trade_xyz_adapter_close_requires_reduce_only() -> None:
    adapter = TradeXyzSafetyAdapter(_FakeExchange())
    blocked = adapter.close_position_reduce_only(
        canonical_symbol="SP500",
        side="short",
        quantity=1.0,
        limit_price=99.0,
        cloid="cloid-3",
        reduce_only=False,
    )
    allowed = adapter.close_position_reduce_only(
        canonical_symbol="SP500",
        side="short",
        quantity=1.0,
        limit_price=99.0,
        cloid="cloid-4",
        reduce_only=True,
    )

    assert blocked.success is False
    assert blocked.status == "blocked_non_reduce_only_close"
    assert allowed.success is True
    assert allowed.status == "close_submitted"
