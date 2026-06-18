from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_live_observation.service import (
    StrategyLiveObservationError,
    StrategyLiveObservationOutputExistsError,
    ingest_strategy_live_observation,
)


def register_strategy_live_observation_commands(app: typer.Typer) -> None:
    @app.command("strategy-live-observation-ingest")
    def strategy_live_observation_ingest_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        audit_bundle: Path = typer.Option(
            ...,
            "--audit-bundle",
            dir_okay=False,
            help="Existing micro live canary audit bundle JSON.",
        ),
        report: Path | None = typer.Option(
            None,
            "--report",
            dir_okay=False,
            help="Optional existing micro live canary Markdown report.",
        ),
        micro_live_plan: Path | None = typer.Option(
            None,
            "--micro-live-plan",
            dir_okay=False,
            help="Optional strategy_micro_live_plan.v1 JSON source.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_live_observations"),
            "--out",
            help="Output root for live observation artifacts.",
        ),
        observation_id: str | None = typer.Option(
            None,
            "--observation-id",
            help="Optional observation id. Defaults to <strategy-id>-live-observation.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing live observation artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = ingest_strategy_live_observation(
                strategy_id=strategy_id,
                audit_bundle_path=_resolve_workspace_path(audit_bundle, settings.data_dir),
                report_path=(
                    _resolve_workspace_path(report, settings.data_dir)
                    if report is not None
                    else None
                ),
                micro_live_plan_path=(
                    _resolve_workspace_path(micro_live_plan, settings.data_dir)
                    if micro_live_plan is not None
                    else None
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                observation_id=observation_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyLiveObservationOutputExistsError,
            StrategyLiveObservationError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        manifest = result.manifest
        typer.echo("status=pass")
        typer.echo(f"ingest_status={manifest.ingest_status.value}")
        typer.echo(f"strategy_id={manifest.strategy_id}")
        typer.echo(f"observation_id={manifest.observation_id}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
