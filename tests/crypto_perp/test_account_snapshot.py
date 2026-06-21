from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.bitget.account import (
    CredentialScopeAttestation,
    build_account_snapshot,
    measurement_readiness_blockers,
)
from support.cli import normalized_stdout


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _attestation(trade_enabled: bool = False) -> CredentialScopeAttestation:
    return CredentialScopeAttestation(
        read_enabled=True,
        trade_enabled=trade_enabled,
        withdrawal_disabled_confirmed=True,
        ip_restriction_confirmed=True,
        attested_by="operator",
        attested_at="2026-06-21T06:00:00Z",
    )


def _account_payload(margin_mode: str = "isolated") -> dict[str, object]:
    return {
        "marginCoin": "USDT",
        "available": "100.5",
        "accountEquity": "125.25",
        "unrealizedPL": "0",
        "marginMode": margin_mode,
        "posMode": "one_way_mode",
    }


def test_account_snapshot_requires_isolated_flat_and_no_open_order() -> None:
    snapshot = build_account_snapshot(
        observed_at="2026-06-21T06:00:00Z",
        account_payload=_account_payload(),
        positions_payload=[],
        open_orders_payload=[],
        credential_scope_attestation=_attestation(),
    )

    assert snapshot.account_equity_usd == Decimal("125.25")
    assert snapshot.available_usd == Decimal("100.5")
    assert snapshot.margin_mode == "isolated"
    assert measurement_readiness_blockers(snapshot) == []

    crossed = snapshot.model_copy(update={"margin_mode": "crossed"})
    positioned = snapshot.model_copy(
        update={
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "hold_side": "long",
                    "total": Decimal("0.01"),
                    "available": Decimal("0.01"),
                    "margin_mode": "isolated",
                }
            ]
        }
    )
    with_open_order = snapshot.model_copy(
        update={
            "open_orders": [
                {
                    "symbol": "BTCUSDT",
                    "order_id": "1",
                    "client_oid": "client-1",
                    "side": "buy",
                    "size": Decimal("0.01"),
                    "reduce_only": False,
                }
            ]
        }
    )
    trade_enabled = snapshot.model_copy(
        update={"credential_scope_attestation": _attestation(trade_enabled=True)}
    )

    assert "MARGIN_MODE_NOT_ISOLATED" in measurement_readiness_blockers(crossed)
    assert "EXISTING_POSITION" in measurement_readiness_blockers(positioned)
    assert "EXISTING_OPEN_ORDER" in measurement_readiness_blockers(with_open_order)
    assert "CREDENTIAL_NOT_READ_ONLY" in measurement_readiness_blockers(trade_enabled)


def test_account_snapshot_dump_matches_schema_and_contains_no_secret() -> None:
    snapshot = build_account_snapshot(
        observed_at="2026-06-21T06:00:00Z",
        account_payload=_account_payload(),
        positions_payload=[],
        open_orders_payload=[],
        credential_scope_attestation=_attestation(),
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_account_snapshot.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    payload = snapshot.model_dump(mode="json")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert "api_key" not in json.dumps(payload)
    assert "api_secret" not in json.dumps(payload)
    assert "passphrase" not in json.dumps(payload)


def test_crypto_perp_account_probe_cli_writes_fixture_snapshot(tmp_path: Path) -> None:
    result = runner.invoke(app, ["crypto-perp-account-probe", "--out", str(tmp_path)])
    stdout = normalized_stdout(result)
    payload = json.loads((tmp_path / "account_snapshot.json").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert "network_attempted=false" in stdout
    assert "credentials_used=false" in stdout
    assert payload["schema_version"] == "crypto_perp_account_snapshot.v1"
    assert payload["boundary"]["exchange_write_used"] is False
