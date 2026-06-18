from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_micro_live_plan.models import MicroLiveMonitoringPlan
from sis.strategy_next_scale_plan.models import NextScaleGuardPolicy, NextScaleRiskLimits
from sis.strategy_next_scale_plan.service import (
    StrategyNextScalePlanError,
    StrategyNextScalePlanOutputExistsError,
    build_strategy_next_scale_plan,
)


def _symbols(value: str) -> list[str]:
    symbols = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not symbols:
        raise typer.BadParameter("allowed symbols must not be empty")
    return list(dict.fromkeys(symbols))


def register_strategy_next_scale_plan_commands(app: typer.Typer) -> None:
    @app.command("strategy-next-scale-plan")
    def strategy_next_scale_plan_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        scale_decision: Path = typer.Option(
            ...,
            "--scale-decision",
            dir_okay=False,
            help="strategy_scale_decision.v1 JSON.",
        ),
        micro_live_plan: Path | None = typer.Option(
            None,
            "--micro-live-plan",
            dir_okay=False,
            help="Previous strategy_micro_live_plan.v1 JSON for multiplier guard.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_next_scale_plans"),
            "--out",
            help="Output root for next scale plan artifacts.",
        ),
        plan_id: str | None = typer.Option(None, "--plan-id", help="Optional plan id."),
        next_max_order_notional_usd: float = typer.Option(
            ...,
            "--next-max-order-notional-usd",
            help="Next maximum order notional in USD.",
        ),
        next_max_position_notional_usd: float = typer.Option(
            ...,
            "--next-max-position-notional-usd",
            help="Next maximum position notional in USD.",
        ),
        next_max_daily_loss_usd: float = typer.Option(
            ...,
            "--next-max-daily-loss-usd",
            help="Next maximum daily loss in USD.",
        ),
        next_max_total_loss_usd: float = typer.Option(
            ...,
            "--next-max-total-loss-usd",
            help="Next maximum total loss in USD.",
        ),
        next_max_open_positions: int = typer.Option(
            ...,
            "--next-max-open-positions",
            help="Next maximum open positions.",
        ),
        allowed_symbols: str = typer.Option(
            ...,
            "--allowed-symbols",
            help="Comma-separated allowed symbols.",
        ),
        session_window: str = typer.Option(..., "--session-window", help="Session window."),
        monitoring_owner: str = typer.Option(
            ...,
            "--monitoring-owner",
            help="Human monitoring owner.",
        ),
        monitoring_cadence: str = typer.Option(
            ...,
            "--monitoring-cadence",
            help="Monitoring cadence.",
        ),
        schedule_cancel_procedure: str = typer.Option(
            ...,
            "--schedule-cancel-procedure",
            help="Schedule cancel procedure.",
        ),
        kill_switch_procedure: str = typer.Option(
            ...,
            "--kill-switch-procedure",
            help="Kill switch procedure.",
        ),
        max_scale_multiplier: float = typer.Option(
            2.0,
            "--max-scale-multiplier",
            help="Maximum allowed multiplier versus previous micro live plan risk limits.",
        ),
        require_previous_micro_live_plan: bool = typer.Option(
            True,
            "--require-previous-micro-live-plan/--no-require-previous-micro-live-plan",
            help="Require previous micro live plan for multiplier guard.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing next scale plan artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_next_scale_plan(
                strategy_id=strategy_id,
                scale_decision_path=_resolve_workspace_path(scale_decision, settings.data_dir),
                micro_live_plan_path=(
                    _resolve_workspace_path(micro_live_plan, settings.data_dir)
                    if micro_live_plan is not None
                    else None
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                plan_id=plan_id,
                risk_limits=NextScaleRiskLimits(
                    next_max_order_notional_usd=next_max_order_notional_usd,
                    next_max_position_notional_usd=next_max_position_notional_usd,
                    next_max_daily_loss_usd=next_max_daily_loss_usd,
                    next_max_total_loss_usd=next_max_total_loss_usd,
                    next_max_open_positions=next_max_open_positions,
                    allowed_symbols=_symbols(allowed_symbols),
                    session_window=session_window,
                ),
                monitoring_plan=MicroLiveMonitoringPlan(
                    owner=monitoring_owner,
                    cadence=monitoring_cadence,
                    schedule_cancel_procedure=schedule_cancel_procedure,
                    kill_switch_procedure=kill_switch_procedure,
                ),
                guard_policy=NextScaleGuardPolicy(
                    max_scale_multiplier=max_scale_multiplier,
                    require_previous_micro_live_plan=require_previous_micro_live_plan,
                ),
                replace_existing=replace_existing,
            )
        except (
            StrategyNextScalePlanOutputExistsError,
            StrategyNextScalePlanError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        plan = result.plan
        typer.echo("status=pass")
        typer.echo(f"plan_status={plan.plan_status.value}")
        typer.echo(f"strategy_id={plan.strategy_id}")
        typer.echo(f"plan_path={result.plan_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
