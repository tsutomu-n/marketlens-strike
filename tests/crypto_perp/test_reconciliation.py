from __future__ import annotations

from decimal import Decimal

from sis.crypto_perp.reconciliation import (
    LiveOpenOrder,
    LivePosition,
    build_reduce_only_close_order,
    reconcile_flat,
)


def test_reconcile_flat_requires_no_position_and_no_open_order() -> None:
    flat = reconcile_flat(positions=[], open_orders=[])
    positioned = reconcile_flat(
        positions=[LivePosition(symbol="BTCUSDT", hold_side="long", total=Decimal("0.01"))],
        open_orders=[],
    )
    ordered = reconcile_flat(
        positions=[],
        open_orders=[LiveOpenOrder(symbol="BTCUSDT", order_id="1", client_oid="client-1")],
    )

    assert flat.status == "FLAT"
    assert positioned.status == "BLOCKED_RECONCILIATION"
    assert "EXISTING_POSITION" in positioned.blockers
    assert ordered.status == "BLOCKED_RECONCILIATION"
    assert "EXISTING_OPEN_ORDER" in ordered.blockers


def test_reduce_only_close_order_uses_opposite_side() -> None:
    long_close = build_reduce_only_close_order(
        LivePosition(symbol="BTCUSDT", hold_side="long", total=Decimal("0.01"))
    )
    short_close = build_reduce_only_close_order(
        LivePosition(symbol="BTCUSDT", hold_side="short", total=Decimal("0.02"))
    )

    assert long_close.side == "sell"
    assert long_close.reduce_only is True
    assert short_close.side == "buy"
    assert short_close.reduce_only is True
