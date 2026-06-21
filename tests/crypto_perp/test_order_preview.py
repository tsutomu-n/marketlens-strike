from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.bitget.account import CredentialScopeAttestation, build_account_snapshot
from sis.crypto_perp.idempotency import CLIENT_OID_PATTERN, build_client_oid
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)
from support.cli import normalized_stdout


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _account(open_order: bool = False):
    return build_account_snapshot(
        observed_at="2026-06-21T06:00:00Z",
        account_payload={
            "marginCoin": "USDT",
            "available": "100",
            "accountEquity": "100",
            "unrealizedPL": "0",
            "marginMode": "isolated",
            "posMode": "one_way_mode",
        },
        positions_payload=[],
        open_orders_payload=[
            {
                "symbol": "BTCUSDT",
                "orderId": "1",
                "clientOid": "client-1",
                "side": "buy",
                "size": "0.01",
                "reduceOnly": "NO",
            }
        ]
        if open_order
        else [],
        credential_scope_attestation=CredentialScopeAttestation(
            read_enabled=True,
            trade_enabled=False,
            withdrawal_disabled_confirmed=True,
            ip_restriction_confirmed=True,
            attested_by="operator",
            attested_at="2026-06-21T06:00:00Z",
        ),
    )


def _constraints() -> InstrumentOrderConstraints:
    return InstrumentOrderConstraints(
        symbol="BTCUSDT",
        product_type="USDT-FUTURES",
        price_multiplier=Decimal("0.1"),
        size_multiplier=Decimal("0.001"),
        min_order_amount=Decimal("5"),
        min_order_qty=Decimal("0.001"),
        max_market_order_qty=Decimal("10"),
    )


def _request() -> OrderPreviewRequest:
    return OrderPreviewRequest(
        event_id="event-1",
        decision_id="decision-1",
        symbol="BTCUSDT",
        product_type="USDT-FUTURES",
        side="buy",
        position_side="one_way",
        order_type="limit",
        margin_mode="isolated",
        margin_coin="USDT",
        requested_notional_usd=Decimal("25"),
        reference_price=Decimal("100"),
        limit_price=Decimal("100.19"),
        leverage=2,
    )


def test_client_oid_is_deterministic_and_valid() -> None:
    first = build_client_oid(
        event_id="event-1",
        decision_id="decision-1",
        symbol="BTCUSDT",
        side="buy",
        position_side="one_way",
    )
    second = build_client_oid(
        event_id="event-1",
        decision_id="decision-1",
        symbol="BTCUSDT",
        side="buy",
        position_side="one_way",
    )

    assert first == second
    assert len(first) <= 32
    assert CLIENT_OID_PATTERN.fullmatch(first)


def test_order_preview_rounds_and_cannot_submit_order() -> None:
    preview = build_order_preview(
        request=_request(),
        constraints=_constraints(),
        account_snapshot=_account(),
        created_at="2026-06-21T06:01:00Z",
    )

    assert preview.preview_status == "READY"
    assert preview.normalized_limit_price == Decimal("100.1")
    assert preview.normalized_qty == Decimal("0.249")
    assert preview.normalized_notional_usd == Decimal("24.9249")
    assert preview.would_submit_order is False
    assert not hasattr(preview, "submit")


def test_order_preview_blocks_when_account_not_flat() -> None:
    preview = build_order_preview(
        request=_request(),
        constraints=_constraints(),
        account_snapshot=_account(open_order=True),
        created_at="2026-06-21T06:01:00Z",
    )

    assert preview.preview_status == "BLOCKED"
    assert "EXISTING_OPEN_ORDER" in preview.reason_codes
    assert preview.would_submit_order is False


def test_order_preview_dump_matches_schema() -> None:
    preview = build_order_preview(
        request=_request(),
        constraints=_constraints(),
        account_snapshot=_account(),
        created_at="2026-06-21T06:01:00Z",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_order_preview.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(preview.model_dump(mode="json"))


def test_crypto_perp_order_preview_cli_writes_non_writing_preview(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "crypto-perp-order-preview",
            "--out",
            str(tmp_path),
            "--event-id",
            "event-1",
            "--decision-id",
            "decision-1",
            "--notional-usd",
            "25",
            "--reference-price",
            "100",
            "--limit-price",
            "100.19",
        ],
    )
    stdout = normalized_stdout(result)
    payload = json.loads((tmp_path / "order_preview.json").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert "exchange_write_used=false" in stdout
    assert "would_submit_order=false" in stdout
    assert payload["would_submit_order"] is False
    assert payload["preview_status"] == "READY"
