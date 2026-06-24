from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Literal, cast

import polars as pl
from pydantic import ValidationError
import typer
from loguru import logger

from sis.commands.research_strategy_lab_support import (
    _build_signals_or_exit,
    _candidate_selection_policy,
    _current_signal_context,
    _default_trial_group_id_for_current_signal,
    _era_signal_counts,
    _float_or_none,
    _latest_records_by_trial_id,
    _ndx_operator_promotion_evidence,
    _parameter_hash,
    _parse_rank_thresholds,
    _read_signal_manifest,
    _scorecard_summary_from_trial_group,
    _selected_signal_rows,
    _signal_rows_for_record,
    _tail_bucket_value,
    _thresholded_signal_frame,
    _trial_id_for_parameters,
    _record_run_id,
)
from sis.research.signal_builder import (
    DEFAULT_GENERATOR_ID,
    build_signals_from_experiment_spec,
    load_strategy_experiment_spec,
)
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import (
    require_single_signal_identity,
    run_id_from_pack_id,
    run_id_from_trial_group,
)
from sis.research.strategy_lab.signal_registry import default_signal_generator_registry
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.research.strategy_lifecycle.paper_observation_cycle import (
    build_fresh_paper_intent_preview,
)
from sis.settings import get_settings
from sis.venues.suitability import venue_suitability_block_reasons


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

    @app.command("build-paper-candidate-pack")
    def build_paper_candidate_pack_cmd(
        trial_ledger: Path | None = typer.Option(
            None,
            "--trial-ledger",
            help="Trial ledger JSONL path. Defaults to data/research/trial_ledger.jsonl.",
        ),
        trial_group_id: str | None = typer.Option(
            None,
            "--trial-group-id",
            help=(
                "Optional trial_group_id. Defaults to the latest ledger group matching "
                "the current strategy signal artifact run_id. Candidates come from "
                "TrialRecord.metrics.selected_signal_ids."
            ),
        ),
    ) -> None:
        settings = get_settings()
        ledger_path = trial_ledger or (settings.data_dir / "research/trial_ledger.jsonl")
        records = TrialLedger(ledger_path).read_all()
        if not records:
            typer.echo(f"Trial ledger has no records: {ledger_path}")
            raise typer.Exit(2)
        signal_context_error: FileNotFoundError | ValueError | None = None
        try:
            signal_frame, signal_manifest, current_run_id = _current_signal_context(
                settings.data_dir
            )
        except (FileNotFoundError, ValueError) as exc:
            signal_context_error = exc
            signal_frame = pl.DataFrame()
            signal_manifest = _read_signal_manifest(settings.data_dir)
            current_run_id = signal_manifest.signal_artifact_run_id if signal_manifest else ""
        try:
            selected_group_id = trial_group_id or _default_trial_group_id_for_current_signal(
                records,
                current_run_id=current_run_id,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        group_records = [record for record in records if record.trial_group_id == selected_group_id]
        if not group_records:
            typer.echo(f"Trial group not found in ledger: {selected_group_id}")
            raise typer.Exit(2)
        records_for_pack = _latest_records_by_trial_id(group_records)
        if signal_context_error is not None:
            if any(record.selected_for_next_stage for record in records_for_pack):
                typer.echo(str(signal_context_error))
                raise typer.Exit(2) from signal_context_error
        now = datetime.now(timezone.utc)
        operator_promotion_evidence = _ndx_operator_promotion_evidence(settings.data_dir)
        candidates: list[TradeCandidate] = []
        selected_ids: list[str] = []
        rejected_ids: list[str] = []
        for record in records_for_pack:
            if record.selected_for_next_stage:
                record_run_id = _record_run_id(record)
                if record_run_id != current_run_id:
                    typer.echo(
                        "Trial run_id does not match current strategy signal artifact: "
                        f"{record_run_id} != {current_run_id}"
                    )
                    raise typer.Exit(2)
                selected_signal_rows = _signal_rows_for_record(signal_frame, record)
                if not selected_signal_rows:
                    typer.echo(
                        f"Selected trial has no matching selected signals: {record.trial_id}"
                    )
                    raise typer.Exit(2)
            else:
                selected_signal_rows = [{}]
            for signal in selected_signal_rows:
                status = "candidate" if record.selected_for_next_stage else "blocked"
                if record.selected_for_next_stage:
                    signal_id = str(signal.get("signal_id") or "")
                    candidate_id = f"candidate-{record.trial_id}-{signal_id}"
                else:
                    signal_id = None
                    candidate_id = f"candidate-{record.trial_id}-no-signal"
                    if "no_signals" in record.rejection_reasons:
                        status = "no_signal"
                side = str(
                    signal.get("side") or ("long" if record.selected_for_next_stage else "none")
                )
                if side not in {"long", "short"}:
                    side = "none"
                candidate_side = cast(Literal["long", "short", "none"], side)
                reason_codes = list(signal.get("reason_codes") or [])
                if record.selected_for_next_stage and not reason_codes:
                    reason_codes = ["trial_selected"]
                if signal:
                    execution_symbol = str(signal.get("execution_symbol") or "XYZ100")
                    real_market_symbol = str(signal.get("real_market_symbol") or "QQQ")
                    execution_venue = signal.get("execution_venue") or "trade_xyz"
                    timeframe = str(signal.get("timeframe") or "4h")
                    feature_snapshot_ref = (
                        signal.get("feature_snapshot_ref") or record.feature_snapshot_id
                    )
                elif signal_manifest is not None:
                    binding = signal_manifest.symbol_bindings[0]
                    execution_symbol = binding.execution_symbol
                    real_market_symbol = binding.real_market_symbol
                    execution_venue = binding.execution_venue
                    timeframe = "4h"
                    feature_snapshot_ref = record.feature_snapshot_id
                else:
                    typer.echo(
                        "Strategy signal manifest not found for blocked/no-signal candidate."
                    )
                    raise typer.Exit(2)
                block_reasons = (
                    list(signal.get("block_reasons") or [])
                    if record.selected_for_next_stage
                    else list(record.rejection_reasons)
                )
                if record.selected_for_next_stage:
                    venue_reasons = venue_suitability_block_reasons(
                        venue_id=str(execution_venue),
                        execution_symbol=execution_symbol,
                        real_market_symbol=real_market_symbol,
                        stage="paper_candidate",
                        operator_promotion_evidence=operator_promotion_evidence,
                    )
                    if not venue_reasons:
                        block_reasons = [
                            reason
                            for reason in block_reasons
                            if reason != "RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED"
                        ]
                    block_reasons.extend(venue_reasons)
                    block_reasons = list(dict.fromkeys(block_reasons))
                    if block_reasons:
                        status = "blocked"
                candidate = TradeCandidate(
                    schema_version="trade_candidate.v1",
                    candidate_id=candidate_id,
                    generated_at=now,
                    signal_id=signal_id,
                    strategy_id=record.strategy_id,
                    trial_id=record.trial_id,
                    execution_venue=execution_venue,
                    execution_symbol=execution_symbol,
                    real_market_symbol=real_market_symbol,
                    side=candidate_side,
                    timeframe=timeframe,
                    status=status,
                    raw_score=_float_or_none(signal.get("raw_score")),
                    rank_score=_float_or_none(signal.get("rank_score"))
                    if record.selected_for_next_stage
                    else None,
                    percentile_rank=_float_or_none(signal.get("percentile_rank"))
                    if record.selected_for_next_stage
                    else None,
                    tail_bucket=_tail_bucket_value(
                        signal.get("tail_bucket"), selected=record.selected_for_next_stage
                    ),
                    confidence=(_float_or_none(signal.get("confidence")) or 0.8)
                    if record.selected_for_next_stage
                    else 0.0,
                    entry_reason_codes=reason_codes if record.selected_for_next_stage else [],
                    block_reasons=block_reasons,
                    feature_snapshot_ref=feature_snapshot_ref,
                    quote_ref=signal.get("quote_ref"),
                    tracking_ref=signal.get("tracking_ref"),
                )
                candidates.append(candidate)
                if record.selected_for_next_stage and not block_reasons:
                    selected_ids.append(candidate_id)
                else:
                    rejected_ids.append(candidate_id)
        pack_run_id = run_id_from_trial_group(selected_group_id)
        pack = PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id=f"paper-pack-{pack_run_id}",
            generated_at=now,
            evaluation_plan_id=records_for_pack[-1].evaluation_plan_id,
            data_snapshot_id=records_for_pack[-1].data_snapshot_id,
            feature_snapshot_id=records_for_pack[-1].feature_snapshot_id,
            trial_group_id=selected_group_id,
            candidates=candidates,
            selected_candidate_ids=selected_ids,
            rejected_candidate_ids=rejected_ids,
            selection_policy={
                "selected_for_next_stage": True,
                "trial_group_id": selected_group_id,
                "candidate_selection_policy": "selected_signal_ids",
            },
            reason_codes=["from_trial_ledger"],
            block_reasons=[],
            operator_promotion_path=operator_promotion_evidence["operator_promotion_path"],
            operator_promotion_hash=operator_promotion_evidence["operator_promotion_hash"],
        )
        out = settings.data_dir / "research/paper_candidate_pack.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
        report_path = settings.data_dir / "reports/paper_candidate_pack.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Paper Candidate Pack\n\n"
            f"- candidates: {len(candidates)}\n"
            f"- selected: {len(selected_ids)}\n"
            f"- rejected: {len(rejected_ids)}\n",
            encoding="utf-8",
        )
        typer.echo(f"paper_candidate_pack={out}")

    @app.command("promotion-decision")
    def promotion_decision_cmd(
        source_pack: Path | None = typer.Option(
            None,
            "--source-pack",
            help="PaperCandidatePack JSON path. Defaults to data/research/paper_candidate_pack.json.",
        ),
        decision: str = typer.Option(
            "hold",
            "--decision",
            help=(
                "Operator decision to record: hold, reject, or promote. "
                "Promote requires all required evidence and remains paper-only."
            ),
        ),
    ) -> None:
        settings = get_settings()
        if decision not in {"promote", "reject", "hold"}:
            typer.echo("decision must be one of: promote, reject, hold")
            raise typer.Exit(2)
        promotion_value = cast(Literal["promote", "reject", "hold"], decision)
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        required = ["trial_ledger", "paper_candidate_pack"]
        observed = ["paper_candidate_pack"] if pack_path.exists() else []
        if (settings.data_dir / "research/trial_ledger.jsonl").exists():
            observed.append("trial_ledger")
        if not pack_path.exists():
            typer.echo(f"PaperCandidatePack not found: {pack_path}")
            raise typer.Exit(2)
        pack = PaperCandidatePack.model_validate(json.loads(pack_path.read_text(encoding="utf-8")))
        source_pack_id = pack.pack_id
        promotion_run_id = run_id_from_pack_id(source_pack_id)
        scorecard_summary = (
            _scorecard_summary_from_trial_group(settings.data_dir, pack.trial_group_id)
            if pack.trial_group_id
            else {}
        )
        if scorecard_summary:
            required.append("strategy_scorecard")
            observed.append("strategy_scorecard")
        promotion = PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id=f"promotion-{promotion_run_id}",
            generated_at=datetime.now(timezone.utc),
            source_pack_id=source_pack_id,
            reviewer=None,
            from_stage="strategy_lab",
            to_stage="paper_observation",
            decision=promotion_value,
            required_evidence=required,
            observed_evidence=observed,
            approval_reasons=["operator_promoted"] if promotion_value == "promote" else [],
            rejection_reasons=[] if promotion_value == "promote" else ["not_promoted"],
            scorecard_summary=scorecard_summary,
        )
        out = settings.data_dir / "research/promotion_decision.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(promotion.model_dump_json(indent=2), encoding="utf-8")
        report_path = settings.data_dir / "reports/promotion_decision.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f"# Promotion Decision\n\n- decision: {promotion.decision}\n", encoding="utf-8"
        )
        typer.echo(f"promotion_decision={out}")

    @app.command("build-paper-intent-preview")
    def build_paper_intent_preview_cmd(
        source_pack: Path | None = typer.Option(
            None,
            "--source-pack",
            help="PaperCandidatePack JSON path. Defaults to data/research/paper_candidate_pack.json.",
        ),
        promotion_decision: Path | None = typer.Option(
            None,
            "--promotion-decision",
            help="PromotionDecision JSON path. Defaults to data/research/promotion_decision.json.",
        ),
    ) -> None:
        settings = get_settings()
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        decision_path = promotion_decision or (
            settings.data_dir / "research/promotion_decision.json"
        )
        try:
            result = build_fresh_paper_intent_preview(
                data_dir=settings.data_dir,
                source_pack_path=pack_path,
                promotion_decision_path=decision_path,
                reports_dir=settings.data_dir / "reports",
            )
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"paper_intent_preview={result.intents_path}")
