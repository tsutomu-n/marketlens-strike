from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_micro_live_plan.models import (
    MicroLiveMonitoringPlan,
    MicroLivePlanStatus,
    MicroLiveRiskLimits,
)
from sis.strategy_micro_live_plan.service import (
    StrategyMicroLivePlanError,
    StrategyMicroLivePlanOutputExistsError,
    build_strategy_micro_live_plan,
)


def register_strategy_micro_live_plan_commands(app: typer.Typer) -> None:
    @app.command("strategy-micro-live-plan")
    def strategy_micro_live_plan_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        stage_decision: Path = typer.Option(
            ..., "--stage-decision", dir_okay=False, help="strategy_stage_decision.v1 JSON."
        ),
        drift_review: Path = typer.Option(
            ..., "--drift-review", dir_okay=False, help="paper_vs_backtest_drift_review.v1 JSON."
        ),
        human_approval: Path | None = typer.Option(
            None,
            "--human-approval",
            dir_okay=False,
            help="Optional human approval JSON artifact for micro live planning.",
        ),
        micro_live_policy: Path | None = typer.Option(
            None,
            "--micro-live-policy",
            dir_okay=False,
            help="Optional existing configs/micro_live_policy.yaml to cross-check risk limits.",
        ),
        max_order_notional_usd: float = typer.Option(..., "--max-order-notional-usd"),
        max_position_notional_usd: float = typer.Option(..., "--max-position-notional-usd"),
        max_daily_loss_usd: float = typer.Option(..., "--max-daily-loss-usd"),
        max_total_loss_usd: float = typer.Option(..., "--max-total-loss-usd"),
        max_open_positions: int = typer.Option(..., "--max-open-positions"),
        allowed_symbol: list[str] | None = typer.Option(
            None, "--allowed-symbol", help="Allowed symbol. Repeat for multiple symbols."
        ),
        session_window: str = typer.Option(..., "--session-window"),
        monitoring_owner: str = typer.Option(..., "--monitoring-owner"),
        monitoring_cadence: str = typer.Option(..., "--monitoring-cadence"),
        schedule_cancel_procedure: str = typer.Option(..., "--schedule-cancel-procedure"),
        kill_switch_procedure: str = typer.Option(..., "--kill-switch-procedure"),
        out: Path = typer.Option(
            Path("data/strategy_micro_live_plans"),
            "--out",
            help="Output root for micro live plan artifacts.",
        ),
        plan_id: str | None = typer.Option(None, "--plan-id", help="Optional plan id."),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing plan artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            risk_limits = MicroLiveRiskLimits(
                max_order_notional_usd=max_order_notional_usd,
                max_position_notional_usd=max_position_notional_usd,
                max_daily_loss_usd=max_daily_loss_usd,
                max_total_loss_usd=max_total_loss_usd,
                max_open_positions=max_open_positions,
                allowed_symbols=allowed_symbol or [],
                session_window=session_window,
            )
            monitoring_plan = MicroLiveMonitoringPlan(
                owner=monitoring_owner,
                cadence=monitoring_cadence,
                schedule_cancel_procedure=schedule_cancel_procedure,
                kill_switch_procedure=kill_switch_procedure,
            )
            result = build_strategy_micro_live_plan(
                strategy_id=strategy_id,
                stage_decision_path=_resolve_workspace_path(stage_decision, settings.data_dir),
                drift_review_path=_resolve_workspace_path(drift_review, settings.data_dir),
                human_approval_path=(
                    _resolve_workspace_path(human_approval, settings.data_dir)
                    if human_approval is not None
                    else None
                ),
                micro_live_policy_path=(
                    _resolve_workspace_path(micro_live_policy, settings.data_dir)
                    if micro_live_policy is not None
                    else None
                ),
                risk_limits=risk_limits,
                monitoring_plan=monitoring_plan,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                plan_id=plan_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyMicroLivePlanOutputExistsError,
            StrategyMicroLivePlanError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        plan = result.plan
        if plan.plan_status is MicroLivePlanStatus.READY_FOR_HUMAN_MICRO_LIVE_REVIEW:
            typer.echo("status=needs_human_approval")
            typer.echo("requires_explicit_approval=true")
        else:
            typer.echo("status=blocked")
            typer.echo("requires_explicit_approval=false")
        typer.echo("permits_live_order=false")
        typer.echo(f"plan_id={plan.plan_id}")
        typer.echo(f"strategy_id={plan.strategy_id}")
        typer.echo(f"plan_status={plan.plan_status.value}")
        typer.echo(f"micro_live_execution_allowed={plan.micro_live_execution_allowed}")
        typer.echo(f"plan_path={result.plan_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
