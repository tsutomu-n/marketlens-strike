from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_stage.models import StageDecisionStatus, StageName, StagePolicyValidationStatus
from sis.strategy_stage.service import (
    StrategyStageError,
    StrategyStageOutputExistsError,
    build_stage_decision,
    validate_stage_policy,
)


def register_strategy_stage_commands(app: typer.Typer) -> None:
    @app.command("strategy-stage-policy-validate")
    def strategy_stage_policy_validate_cmd(
        policy: Path = typer.Option(..., "--policy", help="strategy_stage_policy.v1 YAML/JSON."),
        out: Path = typer.Option(
            Path("data/strategy_stage_policies"),
            "--out",
            help="Output directory for policy validation artifacts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing validation artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = validate_stage_policy(
                policy_path=_resolve_workspace_path(policy, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            StrategyStageOutputExistsError,
            StrategyStageError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        validation = result.validation
        typer.echo("status=pass")
        typer.echo(f"validation_status={validation.validation_status.value}")
        typer.echo(f"policy_id={validation.policy_id}")
        typer.echo(f"policy_hash={validation.policy_hash}")
        typer.echo(f"validation_path={result.validation_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        if validation.validation_status is not StagePolicyValidationStatus.PASS:
            raise typer.Exit(2)

    @app.command("strategy-stage-decision")
    def strategy_stage_decision_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        stage: StageName = typer.Option(..., "--stage", help="Stage to evaluate."),
        policy: Path = typer.Option(..., "--policy", help="strategy_stage_policy.v1 YAML/JSON."),
        out: Path = typer.Option(
            Path("data/strategy_stage_decisions"),
            "--out",
            help="Output directory for stage decision artifacts.",
        ),
        profile: str = typer.Option("default", "--profile", help="Strategy profile in policy."),
        review_dir: Path | None = typer.Option(
            None,
            "--review-dir",
            help="Strategy review directory containing operator_review.yaml.",
        ),
        paper_observation_status: Path | None = typer.Option(
            None,
            "--paper-observation-status",
            help="strategy_paper_observation_status.v1 JSON.",
        ),
        reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer identifier."),
        override_reason: str | None = typer.Option(
            None,
            "--override-reason",
            help="Manual override reason. Recorded only; does not auto-pass failed evidence.",
        ),
        manual_override: list[str] | None = typer.Option(
            None,
            "--manual-override",
            help="Manual override label. Repeat for multiple labels.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing decision artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_stage_decision(
                strategy_id=strategy_id,
                stage=stage,
                policy_path=_resolve_workspace_path(policy, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                selected_profile=profile,
                review_dir=(
                    _resolve_workspace_path(review_dir, settings.data_dir)
                    if review_dir is not None
                    else None
                ),
                paper_observation_status_path=(
                    _resolve_workspace_path(paper_observation_status, settings.data_dir)
                    if paper_observation_status is not None
                    else None
                ),
                reviewer=reviewer,
                override_reason=override_reason,
                manual_overrides=manual_override,
                replace_existing=replace_existing,
            )
        except (
            StrategyStageOutputExistsError,
            StrategyStageError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        decision = result.decision
        typer.echo("status=pass")
        typer.echo(f"decision={decision.decision.value}")
        typer.echo(f"strategy_id={decision.strategy_id}")
        typer.echo(f"selected_stage={decision.selected_stage.value}")
        typer.echo(f"policy_id={decision.policy_id}")
        typer.echo(f"policy_hash={decision.policy_hash}")
        typer.echo(f"decision_path={result.decision_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        typer.echo(f"failed_condition_count={len(decision.failed_conditions)}")
        if decision.decision in {StageDecisionStatus.BLOCKED, StageDecisionStatus.NEEDS_EVIDENCE}:
            raise typer.Exit(2)
