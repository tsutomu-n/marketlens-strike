from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_drift_review.service import (
    StrategyDriftReviewError,
    StrategyDriftReviewOutputExistsError,
    build_drift_review,
)


def register_strategy_drift_review_commands(app: typer.Typer) -> None:
    @app.command("strategy-drift-review")
    def strategy_drift_review_cmd(
        backtest_result: Path = typer.Option(
            ...,
            "--backtest-result",
            dir_okay=False,
            help="strategy_authoring_backtest_result.v1 JSON.",
        ),
        runtime_observation: Path = typer.Option(
            ...,
            "--runtime-observation",
            dir_okay=False,
            help="strategy_runtime_observation_manifest.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_drift_reviews"),
            "--out",
            help="Output directory for drift review artifacts.",
        ),
        strategy_id: str | None = typer.Option(
            None,
            "--strategy-id",
            help="Optional strategy id. Defaults to source artifact strategy_id.",
        ),
        max_no_fill_rate: float = typer.Option(
            0.5,
            "--max-no-fill-rate",
            help="Maximum acceptable runtime no-fill rate for review condition.",
        ),
        max_blocked_rate: float = typer.Option(
            0.5,
            "--max-blocked-rate",
            help="Maximum acceptable runtime blocked rate for review condition.",
        ),
        max_spread_bps: float | None = typer.Option(
            None,
            "--max-spread-bps",
            help="Optional maximum observed runtime spread in bps.",
        ),
        max_return_drift: float | None = typer.Option(
            None,
            "--max-return-drift",
            help="Optional maximum absolute drift between runtime return and backtest total return.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing drift review artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_drift_review(
                strategy_id=strategy_id,
                backtest_result_path=_resolve_workspace_path(backtest_result, settings.data_dir),
                runtime_observation_path=_resolve_workspace_path(
                    runtime_observation, settings.data_dir
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                max_no_fill_rate=max_no_fill_rate,
                max_blocked_rate=max_blocked_rate,
                max_spread_bps=max_spread_bps,
                max_return_drift=max_return_drift,
                replace_existing=replace_existing,
            )
        except (
            StrategyDriftReviewOutputExistsError,
            StrategyDriftReviewError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        review = result.review
        typer.echo("status=pass")
        typer.echo(f"review_status={review.review_status.value}")
        typer.echo(f"recommended_action={review.recommended_action.value}")
        typer.echo(f"strategy_id={review.strategy_id}")
        typer.echo(f"review_path={result.review_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        if review.review_status.value == "BLOCKED_BOUNDARY_VIOLATION":
            raise typer.Exit(2)
