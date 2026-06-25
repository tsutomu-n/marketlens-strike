from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import typer

from sis.crypto_perp.config import CryptoPerpLabConfig
from sis.crypto_perp.event_card import build_event_card
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.reason_codes import CryptoPerpReasonCode
from sis.crypto_perp.rendering import render_event_card_markdown


def register_crypto_perp_status_commands(
    app: typer.Typer,
    *,
    load_config_for_cli_fn: Callable[[Path], tuple[CryptoPerpLabConfig, Path]],
) -> None:
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
        lab_config, _resolved = load_config_for_cli_fn(config)
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

        lab_config, _resolved = load_config_for_cli_fn(config)
        if top <= 0:
            typer.echo("status=fail")
            typer.echo("error=top must be positive")
            raise typer.Exit(2)
        typer.echo(f"config_id={lab_config.config_id}")
        typer.echo("status=blocked")
        typer.echo(f"block_reason={CryptoPerpReasonCode.WATCHDECK_NOT_IMPLEMENTED_M04.value}")
        raise typer.Exit(2)
