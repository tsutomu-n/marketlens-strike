from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_status import register_crypto_perp_status_commands
from sis.crypto_perp.config import CryptoPerpLabConfig
from support.cli import normalized_stdout
from .test_config import valid_config_payload
from .test_event_card import _event


def _load_config_for_cli(config_path: Path) -> tuple[CryptoPerpLabConfig, Path]:
    return CryptoPerpLabConfig.model_validate(valid_config_payload()), config_path


def test_crypto_perp_status_commands_register_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_status_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "crypto-perp-refresh" in stdout
    assert "crypto-perp-watchdeck" in stdout


def test_crypto_perp_status_commands_keep_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_status_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )

    root_command = get_command(app)
    refresh_command = root_command.commands["crypto-perp-refresh"]
    refresh_options = {
        option
        for parameter in refresh_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }
    watchdeck_command = root_command.commands["crypto-perp-watchdeck"]
    watchdeck_options = {
        option
        for parameter in watchdeck_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--config" in refresh_options
    assert "--through" in refresh_options
    assert "--config" in watchdeck_options
    assert "--event" in watchdeck_options
    assert "--top" in watchdeck_options


def test_crypto_perp_refresh_command_preserves_blocker_mapping(tmp_path: Path) -> None:
    app = typer.Typer()
    register_crypto_perp_status_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )

    result = CliRunner().invoke(
        app,
        [
            "crypto-perp-refresh",
            "--config",
            str(tmp_path / "config.yaml"),
            "--through",
            "events",
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "config_id=bitget-personal-edge-lab" in stdout
    assert "status=blocked" in stdout
    assert "block_reason=event_refresh_not_implemented_m04" in stdout


def test_crypto_perp_watchdeck_command_renders_event_without_config(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(_event().model_dump_json(indent=2) + "\n", encoding="utf-8")
    app = typer.Typer()
    register_crypto_perp_status_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )

    result = CliRunner().invoke(
        app,
        [
            "crypto-perp-watchdeck",
            "--event",
            str(event_path),
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "BTCUSDT slow_pump_74h_v1" in stdout
    assert "REVERSAL_SHORT" not in stdout
