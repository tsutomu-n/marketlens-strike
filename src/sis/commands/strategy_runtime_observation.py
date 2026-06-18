from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_runtime_observation.models import (
    RuntimeObservationIngestStatus,
    RuntimeObservationSourceStage,
)
from sis.strategy_runtime_observation.service import (
    StrategyRuntimeObservationError,
    StrategyRuntimeObservationOutputExistsError,
    ingest_runtime_observation,
)


def register_strategy_runtime_observation_commands(app: typer.Typer) -> None:
    @app.command("strategy-runtime-observation-ingest")
    def strategy_runtime_observation_ingest_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        session_manifest: Path = typer.Option(
            ...,
            "--session-manifest",
            dir_okay=False,
            help="paper_observation_session_manifest.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/runtime_observations"),
            "--out",
            help="Output directory for runtime observation artifacts.",
        ),
        source_stage: RuntimeObservationSourceStage = typer.Option(
            RuntimeObservationSourceStage.PAPER_SMOKE,
            "--source-stage",
            help="Source stage for the runtime observation.",
        ),
        ledger: Path | None = typer.Option(
            None,
            "--ledger",
            dir_okay=False,
            help="Optional paper observation ledger JSONL. Defaults to manifest observation_ledger_path.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing runtime observation artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = ingest_runtime_observation(
                strategy_id=strategy_id,
                session_manifest_path=_resolve_workspace_path(session_manifest, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                source_stage=source_stage,
                ledger_path=(
                    _resolve_workspace_path(ledger, settings.data_dir)
                    if ledger is not None
                    else None
                ),
                replace_existing=replace_existing,
            )
        except (
            StrategyRuntimeObservationOutputExistsError,
            StrategyRuntimeObservationError,
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
        typer.echo(f"session_id={manifest.session_id}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        typer.echo(f"ledger_path={result.ledger_path.as_posix()}")
        typer.echo(f"ledger_entry_count={manifest.summary.ledger_entry_count}")
        if manifest.ingest_status is RuntimeObservationIngestStatus.BLOCKED_BOUNDARY_VIOLATION:
            raise typer.Exit(2)
