from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_daily_brief.service import (
    StrategyDailyBriefError,
    StrategyDailyBriefOutputExistsError,
    build_strategy_daily_brief,
)


def register_strategy_daily_brief_commands(app: typer.Typer) -> None:
    @app.command("strategy-daily-brief")
    def strategy_daily_brief_cmd(
        data_dir: Path = typer.Option(
            Path("data"),
            "--data-dir",
            file_okay=False,
            help="Data directory to scan for strategy artifacts.",
        ),
        out: Path = typer.Option(
            Path("data/reports/strategy_daily_brief"),
            "--out",
            help="Output directory for daily brief artifacts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing daily brief artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_daily_brief(
                data_dir=_resolve_workspace_path(data_dir, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            StrategyDailyBriefOutputExistsError,
            StrategyDailyBriefError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        brief = result.brief
        typer.echo("status=pass")
        typer.echo(f"scanned_json_count={brief.summary.scanned_json_count}")
        typer.echo(f"total_item_count={brief.summary.total_item_count}")
        typer.echo(f"boundary_violation_count={brief.summary.boundary_violation_count}")
        typer.echo(f"brief_path={result.brief_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
