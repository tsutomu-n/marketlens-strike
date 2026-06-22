from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_case_lite.service import (
    StrategyCaseLiteError,
    StrategyCaseLiteOutputExistsError,
    build_strategy_case_lite,
)


def register_strategy_case_lite_commands(app: typer.Typer) -> None:
    @app.command("strategy-case-lite-update")
    def strategy_case_lite_update_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        stage_decision: list[Path] | None = typer.Option(
            None,
            "--stage-decision",
            dir_okay=False,
            help="strategy_stage_decision.v1 JSON. Repeat for multiple artifacts.",
        ),
        runtime_observation: list[Path] | None = typer.Option(
            None,
            "--runtime-observation",
            dir_okay=False,
            help="strategy_runtime_observation_manifest.v1 JSON. Repeat for multiple artifacts.",
        ),
        drift_review: list[Path] | None = typer.Option(
            None,
            "--drift-review",
            dir_okay=False,
            help="paper_vs_backtest_drift_review.v1 JSON. Repeat for multiple artifacts.",
        ),
        learning_event: list[Path] | None = typer.Option(
            None,
            "--learning-event",
            dir_okay=False,
            help="strategy_learning_event.v1 JSON. Repeat for multiple artifacts.",
        ),
        revision_request: list[Path] | None = typer.Option(
            None,
            "--revision-request",
            dir_okay=False,
            help="strategy_revision_request.v1 JSON. Repeat for multiple artifacts.",
        ),
        authoring_handoff: list[Path] | None = typer.Option(
            None,
            "--authoring-handoff",
            dir_okay=False,
            help="strategy_authoring_update_handoff.v1 JSON. Repeat for multiple artifacts.",
        ),
        micro_live_plan: list[Path] | None = typer.Option(
            None,
            "--micro-live-plan",
            dir_okay=False,
            help="strategy_micro_live_plan.v1 JSON. Repeat for multiple artifacts.",
        ),
        live_observation: list[Path] | None = typer.Option(
            None,
            "--live-observation",
            dir_okay=False,
            help="strategy_live_observation_manifest.v1 JSON. Repeat for multiple artifacts.",
        ),
        scale_decision: list[Path] | None = typer.Option(
            None,
            "--scale-decision",
            dir_okay=False,
            help="strategy_scale_decision.v1 JSON. Repeat for multiple artifacts.",
        ),
        next_scale_plan: list[Path] | None = typer.Option(
            None,
            "--next-scale-plan",
            dir_okay=False,
            help="strategy_next_scale_plan.v1 JSON. Repeat for multiple artifacts.",
        ),
        artifact: list[Path] | None = typer.Option(
            None,
            "--artifact",
            dir_okay=False,
            help=(
                "Additional JSON artifact. Known schemas are typed; "
                "unknown schemas are recorded as generic."
            ),
        ),
        out: Path = typer.Option(
            Path("data/strategy_cases"),
            "--out",
            help="Output root for Strategy Case Lite artifacts.",
        ),
        case_id: str | None = typer.Option(
            None,
            "--case-id",
            help="Optional case id. Defaults to strategy id.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing case artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        raw_paths = [
            *(stage_decision or []),
            *(runtime_observation or []),
            *(drift_review or []),
            *(learning_event or []),
            *(revision_request or []),
            *(authoring_handoff or []),
            *(micro_live_plan or []),
            *(live_observation or []),
            *(scale_decision or []),
            *(next_scale_plan or []),
            *(artifact or []),
        ]
        try:
            result = build_strategy_case_lite(
                strategy_id=strategy_id,
                artifact_paths=[
                    _resolve_workspace_path(path, settings.data_dir) for path in raw_paths
                ],
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                case_id=case_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyCaseLiteOutputExistsError,
            StrategyCaseLiteError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        case = result.case
        typer.echo("status=pass")
        typer.echo(f"case_id={case.case_id}")
        typer.echo(f"strategy_id={case.strategy_id}")
        typer.echo(f"latest_status={case.summary.latest_status or ''}")
        typer.echo(f"artifact_count={case.summary.artifact_count}")
        typer.echo(f"case_path={result.case_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
