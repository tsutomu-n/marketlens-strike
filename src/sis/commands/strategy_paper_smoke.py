from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_paper_smoke.models import PaperSmokePlanStatus
from sis.strategy_paper_smoke.service import (
    StrategyPaperSmokeError,
    StrategyPaperSmokeOutputExistsError,
    build_paper_smoke_plan,
)


def register_strategy_paper_smoke_commands(app: typer.Typer) -> None:
    @app.command("strategy-paper-smoke-plan")
    def strategy_paper_smoke_plan_cmd(
        stage_decision: Path = typer.Option(
            ...,
            "--stage-decision",
            help="strategy_stage_decision.v1 JSON for selected_stage=paper_smoke.",
        ),
        policy: Path = typer.Option(..., "--policy", help="strategy_stage_policy.v1 YAML/JSON."),
        out: Path = typer.Option(
            Path("data/strategy_paper_smoke"),
            "--out",
            help="Output directory for smoke plan artifacts.",
        ),
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Paper observation artifact directory used by strategy-paper-observation-cycle.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Report directory used by strategy-paper-observation-cycle.",
        ),
        session_id: str = typer.Option(..., "--session-id", help="Planned smoke session id."),
        backtest_acceptance_path: Path = typer.Option(
            Path("data/research/strategy_lifecycle/backtest_acceptance_decision.json"),
            "--backtest-acceptance-path",
            dir_okay=False,
            help="strategy backtest acceptance decision path.",
        ),
        source_pack: Path = typer.Option(
            Path("data/research/paper_candidate_pack.json"),
            "--source-pack",
            dir_okay=False,
            help="PaperCandidatePack path.",
        ),
        promotion_decision: Path = typer.Option(
            Path("data/research/promotion_decision.json"),
            "--promotion-decision",
            dir_okay=False,
            help="PromotionDecision path.",
        ),
        operator_promotion_path: Path = typer.Option(
            Path("data/research/ndx/operator_promotion_decision.json"),
            "--operator-promotion-path",
            dir_okay=False,
            help="Operator promotion decision path.",
        ),
        paper_notional_usd: float = typer.Option(1000.0, "--paper-notional-usd", min=0.01),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing smoke plan artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = build_paper_smoke_plan(
                stage_decision_path=_resolve_workspace_path(stage_decision, settings.data_dir),
                policy_path=_resolve_workspace_path(policy, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                data_dir=_resolve_workspace_path(effective_data_dir, settings.data_dir),
                artifact_dir=_resolve_workspace_path(artifact_dir, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
                session_id=session_id,
                backtest_acceptance_path=_resolve_workspace_path(
                    backtest_acceptance_path, settings.data_dir
                ),
                source_pack_path=_resolve_workspace_path(source_pack, settings.data_dir),
                promotion_decision_path=_resolve_workspace_path(
                    promotion_decision, settings.data_dir
                ),
                operator_promotion_path=_resolve_workspace_path(
                    operator_promotion_path, settings.data_dir
                ),
                paper_notional_usd=paper_notional_usd,
                replace_existing=replace_existing,
            )
        except (
            StrategyPaperSmokeOutputExistsError,
            StrategyPaperSmokeError,
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
        typer.echo(f"failed_condition_count={len(plan.failed_conditions)}")
        if plan.plan_status is not PaperSmokePlanStatus.READY_TO_RUN_SMOKE_CYCLE:
            raise typer.Exit(2)
