from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_learning.service import (
    StrategyLearningError,
    StrategyLearningOutputExistsError,
    build_authoring_update_handoff,
    build_revision_request,
    record_revision_request_review,
    update_learning_ledger,
)
from sis.strategy_learning.models import RevisionRequestReviewDecision


def register_strategy_learning_commands(app: typer.Typer) -> None:
    @app.command("strategy-learning-ledger-update")
    def strategy_learning_ledger_update_cmd(
        drift_review: Path = typer.Option(
            ...,
            "--drift-review",
            dir_okay=False,
            help="paper_vs_backtest_drift_review.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_learning"),
            "--out",
            help="Output root for strategy learning artifacts.",
        ),
        strategy_id: str | None = typer.Option(
            None,
            "--strategy-id",
            help="Optional strategy id. Defaults to the drift review strategy_id.",
        ),
        learning_event_id: str | None = typer.Option(
            None,
            "--learning-event-id",
            help="Optional learning event id. Defaults to a stable id from source hash.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing learning event and ledger row with the same id.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = update_learning_ledger(
                drift_review_path=_resolve_workspace_path(drift_review, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                strategy_id=strategy_id,
                learning_event_id=learning_event_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyLearningOutputExistsError,
            StrategyLearningError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        event = result.event
        typer.echo("status=pass")
        typer.echo(f"learning_event_id={event.learning_event_id}")
        typer.echo(f"strategy_id={event.strategy_id}")
        typer.echo(f"event_type={event.event_type.value}")
        typer.echo(f"recommended_action={event.recommended_action.value}")
        typer.echo(f"event_path={result.event_path.as_posix()}")
        typer.echo(f"ledger_path={result.ledger_path.as_posix()}")
        typer.echo(f"summary_path={result.summary_path.as_posix()}")

    @app.command("strategy-revision-request-build")
    def strategy_revision_request_build_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        learning_ledger: Path = typer.Option(
            ...,
            "--learning-ledger",
            dir_okay=False,
            help="strategy learning ledger JSONL.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_learning/revision_requests"),
            "--out",
            help="Output directory for revision request artifacts.",
        ),
        revision_request_id: str | None = typer.Option(
            None,
            "--revision-request-id",
            help="Optional revision request id. Defaults to a stable id from ledger hash.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing revision request artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_revision_request(
                strategy_id=strategy_id,
                learning_ledger_path=_resolve_workspace_path(learning_ledger, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                revision_request_id=revision_request_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyLearningOutputExistsError,
            StrategyLearningError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        request = result.request
        typer.echo("status=pass")
        typer.echo(f"revision_request_id={request.revision_request_id}")
        typer.echo(f"strategy_id={request.strategy_id}")
        typer.echo(f"request_status={request.request_status.value}")
        typer.echo(f"reason={request.reason}")
        typer.echo(f"request_path={result.request_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("strategy-revision-request-review")
    def strategy_revision_request_review_cmd(
        revision_request: Path = typer.Option(
            ...,
            "--revision-request",
            dir_okay=False,
            help="strategy_revision_request.v1 JSON.",
        ),
        decision: RevisionRequestReviewDecision = typer.Option(
            ...,
            "--decision",
            help="Human decision for this revision request.",
        ),
        reviewer: str = typer.Option(..., "--reviewer", help="Human reviewer identifier."),
        rationale: str = typer.Option(..., "--rationale", help="Human-readable rationale."),
        required_action: list[str] | None = typer.Option(
            None,
            "--required-action",
            help="Required follow-up action. Repeat for multiple actions.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            help="Output directory. Defaults to the revision request directory.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing revision request review artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = record_revision_request_review(
                revision_request_path=_resolve_workspace_path(revision_request, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir)
                if out is not None
                else None,
                reviewer=reviewer,
                decision=decision,
                rationale=rationale,
                required_actions=required_action,
                replace_existing=replace_existing,
            )
        except (
            StrategyLearningOutputExistsError,
            StrategyLearningError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        review = result.review
        typer.echo("status=pass")
        typer.echo(f"revision_request_id={review.revision_request_id}")
        typer.echo(f"strategy_id={review.strategy_id}")
        typer.echo(f"decision={review.decision.value}")
        typer.echo(
            f"authoring_update_input_allowed={str(review.authoring_update_input_allowed).lower()}"
        )
        typer.echo(f"review_path={result.review_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("strategy-authoring-update-handoff")
    def strategy_authoring_update_handoff_cmd(
        revision_request: Path = typer.Option(
            ...,
            "--revision-request",
            dir_okay=False,
            help="strategy_revision_request.v1 JSON.",
        ),
        revision_review: Path = typer.Option(
            ...,
            "--revision-review",
            dir_okay=False,
            help="strategy_revision_request_review.v1 JSON.",
        ),
        authoring_spec: Path = typer.Option(
            ...,
            "--authoring-spec",
            dir_okay=False,
            help="Current Strategy Authoring YAML/JSON to update by separate human edit.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_learning/authoring_update_handoffs"),
            "--out",
            help="Output directory for authoring update handoff artifacts.",
        ),
        handoff_id: str | None = typer.Option(
            None,
            "--handoff-id",
            help="Optional handoff id. Defaults to a stable id from review hash.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing authoring update handoff artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_authoring_update_handoff(
                revision_request_path=_resolve_workspace_path(revision_request, settings.data_dir),
                revision_review_path=_resolve_workspace_path(revision_review, settings.data_dir),
                authoring_spec_path=_resolve_workspace_path(authoring_spec, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                handoff_id=handoff_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyLearningOutputExistsError,
            StrategyLearningError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        handoff = result.handoff
        typer.echo("status=pass")
        typer.echo(f"handoff_id={handoff.handoff_id}")
        typer.echo(f"revision_request_id={handoff.revision_request_id}")
        typer.echo(f"strategy_id={handoff.strategy_id}")
        typer.echo(f"handoff_status={handoff.handoff_status.value}")
        typer.echo(f"review_decision={handoff.review_decision.value}")
        typer.echo(f"auto_applied={str(handoff.auto_applied).lower()}")
        typer.echo(f"handoff_path={result.handoff_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
