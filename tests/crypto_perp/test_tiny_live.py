from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.bitget.account import CredentialScopeAttestation, build_account_snapshot
from sis.crypto_perp.order_preview import (
    InstrumentOrderConstraints,
    OrderPreviewRequest,
    build_order_preview,
)
from sis.crypto_perp.tiny_live import (
    TINY_LIVE_CONFIRMATION_PHRASE,
    OrderCreateTimeout,
    build_mock_tiny_live_measurement,
    submit_entry_with_query_before_resubmit,
    tiny_live_preflight_blockers,
)
from support.cli import normalized_stdout


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _account(position: bool = False, open_order: bool = False, trade_enabled: bool = True):
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
        positions_payload=[
            {
                "symbol": "BTCUSDT",
                "holdSide": "long",
                "total": "0.01",
                "available": "0.01",
                "marginMode": "isolated",
            }
        ]
        if position
        else [],
        open_orders_payload=[
            {
                "symbol": "BTCUSDT",
                "orderId": "1",
                "clientOid": "client-1",
                "side": "buy",
                "size": "0.01",
            }
        ]
        if open_order
        else [],
        credential_scope_attestation=CredentialScopeAttestation(
            read_enabled=True,
            trade_enabled=trade_enabled,
            withdrawal_disabled_confirmed=True,
            ip_restriction_confirmed=True,
            attested_by="operator",
            attested_at="2026-06-21T06:00:00Z",
        ),
    )


def _preview(account=None, notional: Decimal = Decimal("25")):
    account = account or _account(trade_enabled=False)
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
        created_at="2026-06-21T06:01:00Z",
    )


def test_tiny_live_preflight_requires_all_live_gates() -> None:
    account = _account()
    preview = _preview()

    assert (
        tiny_live_preflight_blockers(
            env={"SIS_ENABLE_TINY_LIVE_MEASUREMENT": "1"},
            confirm_live=True,
            confirmation_phrase=TINY_LIVE_CONFIRMATION_PHRASE,
            account_snapshot=account,
            order_preview=preview,
        )
        == []
    )

    blockers = tiny_live_preflight_blockers(
        env={},
        confirm_live=False,
        confirmation_phrase="wrong",
        account_snapshot=_account(position=True, open_order=True),
        order_preview=_preview(notional=Decimal("25.01")),
    )

    assert "TINY_LIVE_ENV_NOT_ENABLED" in blockers
    assert "CONFIRM_LIVE_FLAG_MISSING" in blockers
    assert "CONFIRMATION_PHRASE_MISMATCH" in blockers
    assert "NOTIONAL_ABOVE_25_USD" in blockers
    assert "EXISTING_POSITION" in blockers
    assert "EXISTING_OPEN_ORDER" in blockers


class TimeoutThenFoundClient:
    def __init__(self) -> None:
        self.create_calls = 0
        self.query_client_oids: list[str] = []

    def create_order(self, client_oid: str) -> dict[str, str]:
        self.create_calls += 1
        raise OrderCreateTimeout(client_oid)

    def query_order(self, client_oid: str) -> dict[str, str]:
        self.query_client_oids.append(client_oid)
        return {"order_id": "order-1", "status": "ACKNOWLEDGED"}


def test_timeout_uses_query_before_resubmit() -> None:
    preview = _preview(_account())
    client = TimeoutThenFoundClient()

    step = submit_entry_with_query_before_resubmit(client=client, order_preview=preview)

    assert client.create_calls == 1
    assert client.query_client_oids == [preview.client_oid]
    assert step.status == "ACKNOWLEDGED_AFTER_QUERY"
    assert step.query_before_resubmit is True
    assert step.resubmitted is False


def test_mock_tiny_live_measurement_dump_matches_schema() -> None:
    account = _account()
    preview = _preview()
    measurement = build_mock_tiny_live_measurement(
        env={"SIS_ENABLE_TINY_LIVE_MEASUREMENT": "1"},
        confirm_live=True,
        confirmation_phrase=TINY_LIVE_CONFIRMATION_PHRASE,
        account_snapshot=account,
        order_preview=preview,
        measured_at="2026-06-21T06:02:00Z",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_live_measurement.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    payload = measurement.model_dump(mode="json")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["execution_mode"] == "mock"
    assert payload["live_order_submitted"] is False
    assert payload["auto_trading_enabled"] is False
    assert payload["close_order"]["reduce_only"] is True
    assert payload["flat_reconciliation"]["status"] == "FLAT"


def test_tiny_live_cli_mock_requires_explicit_confirmation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SIS_ENABLE_TINY_LIVE_MEASUREMENT", "1")
    result = runner.invoke(
        app,
        [
            "crypto-perp-tiny-live-measurement",
            "--mock",
            "--confirm-live",
            "--confirmation-phrase",
            TINY_LIVE_CONFIRMATION_PHRASE,
            "--out",
            str(tmp_path),
        ],
    )
    stdout = normalized_stdout(result)
    payload = json.loads((tmp_path / "live_measurement.json").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert "execution_mode=mock" in stdout
    assert "live_order_submitted=false" in stdout
    assert payload["live_order_submitted"] is False
