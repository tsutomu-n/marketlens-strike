from __future__ import annotations

from pathlib import Path

import typer

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
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
        authoring_spec_path: Path | None = typer.Option(
            None,
            "--authoring-spec-path",
            help="Optional Strategy Authoring YAML spec. Defaults to pack spec_path when available.",
        ),
        lifecycle_review_path: Path = typer.Option(
            Path("data/research/strategy_lifecycle/strategy_lifecycle_review.json"),
            "--lifecycle-review-path",
            help="Optional strategy lifecycle review JSON.",
        ),
        strict: bool = typer.Option(
            False,
            "--strict/--no-strict",
            help="Exit 2 when required artifacts are missing.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing",
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
                    _resolve_workspace_path(authoring_spec_path, settings.data_dir)
                    if authoring_spec_path is not None
                    else None
                ),
                lifecycle_review_path=_resolve_workspace_path(
                    lifecycle_review_path, settings.data_dir
                ),
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

        typer.echo(f"strategy_review={result.review_markdown_path.as_posix()}")
        typer.echo(f"strategy_review_manifest={result.manifest_path.as_posix()}")
        typer.echo(f"review_status={result.manifest.review_status.value}")
        if result.manifest.review_status in {
            ReviewStatus.INVALID_INPUT,
            ReviewStatus.BLOCKED_BOUNDARY_VIOLATION,
        }:
            raise typer.Exit(2)
        if strict and result.manifest.review_status is ReviewStatus.INCOMPLETE_ARTIFACTS:
            raise typer.Exit(2)
