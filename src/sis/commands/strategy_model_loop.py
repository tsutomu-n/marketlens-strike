from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_model_loop.models import ModelOutputRoute
from sis.strategy_model_loop.service import (
    StrategyModelLoopError,
    StrategyModelLoopOutputExistsError,
    build_strategy_model_run,
    parse_json_object,
)


def register_strategy_model_loop_commands(app: typer.Typer) -> None:
    @app.command("strategy-model-run-record")
    def strategy_model_run_record_cmd(
        strategy_id: str = typer.Option(..., "--strategy-id", help="Strategy id."),
        training_data: Path = typer.Option(
            ...,
            "--training-data",
            dir_okay=False,
            help="Training data artifact path.",
        ),
        label_definition: str = typer.Option(
            ...,
            "--label-definition",
            help="Label definition used by the model or optimizer.",
        ),
        split: str = typer.Option(
            ...,
            "--split",
            help="Train/validation/holdout split description.",
        ),
        search_space_json: str = typer.Option(
            ...,
            "--search-space-json",
            help="JSON object describing the search space.",
        ),
        trial_json: list[str] = typer.Option(
            ...,
            "--trial-json",
            help="Trial JSON object. Repeat for all completed, failed, pruned, and running trials.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_model_loop"),
            "--out",
            help="Output directory for model loop artifacts.",
        ),
        model_run_id: str = typer.Option(
            "strategy-model-run",
            "--model-run-id",
            help="Model run id.",
        ),
        ledger_id: str = typer.Option(
            "strategy-optimizer-trial-ledger",
            "--ledger-id",
            help="Optimizer trial ledger id.",
        ),
        seed: int | None = typer.Option(None, "--seed", help="Random seed, if applicable."),
        best_trial_id: str | None = typer.Option(
            None,
            "--best-trial-id",
            help="Best trial id. Must reference a recorded trial.",
        ),
        holdout_result_json: str | None = typer.Option(
            None,
            "--holdout-result-json",
            help="JSON object describing holdout result.",
        ),
        limitation: list[str] | None = typer.Option(
            None,
            "--limitation",
            help="Known limitation. Repeat for multiple limitations.",
        ),
        output_route: ModelOutputRoute = typer.Option(
            ModelOutputRoute.REVISION_REQUEST_ONLY,
            "--output-route",
            help="Allowed downstream route for model / optimizer output.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing model loop artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_model_run(
                strategy_id=strategy_id,
                training_data_path=_resolve_workspace_path(training_data, settings.data_dir),
                label_definition=label_definition,
                split=split,
                search_space=parse_json_object(search_space_json, label="search space"),
                trials=[
                    parse_json_object(value, label=f"trial {index}")
                    for index, value in enumerate(trial_json, start=1)
                ],
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                model_run_id=model_run_id,
                ledger_id=ledger_id,
                seed=seed,
                best_trial_id=best_trial_id,
                holdout_result=parse_json_object(holdout_result_json, label="holdout result")
                if holdout_result_json is not None
                else None,
                limitations=limitation,
                output_route=output_route,
                replace_existing=replace_existing,
            )
        except (
            StrategyModelLoopOutputExistsError,
            StrategyModelLoopError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        model_run = result.model_run
        ledger = result.trial_ledger
        typer.echo("status=pass")
        typer.echo(f"model_run_id={model_run.model_run_id}")
        typer.echo(f"strategy_id={model_run.strategy_id}")
        typer.echo(f"trial_count={ledger.summary.trial_count}")
        typer.echo(f"failed_count={ledger.summary.failed_count}")
        typer.echo(f"success_only_reporting={str(ledger.summary.success_only_reporting).lower()}")
        typer.echo(f"model_run_path={result.model_run_path.as_posix()}")
        typer.echo(f"trial_ledger_path={result.trial_ledger_path.as_posix()}")
