from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_order_preview import register_crypto_perp_order_preview_commands
from support.cli import normalized_stdout


def _utc_now() -> datetime:
    return datetime(2026, 6, 21, 6, 1, tzinfo=timezone.utc)


def test_crypto_perp_order_preview_command_registers_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_order_preview_commands(app, utc_now_fn=_utc_now)

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--account-snapshot" in stdout
    assert "--limit-price" in stdout


def test_crypto_perp_order_preview_command_keeps_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_order_preview_commands(app, utc_now_fn=_utc_now)

    command = get_command(app)
    option_names = {
        option
        for parameter in command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--out" in option_names
    assert "--account-snapshot" in option_names
    assert "--event-id" in option_names
    assert "--decision-id" in option_names
    assert "--symbol" in option_names
    assert "--side" in option_names
    assert "--position-side" in option_names
    assert "--notional-usd" in option_names
    assert "--reference-price" in option_names
    assert "--limit-price" in option_names


def test_crypto_perp_order_preview_command_writes_standalone_artifact(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    app = typer.Typer()
    register_crypto_perp_order_preview_commands(app, utc_now_fn=_utc_now)

    result = CliRunner().invoke(
        app,
        [
            "--out",
            str(out),
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

    assert result.exit_code == 0
    assert "network_attempted=false" in stdout
    assert "exchange_write_used=false" in stdout
    assert "status=pass" in stdout
    assert "would_submit_order=false" in stdout
    assert f"order_preview_path={(out / 'order_preview.json').as_posix()}" in stdout
    payload = json.loads((out / "order_preview.json").read_text(encoding="utf-8"))
    assert payload["preview_status"] == "READY"
    assert payload["would_submit_order"] is False
    assert payload["normalized_limit_price"] == "100.1"


def test_crypto_perp_order_preview_command_rejects_invalid_side(tmp_path: Path) -> None:
    out = tmp_path / "preview"
    app = typer.Typer()
    register_crypto_perp_order_preview_commands(app, utc_now_fn=_utc_now)

    result = CliRunner().invoke(
        app,
        [
            "--out",
            str(out),
            "--side",
            "hold",
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "status=fail" in stdout
    assert "error=side must be buy or sell" in stdout
    assert not (out / "order_preview.json").exists()
