from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import typer

from sis.crypto_perp.bitget.account import (
    CredentialScopeAttestation,
    CryptoPerpAccountSnapshot,
    build_account_snapshot,
)
from sis.crypto_perp.bitget.auth import missing_bitget_credential_env
from sis.crypto_perp.config import CryptoPerpLabConfig
from sis.crypto_perp.io import write_json_artifact


def _fixture_credential_attestation(
    *,
    utc_now_fn: Callable[[], datetime],
) -> CredentialScopeAttestation:
    return CredentialScopeAttestation(
        read_enabled=True,
        trade_enabled=False,
        withdrawal_disabled_confirmed=True,
        ip_restriction_confirmed=True,
        attested_by="local-fixture",
        attested_at=utc_now_fn(),
    )


def build_fixture_account_snapshot(
    *,
    utc_now_fn: Callable[[], datetime],
) -> CryptoPerpAccountSnapshot:
    return build_account_snapshot(
        observed_at=utc_now_fn(),
        account_payload={
            "marginCoin": "USDT",
            "available": "100",
            "accountEquity": "100",
            "unrealizedPL": "0",
            "marginMode": "isolated",
            "posMode": "one_way_mode",
        },
        positions_payload=[],
        open_orders_payload=[],
        credential_scope_attestation=_fixture_credential_attestation(
            utc_now_fn=utc_now_fn,
        ),
    )


def register_crypto_perp_account_commands(
    app: typer.Typer,
    *,
    load_config_for_cli_fn: Callable[[Path], tuple[CryptoPerpLabConfig, Path]],
    env_enabled_fn: Callable[[str], bool],
    utc_now_fn: Callable[[], datetime],
) -> None:
    @app.command("crypto-perp-account-probe")
    def crypto_perp_account_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/account_probe"),
            "--out",
            help="Output directory for account snapshot artifacts.",
        ),
        fixture: bool = typer.Option(
            True,
            "--fixture/--no-fixture",
            help="Use a local read-only fixture. Real credentialed network read is blocked in M08.",
        ),
    ) -> None:
        lab_config, _resolved = load_config_for_cli_fn(config)
        if not fixture:
            env_name = lab_config.network_policy.credentialed_read_env_var
            typer.echo(f"config_id={lab_config.config_id}")
            if not env_enabled_fn(env_name):
                typer.echo("network_attempted=false")
                typer.echo("status=blocked")
                typer.echo("block_reason=CREDENTIALED_READ_OPT_IN_REQUIRED")
                raise typer.Exit(2)
            missing = missing_bitget_credential_env()
            if missing:
                typer.echo("network_attempted=false")
                typer.echo("status=blocked")
                typer.echo(f"missing_env={','.join(missing)}")
                raise typer.Exit(2)
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo("block_reason=CREDENTIALED_READ_NETWORK_NOT_IMPLEMENTED_M08")
            raise typer.Exit(2)

        snapshot = build_fixture_account_snapshot(utc_now_fn=utc_now_fn)
        path = out / "account_snapshot.json"
        write_json_artifact(path, snapshot.model_dump(mode="json"))
        typer.echo("network_attempted=false")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"account_snapshot_id={snapshot.account_snapshot_id}")
        typer.echo(f"account_snapshot_path={path.as_posix()}")
