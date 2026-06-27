from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.commands.crypto_perp_account import build_fixture_account_snapshot
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)
from sis.crypto_perp.tiny_live_shadow import build_tiny_live_shadow


REPO_ROOT = Path(__file__).resolve().parents[2]


def _account():
    return build_fixture_account_snapshot(
        utc_now_fn=lambda: datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc),
    )


def _preview(notional: Decimal = Decimal("25")):
    account = _account()
    return build_order_preview(
        request=OrderPreviewRequest(
            event_id="event-1",
            decision_id="decision-1",
            symbol="BTCUSDT",
            product_type="USDT-FUTURES",
            side="buy",
            position_side="one_way",
            order_type="limit",
            margin_mode="isolated",
            margin_coin="USDT",
            requested_notional_usd=notional,
            reference_price=Decimal("100"),
            limit_price=Decimal("100"),
            leverage=1,
        ),
        constraints=InstrumentOrderConstraints(
            symbol="BTCUSDT",
            product_type="USDT-FUTURES",
            price_multiplier=Decimal("0.1"),
            size_multiplier=Decimal("0.001"),
            min_order_amount=Decimal("5"),
            min_order_qty=Decimal("0.001"),
            max_market_order_qty=Decimal("10"),
        ),
        account_snapshot=account,
        created_at="2026-06-27T10:00:00Z",
    )


def test_tiny_live_shadow_never_permits_live_order_or_exchange_write() -> None:
    account = _account()
    preview = _preview()

    shadow = build_tiny_live_shadow(
        account_snapshot=account,
        order_preview=preview,
        created_at="2026-06-27T10:01:00Z",
    )

    assert shadow.exchange_write_used is False
    assert shadow.live_order_submitted is False
    assert shadow.permits_live_order is False
    assert shadow.boundary.exchange_write_used is False
    assert shadow.boundary.live_order_submitted is False
    assert shadow.preflight_status == "PASS"


def test_tiny_live_shadow_blocks_notional_above_25_usd_and_matches_schema() -> None:
    account = _account()
    preview = _preview(Decimal("30"))

    shadow = build_tiny_live_shadow(
        account_snapshot=account,
        order_preview=preview,
        created_at="2026-06-27T10:01:00Z",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_tiny_live_shadow.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert shadow.preflight_status == "BLOCKED"
    assert "TINY_LIVE_SHADOW_FAILED_requested_notional_within_shadow_cap" in shadow.blockers
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(shadow.model_dump(mode="json"))
