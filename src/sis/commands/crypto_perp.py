from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.crypto_perp.bitget.probe import run_provider_probe
from sis.crypto_perp.config import load_crypto_perp_lab_config
from sis.crypto_perp.event_card import build_event_card
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import ConfigValidationArtifact, CryptoPerpProducer, stable_hash
from sis.crypto_perp.reason_codes import CryptoPerpReasonCode
from sis.crypto_perp.rendering import render_event_card_markdown
from sis.settings import get_settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _config_hash(config_path: Path) -> str:
    return "sha256:" + stable_hash([config_path.read_text(encoding="utf-8")])


def _load_config_for_cli(config_path: Path):
    settings = get_settings()
    resolved = _resolve_workspace_path(config_path, settings.data_dir)
    return load_crypto_perp_lab_config(resolved), resolved


def _write_config_validation(config_path: Path, out_dir: Path) -> ConfigValidationArtifact:
    config, resolved = _load_config_for_cli(config_path)
    artifact = ConfigValidationArtifact(
        artifact_id=stable_hash(
            ["crypto-perp-config-validate", config.config_id, _config_hash(resolved)]
        ),
        created_at=_utc_now(),
        producer=CryptoPerpProducer(command="crypto-perp-config-validate"),
        config_id=config.config_id,
        config_hash=_config_hash(resolved),
    )
    payload = artifact.model_dump(mode="json")
    write_json_artifact(out_dir / "config_validation.json", payload)
    write_text_artifact(
        out_dir / "config_validation.md",
        "\n".join(
            [
                "# Crypto Perp Config Validation",
                "",
                f"- config_id: `{artifact.config_id}`",
                f"- validation_status: `{artifact.validation_status}`",
                "- boundary: all normal flags false",
            ]
        ),
    )
    return artifact


def _env_enabled(name: str) -> bool:
    return os.getenv(name) == "1"


def register_crypto_perp_commands(app: typer.Typer) -> None:
    @app.command("crypto-perp-config-validate")
    def crypto_perp_config_validate_cmd(
        config: Path = typer.Option(
            ...,
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/config_validation"),
            "--out",
            help="Output directory for config validation artifacts.",
        ),
    ) -> None:
        try:
            artifact = _write_config_validation(config, out)
        except (ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"config_id={artifact.config_id}")
        typer.echo(f"validation_status={artifact.validation_status}")
        typer.echo(f"validation_path={(out / 'config_validation.json').as_posix()}")
        typer.echo(f"report_path={(out / 'config_validation.md').as_posix()}")

    @app.command("crypto-perp-probe")
    def crypto_perp_probe_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/crypto_perp/provider_probe"),
            "--out",
            help="Output directory for provider probe artifacts.",
        ),
        raw_root: Path = typer.Option(
            Path("data/crypto_perp/raw"),
            "--raw-root",
            help="Root directory for immutable raw public snapshots.",
        ),
        network: bool = typer.Option(
            False,
            "--network/--no-network",
            help="Attempt public network only when env opt-in is also set.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        env_name = lab_config.network_policy.public_network_env_var
        typer.echo(f"config_id={lab_config.config_id}")
        if not network or not _env_enabled(env_name):
            typer.echo("network_attempted=false")
            typer.echo("status=blocked")
            typer.echo(f"block_reason={CryptoPerpReasonCode.PUBLIC_NETWORK_OPT_IN_REQUIRED.value}")
            raise typer.Exit(2)
        try:
            result = run_provider_probe(
                config=lab_config,
                out_dir=out,
                raw_root=raw_root,
                network_attempted=True,
                started_at=_utc_now(),
            )
        except Exception as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("network_attempted=true")
        typer.echo("credentials_used=false")
        typer.echo("status=pass")
        typer.echo(f"probe_id={result.probe.probe_id}")
        typer.echo(f"probe_path={result.probe_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("crypto-perp-refresh")
    def crypto_perp_refresh_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        through: str = typer.Option(
            "config",
            "--through",
            help="Refresh stage. M01 supports config only; later tasks add probe/events.",
        ),
    ) -> None:
        lab_config, _resolved = _load_config_for_cli(config)
        typer.echo(f"config_id={lab_config.config_id}")
        if through == "config":
            typer.echo("status=pass")
            typer.echo("through=config")
            return
        typer.echo("status=blocked")
        block_reason = (
            CryptoPerpReasonCode.EVENT_REFRESH_NOT_IMPLEMENTED_M04
            if through == "events"
            else CryptoPerpReasonCode.MARKET_REFRESH_NOT_IMPLEMENTED_M02
        )
        typer.echo(f"block_reason={block_reason.value}")
        raise typer.Exit(2)

    @app.command("crypto-perp-watchdeck")
    def crypto_perp_watchdeck_cmd(
        config: Path = typer.Option(
            Path("configs/crypto_perp/bitget_personal_edge_lab.yaml"),
            "--config",
            help="crypto_perp_lab_config.v1 YAML/JSON.",
        ),
        event_path: Path | None = typer.Option(
            None,
            "--event",
            help="Render a crypto_perp_event.v1 JSON artifact as an event card.",
        ),
        top: int = typer.Option(20, "--top", help="Maximum cards to display."),
    ) -> None:
        if event_path is not None:
            try:
                event_payload = json.loads(event_path.read_text(encoding="utf-8"))
                event = CryptoPerpEvent.model_validate(event_payload)
            except Exception as exc:
                typer.echo("status=fail")
                typer.echo(f"error={exc}")
                raise typer.Exit(2) from exc
            typer.echo(render_event_card_markdown(build_event_card(event)))
            return

        lab_config, _resolved = _load_config_for_cli(config)
        if top <= 0:
            typer.echo("status=fail")
            typer.echo("error=top must be positive")
            raise typer.Exit(2)
        typer.echo(f"config_id={lab_config.config_id}")
        typer.echo("status=blocked")
        typer.echo(f"block_reason={CryptoPerpReasonCode.WATCHDECK_NOT_IMPLEMENTED_M04.value}")
        raise typer.Exit(2)
