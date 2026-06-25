from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

import polars as pl
import typer

from sis.commands.research_strategy_lab_support import (
    _current_signal_context,
    _default_trial_group_id_for_current_signal,
    _float_or_none,
    _latest_records_by_trial_id,
    _ndx_operator_promotion_evidence,
    _read_signal_manifest,
    _record_run_id,
    _signal_rows_for_record,
    _tail_bucket_value,
)
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.signal_artifact import run_id_from_trial_group
from sis.research.strategy_lab.trial_ledger import TrialLedger
from sis.settings import get_settings
from sis.venues.suitability import venue_suitability_block_reasons


def register_research_strategy_lab_candidate_pack_commands(app: typer.Typer) -> None:
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
