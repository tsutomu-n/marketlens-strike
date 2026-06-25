from __future__ import annotations

from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_config import register_crypto_perp_config_commands
from sis.crypto_perp.config import CryptoPerpLabConfig
from support.cli import normalized_stdout
from .test_config import valid_config_payload


def _load_config_for_cli(config_path: Path) -> tuple[CryptoPerpLabConfig, Path]:
    return CryptoPerpLabConfig.model_validate(valid_config_payload()), config_path


def test_crypto_perp_config_command_registers_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_config_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--config" in stdout
    assert "crypto_perp_lab_config.v1" in stdout


def test_crypto_perp_config_command_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_config_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
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


def test_crypto_perp_config_command_writes_standalone_artifacts(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("config: fixture\n", encoding="utf-8")
    out = tmp_path / "out"
    app = typer.Typer()
    register_crypto_perp_config_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
    )

    result = CliRunner().invoke(
        app,
        [
            "--config",
            str(config_path),
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "config_id=bitget-personal-edge-lab" in result.stdout
    assert f"validation_path={(out / 'config_validation.json').as_posix()}" in result.stdout
    assert f"report_path={(out / 'config_validation.md').as_posix()}" in result.stdout
    assert (out / "config_validation.json").exists()
    assert "- boundary: all normal flags false" in (out / "config_validation.md").read_text(
        encoding="utf-8"
    )
