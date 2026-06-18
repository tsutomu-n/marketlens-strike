from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_scale_decision.models import ScaleDecisionPolicy
from sis.strategy_scale_decision.service import (
    StrategyScaleDecisionError,
    StrategyScaleDecisionOutputExistsError,
    build_strategy_scale_decision,
)


def register_strategy_scale_decision_commands(app: typer.Typer) -> None:
    @app.command("strategy-scale-decision")
    def strategy_scale_decision_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        live_observation: Path = typer.Option(
            ...,
            "--live-observation",
            dir_okay=False,
            help="strategy_live_observation_manifest.v1 JSON.",
        ),
        micro_live_plan: Path | None = typer.Option(
            None,
            "--micro-live-plan",
            dir_okay=False,
            help="Optional strategy_micro_live_plan.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_scale_decisions"),
            "--out",
            help="Output root for scale decision artifacts.",
        ),
        decision_id: str | None = typer.Option(None, "--decision-id", help="Optional decision id."),
        require_actual_fill: bool = typer.Option(
            False,
            "--require-actual-fill/--no-require-actual-fill",
            help="Require an actual fill before human scale review.",
        ),
        require_cancel_or_close_observed: bool = typer.Option(
            True,
            "--require-cancel-or-close-observed/--no-require-cancel-or-close-observed",
            help="Require cancel or close safety observation.",
        ),
        allow_rejection: bool = typer.Option(
            False,
            "--allow-rejection/--no-allow-rejection",
            help="Allow canary rejection without revise/retire recommendation.",
        ),
        allow_blocked_canary: bool = typer.Option(
            False,
            "--allow-blocked-canary/--no-allow-blocked-canary",
            help="Allow blocked canary without repair/hold recommendation.",
        ),
        allow_max_loss_breach: bool = typer.Option(
            False,
            "--allow-max-loss-breach/--no-allow-max-loss-breach",
            help="Allow max loss breach without revise recommendation.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing scale decision artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_scale_decision(
                strategy_id=strategy_id,
                live_observation_path=_resolve_workspace_path(live_observation, settings.data_dir),
                micro_live_plan_path=(
                    _resolve_workspace_path(micro_live_plan, settings.data_dir)
                    if micro_live_plan is not None
                    else None
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                decision_id=decision_id,
                policy=ScaleDecisionPolicy(
                    require_actual_fill=require_actual_fill,
                    require_cancel_or_close_observed=require_cancel_or_close_observed,
                    allow_rejection=allow_rejection,
                    allow_blocked_canary=allow_blocked_canary,
                    allow_max_loss_breach=allow_max_loss_breach,
                ),
                replace_existing=replace_existing,
            )
        except (
            StrategyScaleDecisionOutputExistsError,
            StrategyScaleDecisionError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        decision = result.decision
        typer.echo("status=pass")
        typer.echo(f"decision_status={decision.decision_status.value}")
        typer.echo(f"recommended_action={decision.recommended_action.value}")
        typer.echo(f"strategy_id={decision.strategy_id}")
        typer.echo(f"decision_path={result.decision_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
