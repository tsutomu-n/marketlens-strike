from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_input_feedback.models import StrategyInputFeedbackReviewDecision
from sis.strategy_input_feedback.service import (
    StrategyInputFeedbackError,
    StrategyInputFeedbackOutputExistsError,
    build_input_feedback_proposal,
    build_input_feedback_review,
)


def register_strategy_input_feedback_commands(app: typer.Typer) -> None:
    @app.command("strategy-input-feedback-proposal-build")
    def strategy_input_feedback_proposal_build_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        runtime_observation: list[Path] | None = typer.Option(
            None,
            "--runtime-observation",
            dir_okay=False,
            help="strategy_runtime_observation_manifest.v1 JSON. Repeatable.",
        ),
        learning_event: list[Path] | None = typer.Option(
            None,
            "--learning-event",
            dir_okay=False,
            help="strategy_learning_event.v1 JSON. Repeatable.",
        ),
        source_contract: Path | None = typer.Option(
            None,
            "--source-contract",
            dir_okay=False,
            help="Optional strategy_input_contract.v1 JSON/YAML context.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_input_feedback"),
            "--out",
            help="Output root for Strategy Input Feedback artifacts.",
        ),
        proposal_id: str | None = typer.Option(
            None,
            "--proposal-id",
            help="Optional proposal id. Defaults to a stable id from source hashes.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing proposal artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_input_feedback_proposal(
                strategy_id=strategy_id,
                runtime_observation_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (runtime_observation or [])
                ],
                learning_event_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (learning_event or [])
                ],
                source_contract_path=(
                    _resolve_workspace_path(source_contract, settings.data_dir)
                    if source_contract is not None
                    else None
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                proposal_id=proposal_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyInputFeedbackOutputExistsError,
            StrategyInputFeedbackError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        proposal = result.proposal
        typer.echo("status=pass")
        typer.echo(f"proposal_id={proposal.proposal_id}")
        typer.echo(f"strategy_id={proposal.strategy_id}")
        typer.echo(f"proposal_status={proposal.status.value}")
        typer.echo(f"proposed_change_count={len(proposal.proposed_changes)}")
        typer.echo(f"auto_applied={str(proposal.auto_applied).lower()}")
        typer.echo(
            f"direct_contract_edit_allowed={str(proposal.direct_contract_edit_allowed).lower()}"
        )
        typer.echo(f"proposal_path={result.proposal_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("strategy-input-feedback-proposal-review")
    def strategy_input_feedback_proposal_review_cmd(
        proposal: Path = typer.Option(
            ...,
            "--proposal",
            dir_okay=False,
            help="strategy_input_contract_update_proposal.v1 JSON.",
        ),
        decision: StrategyInputFeedbackReviewDecision = typer.Option(
            ...,
            "--decision",
            help="Human review decision.",
        ),
        reviewer: str = typer.Option(..., "--reviewer", help="Reviewer identifier."),
        rationale: str = typer.Option(..., "--rationale", help="Review rationale."),
        approved_change_id: list[str] | None = typer.Option(
            None,
            "--approved-change-id",
            help="Approved change id. Repeatable.",
        ),
        required_action: list[str] | None = typer.Option(
            None,
            "--required-action",
            help="Required follow-up action. Repeatable.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            help="Output directory. Defaults to the proposal directory.",
        ),
        review_id: str | None = typer.Option(
            None,
            "--review-id",
            help="Optional review id. Defaults to <proposal-id>-review.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing review artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_input_feedback_review(
                proposal_path=_resolve_workspace_path(proposal, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir)
                if out is not None
                else None,
                reviewer=reviewer,
                decision=decision,
                rationale=rationale,
                approved_change_ids=approved_change_id or [],
                required_actions=required_action or [],
                review_id=review_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyInputFeedbackOutputExistsError,
            StrategyInputFeedbackError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        review = result.review
        typer.echo("status=pass")
        typer.echo(f"review_id={review.review_id}")
        typer.echo(f"proposal_id={review.proposal_id}")
        typer.echo(f"strategy_id={review.strategy_id}")
        typer.echo(f"decision={review.decision.value}")
        typer.echo(
            f"manual_contract_update_input_allowed="
            f"{str(review.manual_contract_update_input_allowed).lower()}"
        )
        typer.echo(f"auto_applied={str(review.auto_applied).lower()}")
        typer.echo(
            f"direct_contract_edit_allowed={str(review.direct_contract_edit_allowed).lower()}"
        )
        typer.echo(f"review_path={result.review_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
