from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click
import typer
from typer.main import get_command
from typer.testing import CliRunner

from sis.commands.crypto_perp_probe import register_crypto_perp_probe_commands
from sis.crypto_perp.bitget.probe import run_provider_probe
from sis.crypto_perp.config import CryptoPerpLabConfig
from support.cli import normalized_stdout
from .test_config import valid_config_payload
from .test_provider_probe import _transport


def _load_config_for_cli(config_path: Path) -> tuple[CryptoPerpLabConfig, Path]:
    return CryptoPerpLabConfig.model_validate(valid_config_payload()), config_path


def _env_enabled(name: str) -> bool:
    return False


def _utc_now() -> datetime:
    return datetime(2026, 6, 21, 4, 30, tzinfo=timezone.utc)


def test_crypto_perp_probe_commands_register_standalone() -> None:
    app = typer.Typer()
    register_crypto_perp_probe_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    result = CliRunner().invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "crypto-perp-probe" in stdout
    assert "crypto-perp-probe-audit" in stdout


def test_crypto_perp_probe_commands_keep_core_options() -> None:
    app = typer.Typer()
    register_crypto_perp_probe_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    root_command = get_command(app)
    probe_command = root_command.commands["crypto-perp-probe"]
    probe_options = {
        option
        for parameter in probe_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }
    audit_command = root_command.commands["crypto-perp-probe-audit"]
    audit_options = {
        option
        for parameter in audit_command.params
        if isinstance(parameter, click.Option)
        for option in [*parameter.opts, *parameter.secondary_opts]
    }

    assert "--config" in probe_options
    assert "--out" in probe_options
    assert "--raw-root" in probe_options
    assert "--network" in probe_options
    assert "--probe" in audit_options
    assert "--out" in audit_options
    assert "--check-raw-exists" in audit_options


def test_crypto_perp_probe_command_blocks_without_env_opt_in(tmp_path: Path) -> None:
    app = typer.Typer()
    register_crypto_perp_probe_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    result = CliRunner().invoke(
        app,
        [
            "crypto-perp-probe",
            "--config",
            str(tmp_path / "config.yaml"),
            "--out",
            str(tmp_path / "probe"),
            "--raw-root",
            str(tmp_path / "raw"),
            "--network",
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "network_attempted=false" in stdout
    assert "status=blocked" in stdout
    assert "block_reason=public_network_opt_in_required" in stdout
    assert not (tmp_path / "raw").exists()


def test_crypto_perp_probe_audit_command_writes_standalone_artifacts(tmp_path: Path) -> None:
    config = CryptoPerpLabConfig.model_validate(valid_config_payload())
    probe_result = run_provider_probe(
        config=config,
        out_dir=tmp_path / "data/crypto_perp/provider_probe",
        raw_root=tmp_path / "data/crypto_perp/raw",
        transport=_transport(),
        network_attempted=True,
        started_at="2026-06-21T04:30:00Z",
    )
    out = tmp_path / "audit"
    app = typer.Typer()
    register_crypto_perp_probe_commands(
        app,
        load_config_for_cli_fn=_load_config_for_cli,
        env_enabled_fn=_env_enabled,
        utc_now_fn=_utc_now,
    )

    result = CliRunner().invoke(
        app,
        [
            "crypto-perp-probe-audit",
            "--probe",
            str(probe_result.probe_path),
            "--out",
            str(out),
        ],
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, stdout
    assert "network_attempted=false" in stdout
    assert "exchange_write_used=false" in stdout
    assert "audit_status=READY_FOR_EVENT_REFRESH" in stdout
    assert f"probe_audit_path={(out / 'probe_audit.json').as_posix()}" in stdout
    assert f"report_path={(out / 'probe_audit.md').as_posix()}" in stdout
    payload = json.loads((out / "probe_audit.json").read_text(encoding="utf-8"))
    assert payload["audit_status"] == "READY_FOR_EVENT_REFRESH"
    assert "- exchange_write_used: `false`" in (out / "probe_audit.md").read_text(encoding="utf-8")
