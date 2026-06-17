from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_review.operator_review import (
    OperatorReviewDecision,
    OperatorReviewRecordError,
    OperatorReviewOutputExistsError,
    record_operator_review,
    validate_existing_operator_review,
)
from sis.strategy_review.manifest import ReviewStatus
from sis.strategy_review.service import (
    StrategyReviewBuildError,
    StrategyReviewOutputExistsError,
    build_strategy_review,
)


def register_strategy_review_commands(app: typer.Typer) -> None:
    @app.command("strategy-review-build")
    def strategy_review_build_cmd(
        review_id: str = typer.Option(..., "--review-id", help="Review id path segment."),
        out: Path = typer.Option(
            Path("data/strategy_reviews"),
            "--out",
            help="Output strategy review directory root.",
        ),
        pack_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack.json"),
            "--pack-path",
            help="Strategy backtest pack manifest JSON.",
        ),
        validation_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack_validation.json"),
            "--validation-path",
            help="Strategy backtest pack validation JSON.",
        ),
        authoring_spec: Path | None = typer.Option(
            None,
            "--authoring-spec",
            help="Optional Strategy Authoring YAML spec. Defaults to pack spec_path when available.",
        ),
        lifecycle_review: Path = typer.Option(
            Path("data/research/strategy_lifecycle/strategy_lifecycle_review.json"),
            "--lifecycle-review",
            help="Optional strategy lifecycle review JSON.",
        ),
        strict: bool = typer.Option(
            False,
            "--strict/--no-strict",
            help="Exit 2 when required artifacts are missing.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace an existing review output directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_review(
                review_id=review_id,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                pack_path=_resolve_workspace_path(pack_path, settings.data_dir),
                validation_path=_resolve_workspace_path(validation_path, settings.data_dir),
                authoring_spec_path=(
                    _resolve_workspace_path(authoring_spec, settings.data_dir)
                    if authoring_spec is not None
                    else None
                ),
                lifecycle_review_path=_resolve_workspace_path(lifecycle_review, settings.data_dir),
                strict=strict,
                replace_existing=replace_existing,
            )
        except StrategyReviewOutputExistsError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        except StrategyReviewBuildError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc

        typer.echo(f"review_status={result.manifest.review_status.value}")
        typer.echo(f"review_dir={result.manifest.paths.review_dir}")
        typer.echo(f"manifest_path={result.manifest.paths.manifest_path}")
        typer.echo(f"markdown_path={result.manifest.paths.review_markdown_path}")
        typer.echo(f"missing_required_count={result.manifest.summary.missing_required_count}")
        typer.echo(f"invalid_required_count={result.manifest.summary.invalid_required_count}")
        typer.echo(f"boundary_violation_count={result.manifest.summary.boundary_violation_count}")
        if result.manifest.review_status in {
            ReviewStatus.INVALID_INPUT,
            ReviewStatus.BLOCKED_BOUNDARY_VIOLATION,
        }:
            raise typer.Exit(2)
        if strict and result.manifest.review_status is ReviewStatus.INCOMPLETE_ARTIFACTS:
            raise typer.Exit(2)

    @app.command("strategy-review-record")
    def strategy_review_record_cmd(
        review_dir: Path = typer.Option(
            ...,
            "--review-dir",
            help="Existing strategy review directory containing review.md and review_manifest.json.",
        ),
        decision: OperatorReviewDecision | None = typer.Option(
            None,
            "--decision",
            help="Operator decision to record.",
        ),
        reviewer: str | None = typer.Option(
            None,
            "--reviewer",
            help="Human reviewer identifier.",
        ),
        rationale: str | None = typer.Option(
            None,
            "--rationale",
            help="Human-readable review rationale.",
        ),
        required_action: list[str] | None = typer.Option(
            None,
            "--required-action",
            help="Required follow-up action. Repeat for multiple actions.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace an existing operator_review.yaml.",
        ),
        validate_existing: bool = typer.Option(
            False,
            "--validate-existing/--no-validate-existing",
            help="Validate existing operator_review.yaml against current review.md and manifest.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_review_dir = _resolve_workspace_path(review_dir, settings.data_dir)
        try:
            if validate_existing:
                result = validate_existing_operator_review(review_dir=resolved_review_dir)
            else:
                if decision is None:
                    raise OperatorReviewRecordError(
                        "--decision is required unless --validate-existing is used"
                    )
                if reviewer is None:
                    raise OperatorReviewRecordError(
                        "--reviewer is required unless --validate-existing is used"
                    )
                if rationale is None:
                    raise OperatorReviewRecordError(
                        "--rationale is required unless --validate-existing is used"
                    )
                result = record_operator_review(
                    review_dir=resolved_review_dir,
                    reviewer=reviewer,
                    decision=decision,
                    rationale=rationale,
                    required_actions=required_action,
                    replace_existing=replace_existing,
                )
        except (
            OperatorReviewOutputExistsError,
            OperatorReviewRecordError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"operator_review_path={result.operator_review_path.as_posix()}")
        typer.echo(f"decision={result.operator_review.decision.value}")
