from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_inputs.models import InputValidationStatus, IdeaIntakeDecision
from sis.strategy_inputs.validation import (
    StrategyInputOutputExistsError,
    StrategyInputValidationError,
    validate_strategy_input_contract,
    validate_strategy_intake,
)


def register_strategy_input_commands(app: typer.Typer) -> None:
    @app.command("strategy-input-contract-validate")
    def strategy_input_contract_validate_cmd(
        contract: Path = typer.Option(..., "--contract", help="Strategy input contract YAML/JSON."),
        out: Path = typer.Option(
            Path("data/strategy_inputs"),
            "--out",
            help="Output directory for validation artifacts.",
        ),
        strict: bool = typer.Option(
            False,
            "--strict/--no-strict",
            help="Exit 2 for NEEDS_FIX validation status.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing validation artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = validate_strategy_input_contract(
                contract_path=_resolve_workspace_path(contract, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                strict=strict,
                replace_existing=replace_existing,
            )
        except (
            StrategyInputOutputExistsError,
            StrategyInputValidationError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        validation = result.validation
        typer.echo("status=pass")
        typer.echo(f"validation_status={validation.validation_status.value}")
        typer.echo(f"contract_id={validation.contract_id}")
        typer.echo(f"validation_path={result.validation_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        typer.echo(f"missing_required_count={validation.summary.missing_required_count}")
        typer.echo(f"boundary_violation_count={validation.summary.boundary_violation_count}")
        if validation.validation_status is InputValidationStatus.BLOCKED_BOUNDARY_VIOLATION:
            raise typer.Exit(2)
        if strict and validation.validation_status is InputValidationStatus.NEEDS_FIX:
            raise typer.Exit(2)

    @app.command("strategy-intake-validate")
    def strategy_intake_validate_cmd(
        idea: Path = typer.Option(..., "--idea", help="Strategy idea YAML/JSON."),
        input_contract_validation: list[Path] = typer.Option(
            ...,
            "--input-contract-validation",
            help="Input contract validation JSON/YAML. Repeat for multiple contracts.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_ideas"),
            "--out",
            help="Output directory for intake decision artifacts.",
        ),
        strict: bool = typer.Option(
            False,
            "--strict/--no-strict",
            help="Exit 2 unless decision is READY_FOR_AUTHORING_DRAFT.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing intake decision artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = validate_strategy_intake(
                idea_path=_resolve_workspace_path(idea, settings.data_dir),
                input_contract_validation_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in input_contract_validation
                ],
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            StrategyInputOutputExistsError,
            StrategyInputValidationError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        decision = result.decision
        typer.echo("status=pass")
        typer.echo(f"decision={decision.decision.value}")
        typer.echo(f"idea_id={decision.idea_id}")
        typer.echo(f"decision_path={result.decision_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        typer.echo(f"required_action_count={len(decision.required_actions)}")
        typer.echo(f"boundary_violation_count={decision.summary.boundary_violation_count}")
        if strict and decision.decision is not IdeaIntakeDecision.READY_FOR_AUTHORING_DRAFT:
            raise typer.Exit(2)
