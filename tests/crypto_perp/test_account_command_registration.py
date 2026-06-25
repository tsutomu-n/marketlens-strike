from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_account import register_crypto_perp_account_commands
from sis.crypto_perp.config import CryptoPerpLabConfig
from support.cli import normalized_stdout
from .test_config import valid_config_payload


def _load_config_for_cli(config_path: Path) -> tuple[CryptoPerpLabConfig, Path]:
    return CryptoPerpLabConfig.model_validate(valid_config_payload()), config_path


def _env_enabled(name: str) -> bool:
    return False


def _utc_now() -> datetime:
    return datetime(2026, 6, 21, 6, 0, tzinfo=timezone.utc)


def test_crypto_perp_account_command_registers_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_account_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--config" in stdout
    assert "--fixture" in stdout


def test_crypto_perp_account_command_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_account_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    command = get_command(app)
    option_names = {
        option
        for parameter in command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--config" in option_names
    assert "--out" in option_names
    assert "--fixture" in option_names
    assert "--no-fixture" in option_names


def test_crypto_perp_account_command_writes_fixture_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "account"
    app = typer.Typer()
    register_crypto_perp_account_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    result = CliRunner().invoke(app, ["--out", str(out)])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "network_attempted=false" in stdout
    assert "credentials_used=false" in stdout
    assert "status=pass" in stdout
    assert f"account_snapshot_path={(out / 'account_snapshot.json').as_posix()}" in stdout
    payload = json.loads((out / "account_snapshot.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crypto_perp_account_snapshot.v1"
    assert payload["boundary"]["exchange_write_used"] is False
    assert payload["credential_scope_attestation"]["trade_enabled"] is False


def test_crypto_perp_account_command_blocks_no_fixture_without_env(tmp_path: Path) -> None:
    app = typer.Typer()
    register_crypto_perp_account_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    result = CliRunner().invoke(
        app,
        [
            "--config",
            str(tmp_path / "config.yaml"),
            "--out",
            str(tmp_path / "account"),
            "--no-fixture",
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "network_attempted=false" in stdout
    assert "status=blocked" in stdout
    assert "block_reason=CREDENTIALED_READ_OPT_IN_REQUIRED" in stdout
    assert not (tmp_path / "account").exists()
