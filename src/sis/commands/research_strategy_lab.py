from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import ValidationError
import typer
from loguru import logger

from sis.commands.research_strategy_lab_candidate_pack import (
    register_research_strategy_lab_candidate_pack_commands,
)
from sis.commands.research_strategy_lab_support import (
    _build_signals_or_exit,
    _candidate_selection_policy,
    _current_signal_context,
    _era_signal_counts,
    _parameter_hash,
    _parse_rank_thresholds,
    _selected_signal_rows,
    _thresholded_signal_frame,
    _trial_id_for_parameters,
)
from sis.commands.research_strategy_lab_promotion import (
    register_research_strategy_lab_promotion_commands,
)
from sis.research.signal_builder import (
    DEFAULT_GENERATOR_ID,
    build_signals_from_experiment_spec,
    load_strategy_experiment_spec,
)
from sis.research.strategy_lab.signal_artifact import require_single_signal_identity
from sis.research.strategy_lab.signal_registry import default_signal_generator_registry
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.settings import get_settings


def register_research_strategy_lab_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("build-signals")
    def build_signals_cmd(
        generator_id: str = typer.Option(
            DEFAULT_GENERATOR_ID,
            "--generator-id",
            help=(
                "Registered Strategy Lab signal generator ID. Unknown IDs exit "
                "with code 2 and print registered_generator_ids."
            ),
        ),
    ) -> None:
        """Build Strategy Lab signal artifacts from the feature panel.

        Reads data/research/feature_panel.parquet and writes
        data/research/strategy_signals.parquet,
        data/research/strategy_signal_manifest.json,
        data/research/strategy_signals.jsonl, and legacy data/research/signals.csv.
        Submits no live orders.
        """
        settings = get_settings()
        out = _build_signals_or_exit(settings.data_dir, generator_id=generator_id)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("strategy-preview")
    def strategy_preview_cmd(
        generator_id: str = typer.Option(
            DEFAULT_GENERATOR_ID,
            "--generator-id",
            help=(
                "Registered Strategy Lab signal generator ID. Unknown IDs exit "
                "with code 2 and print registered_generator_ids."
            ),
        ),
    ) -> None:
        """Build Strategy Lab signal artifacts plus a preview report.

        Reads data/research/feature_panel.parquet and writes
        data/research/strategy_signals.parquet,
        data/research/strategy_signal_manifest.json,
        data/research/strategy_signals.jsonl, legacy data/research/signals.csv,
        and data/reports/strategy_signals_preview.md. Submits no live orders.
        """
        settings = get_settings()
        legacy_path = _build_signals_or_exit(settings.data_dir, generator_id=generator_id)
        report_path = settings.data_dir / "reports/strategy_signals_preview.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Strategy Signals Preview\n\n"
            f"- generator_id: {generator_id}\n"
            f"- canonical_artifact: {settings.data_dir / 'research/strategy_signals.parquet'}\n"
            f"- legacy_export: {legacy_path}\n",
            encoding="utf-8",
        )
        typer.echo(f"legacy_export={legacy_path}")
        typer.echo(f"report_path={report_path}")

    @app.command("strategy-experiment-run")
    def strategy_experiment_run_cmd(
        spec_path: Path = typer.Option(
            ...,
            "--spec",
            help=(
                "StrategyExperimentSpec YAML/JSON file. Runs only registered "
                "generator IDs; no arbitrary Python plugin is executed."
            ),
        ),
        max_variants: int = typer.Option(
            64,
            "--max-variants",
            min=1,
            help=(
                "Maximum cartesian parameter_grid variants to materialize; "
                "exits with code 2 when exceeded."
            ),
        ),
    ) -> None:
        """Run a StrategyExperimentSpec into paper-only signal artifacts.

        Writes data/research/strategy_signals.parquet,
        data/research/strategy_signal_manifest.json, legacy data/research/signals.csv,
        and data/reports/strategy_experiment_run.md. Submits no live orders.
        """
        settings = get_settings()
        try:
            spec = load_strategy_experiment_spec(spec_path)
            legacy_path = build_signals_from_experiment_spec(
                settings.data_dir,
                spec=spec,
                max_variants=max_variants,
            )
        except KeyError as exc:
            registered = ", ".join(default_signal_generator_registry().registered_ids())
            typer.echo(f"{exc.args[0]}; registered_generator_ids={registered}")
            raise typer.Exit(2) from exc
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        report_path = settings.data_dir / "reports/strategy_experiment_run.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Strategy Experiment Run\n\n"
            f"- spec_path: {spec_path}\n"
            f"- strategy_id: {spec.strategy_id}\n"
            f"- generator_id: {spec.generator_id}\n"
            f"- max_variants: {max_variants}\n"
            f"- canonical_artifact: {settings.data_dir / 'research/strategy_signals.parquet'}\n"
            f"- legacy_export: {legacy_path}\n"
            "- paper_only: true\n"
            "- live_order_submitted: false\n",
            encoding="utf-8",
        )
        typer.echo(f"legacy_export={legacy_path}")
        typer.echo(f"report_path={report_path}")

    @app.command("evaluate-strategy-lab")
    def evaluate_strategy_lab_cmd(
        rank_thresholds: str = typer.Option(
            "",
            "--rank-thresholds",
            help=(
                "Comma-separated rank_score thresholds for paper-only parameter sweep "
                "over data/research/strategy_signals.parquet."
            ),
        ),
        candidate_limit: int = typer.Option(
            1,
            "--candidate-limit",
            min=0,
            help=(
                "Selected signal limit per trial for "
                "TrialRecord.metrics.selected_signal_ids. Use 0 to select all "
                "threshold-passing signals."
            ),
        ),
        split_method: Literal["single_window", "walk_forward", "purged_walk_forward"] = (
            typer.Option(
                "single_window",
                "--split-method",
                help=(
                    "Paper-only split metadata recorded in TrialRecord.metrics; "
                    "not a walk-forward PnL engine."
                ),
            )
        ),
        era_unit: Literal["session", "trading_day", "week", "month"] = typer.Option(
            "trading_day",
            "--era-unit",
            help="Era unit for signal-count metrics only.",
        ),
    ) -> None:
        """Evaluate current Strategy Lab signals into a paper-only trial ledger.

        Reads data/research/strategy_signals.parquet and writes
        data/research/trial_ledger.jsonl plus data/reports/strategy_trial_report.md.
        """
        settings = get_settings()
        signals_path = settings.data_dir / "research/strategy_signals.parquet"
        if not signals_path.exists():
            typer.echo(f"Strategy signal artifact not found: {signals_path}")
            raise typer.Exit(2)
        try:
            parsed_thresholds = _parse_rank_thresholds(rank_thresholds)
            frame, manifest, run_id = _current_signal_context(settings.data_dir)
            signal_identity = require_single_signal_identity(frame)
        except (ValueError, TypeError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        if not frame.is_empty():
            metadata = signal_identity
        elif manifest is not None:
            metadata = {
                "strategy_id": manifest.strategy_id,
                "strategy_family": manifest.strategy_family,
                "strategy_version": manifest.strategy_version,
            }
        else:
            typer.echo("Strategy signal manifest not found for empty signal artifact.")
            raise typer.Exit(2)
        records: list[TrialRecord] = []
        for trial_index, rank_threshold in enumerate(parsed_thresholds):
            candidate_frame = _thresholded_signal_frame(frame, rank_threshold)
            selected_rows = _selected_signal_rows(candidate_frame, candidate_limit=candidate_limit)
            selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
            selected = bool(selected_signal_ids)
            parameter_hash = _parameter_hash(
                run_id=run_id,
                rank_threshold=rank_threshold,
                candidate_limit=candidate_limit,
                split_method=split_method,
                era_unit=era_unit,
            )
            metrics: dict[str, Any] = {
                "signal_count": frame.height,
                "candidate_signal_count": candidate_frame.height,
                "signal_artifact_run_id": run_id,
                "candidate_selection_policy": _candidate_selection_policy(candidate_limit),
                "candidate_limit": candidate_limit,
                "rank_threshold": rank_threshold,
                "split_method": split_method,
                "era_unit": era_unit,
                "era_signal_counts": _era_signal_counts(candidate_frame, era_unit),
            }
            metrics["era_count"] = len(metrics["era_signal_counts"])
            if selected_signal_ids:
                metrics["selected_signal_id"] = selected_signal_ids[0]
                metrics["selected_signal_ids"] = selected_signal_ids
            records.append(
                TrialRecord(
                    schema_version="trial_record.v1",
                    trial_id=_trial_id_for_parameters(run_id, parameter_hash),
                    trial_group_id=f"trial-group-{run_id}",
                    trial_index=trial_index,
                    strategy_id=str(metadata.get("strategy_id")),
                    strategy_family=str(metadata.get("strategy_family")),
                    strategy_version=str(metadata.get("strategy_version")),
                    evaluation_plan_id="initial_walkforward",
                    data_snapshot_id="data-snap-current",
                    feature_snapshot_id="feature-snap-current",
                    parameter_hash=parameter_hash,
                    parameter_count=1,
                    parameter_space_hash="registered-generator-default-space",
                    random_seed=None,
                    git_sha=None,
                    signal_count=frame.height,
                    candidate_count=candidate_frame.height,
                    paper_candidate_count=len(selected_signal_ids),
                    executed_count=0,
                    blocked_count=0,
                    no_signal_count=0 if selected else 1,
                    blocked_reason_counts={},
                    metrics=metrics,
                    baseline_strategy_id=None,
                    baseline_delta_metrics={},
                    selected_for_next_stage=selected,
                    rejection_reasons=[] if selected else ["no_signals"],
                )
            )
        ledger_path = settings.data_dir / "research/trial_ledger.jsonl"
        ledger = TrialLedger(ledger_path)
        existing_trial_ids = {existing.trial_id for existing in ledger.read_all()}
        for record in records:
            if record.trial_id not in existing_trial_ids:
                ledger.append(record)
                existing_trial_ids.add(record.trial_id)
        report_path = settings.data_dir / "reports/strategy_trial_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        latest_record = records[-1]
        report_path.write_text(
            "# Strategy Trial Report\n\n"
            f"- trial_group_id: trial-group-{run_id}\n"
            f"- trial_count: {len(records)}\n"
            f"- latest_trial_id: {latest_record.trial_id}\n"
            f"- signal_count: {latest_record.signal_count}\n"
            f"- selected_for_next_stage: {latest_record.selected_for_next_stage}\n",
            encoding="utf-8",
        )
        typer.echo(f"trial_ledger={ledger_path}")
        typer.echo(f"report_path={report_path}")

    register_research_strategy_lab_candidate_pack_commands(app)
    register_research_strategy_lab_promotion_commands(app)
