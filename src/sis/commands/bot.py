from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer

from sis.bot.preview import build_bot_preview
from sis.settings import get_settings


def register_bot_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("bot-preview")
    def bot_preview_cmd(
        output_dir: Path | None = typer.Option(
            None,
            "--output-dir",
            help="Base data directory for reading artifacts and writing bot preview outputs.",
        ),
        fail_on_not_ready: bool = typer.Option(
            False,
            "--fail-on-not-ready",
            help="Exit 2 when required read-only artifacts or phase gate readiness are missing.",
        ),
    ) -> None:
        """Build a read-only HOLD preview; no wallet, signing, or exchange writes."""
        settings = get_settings()
        data_dir = output_dir or settings.data_dir
        result = build_bot_preview(data_dir)
        typer.echo(f"decision={result.decision}")
        typer.echo(f"decision_path={result.decision_path}")
        typer.echo(f"report_path={result.report_path}")
        typer.echo(f"reason_codes={','.join(result.reason_codes)}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        if fail_on_not_ready and not result.ready_for_bot_logic:
            raise typer.Exit(code=2)
