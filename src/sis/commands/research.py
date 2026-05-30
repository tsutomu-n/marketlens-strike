from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Callable, Literal, cast

import polars as pl
import typer
from loguru import logger

from sis.reports.cost_matrix import build_cost_matrix_from_quotes, build_cost_matrix_report
from sis.research.event_calendar import build_event_calendar
from sis.research.feature_panel import build_feature_panel
from sis.research.macro_ingest import build_macro_panel
from sis.research.price_ingest import build_market_panel
from sis.research.providers import FredMacroProvider
from sis.research.research_quality import build_research_quality_report
from sis.research.signal_builder import DEFAULT_GENERATOR_ID, build_signals
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    latest_signal_row,
    read_strategy_signal_manifest,
    require_single_signal_identity,
    run_id_from_pack_id,
    run_id_from_trial_group,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
)
from sis.research.strategy_lab.signal_registry import default_signal_generator_registry
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.real_market.alpaca_smoke import run_alpaca_live_smoke
from sis.settings import get_settings


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _build_signals_or_exit(data_dir: Path, *, generator_id: str) -> Path:
    try:
        return build_signals(data_dir, generator_id=generator_id)
    except KeyError as exc:
        registered = ", ".join(default_signal_generator_registry().registered_ids())
        typer.echo(f"{exc.args[0]}; registered_generator_ids={registered}")
        raise typer.Exit(2) from exc


def _read_signal_manifest(data_dir: Path) -> StrategySignalManifest | None:
    path = strategy_signal_manifest_path(data_dir)
    return read_strategy_signal_manifest(path) if path.exists() else None


def _current_signal_context(data_dir: Path) -> tuple[pl.DataFrame, StrategySignalManifest | None, str]:
    signals_path = data_dir / "research/strategy_signals.parquet"
    if not signals_path.exists():
        raise FileNotFoundError(f"Strategy signal artifact not found: {signals_path}")
    frame = pl.read_parquet(signals_path)
    manifest = _read_signal_manifest(data_dir)
    if frame.is_empty():
        if manifest is None:
            raise ValueError(
                "Empty strategy signal artifact requires strategy_signal_manifest.json."
            )
        return frame, manifest, manifest.signal_artifact_run_id
    run_id = signal_artifact_run_id(frame)
    if manifest is not None:
        if manifest.signal_count != frame.height:
            raise ValueError(
                "Strategy signal manifest signal_count does not match artifact: "
                f"{manifest.signal_count} != {frame.height}"
            )
        if manifest.signal_artifact_run_id != run_id:
            raise ValueError(
                "Strategy signal manifest run_id does not match artifact: "
                f"{manifest.signal_artifact_run_id} != {run_id}"
            )
    return frame, manifest, run_id


def _record_run_id(record: TrialRecord) -> str:
    value = record.metrics.get("signal_artifact_run_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return run_id_from_trial_group(record.trial_group_id)


def _latest_records_by_trial_id(records: list[TrialRecord]) -> list[TrialRecord]:
    by_id: dict[str, TrialRecord] = {}
    for record in records:
        by_id[record.trial_id] = record
    return sorted(by_id.values(), key=lambda item: (item.trial_index, item.trial_id))


def _float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _tail_bucket_value(
    value: object, *, selected: bool
) -> Literal["top", "middle", "bottom", "none"]:
    fallback = "top" if selected else "none"
    text = str(value or fallback)
    if text in {"top", "middle", "bottom", "none"}:
        return cast(Literal["top", "middle", "bottom", "none"], text)
    return "none"


def register_research_commands(
    app: typer.Typer,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    @app.command("build-cost-matrix")
    def build_cost_matrix() -> None:
        settings = get_settings()
        out = settings.data_dir / "research/venue_cost_matrix.csv"
        build_cost_matrix_from_quotes(
            settings.data_dir / "normalized/quotes.parquet",
            out,
        )
        build_cost_matrix_report(
            cost_matrix_path=out,
            out_path=settings.data_dir / "reports/venue_cost_matrix.md",
            summary_path=settings.data_dir / "ops/venue_cost_matrix_summary.json",
        )
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("ingest-research-data")
    def ingest_research_data() -> None:
        settings = get_settings()
        market_panel = build_market_panel(settings.data_dir)
        macro_provider = (
            FredMacroProvider(api_key=settings.fred_api_key) if settings.fred_api_key else None
        )
        macro_panel = build_macro_panel(settings.data_dir, provider=macro_provider)
        logger.info("written: {}", market_panel)
        logger.info("written: {}", macro_panel)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-event-calendar")
    def build_event_calendar_cmd(
        csv_path: Path | None = typer.Option(
            None,
            "--csv-path",
            help="Optional event calendar CSV path. Defaults to data/research/event_calendar.csv.",
        ),
    ) -> None:
        settings = get_settings()
        out = build_event_calendar(settings.data_dir, csv_path=csv_path)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-feature-panel")
    def build_feature_panel_cmd() -> None:
        settings = get_settings()
        out = build_feature_panel(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("build-signals")
    def build_signals_cmd(
        generator_id: str = typer.Option(
            DEFAULT_GENERATOR_ID,
            "--generator-id",
            help="Registered Strategy Lab signal generator ID.",
        ),
    ) -> None:
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
            help="Registered Strategy Lab signal generator ID.",
        ),
    ) -> None:
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

    @app.command("evaluate-strategy-lab")
    def evaluate_strategy_lab_cmd() -> None:
        settings = get_settings()
        signals_path = settings.data_dir / "research/strategy_signals.parquet"
        if not signals_path.exists():
            typer.echo(f"Strategy signal artifact not found: {signals_path}")
            raise typer.Exit(2)
        try:
            frame, manifest, run_id = _current_signal_context(settings.data_dir)
            signal_identity = require_single_signal_identity(frame)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        except FileNotFoundError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        selected = frame.height > 0
        selected_signal = latest_signal_row(frame) if selected else {}
        if selected:
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
        metrics: dict[str, Any] = {
            "signal_count": frame.height,
            "signal_artifact_run_id": run_id,
            "candidate_selection_policy": "latest_signal_by_ts",
        }
        if selected:
            metrics["selected_signal_id"] = str(selected_signal.get("signal_id") or "")
        record = TrialRecord(
            schema_version="trial_record.v1",
            trial_id=f"trial-{run_id}",
            trial_group_id=f"trial-group-{run_id}",
            trial_index=0,
            strategy_id=str(metadata.get("strategy_id")),
            strategy_family=str(metadata.get("strategy_family")),
            strategy_version=str(metadata.get("strategy_version")),
            evaluation_plan_id="initial_walkforward",
            data_snapshot_id="data-snap-current",
            feature_snapshot_id="feature-snap-current",
            parameter_hash=f"generator-default-{run_id}",
            parameter_count=1,
            parameter_space_hash="registered-generator-default-space",
            random_seed=None,
            git_sha=None,
            signal_count=frame.height,
            candidate_count=1 if selected else 0,
            paper_candidate_count=1 if selected else 0,
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
        ledger_path = settings.data_dir / "research/trial_ledger.jsonl"
        ledger = TrialLedger(ledger_path)
        if record.trial_id not in {existing.trial_id for existing in ledger.read_all()}:
            ledger.append(record)
        report_path = settings.data_dir / "reports/strategy_trial_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Strategy Trial Report\n\n"
            f"- trial_id: {record.trial_id}\n"
            f"- signal_count: {record.signal_count}\n"
            f"- selected_for_next_stage: {record.selected_for_next_stage}\n",
            encoding="utf-8",
        )
        typer.echo(f"trial_ledger={ledger_path}")
        typer.echo(f"report_path={report_path}")

    @app.command("build-paper-candidate-pack")
    def build_paper_candidate_pack_cmd(
        trial_ledger: Path | None = typer.Option(None, "--trial-ledger"),
        trial_group_id: str | None = typer.Option(
            None,
            "--trial-group-id",
            help="Optional trial_group_id. Defaults to the latest group in the ledger.",
        ),
    ) -> None:
        settings = get_settings()
        ledger_path = trial_ledger or (settings.data_dir / "research/trial_ledger.jsonl")
        records = TrialLedger(ledger_path).read_all()
        if not records:
            typer.echo(f"Trial ledger has no records: {ledger_path}")
            raise typer.Exit(2)
        selected_group_id = trial_group_id or records[-1].trial_group_id
        group_records = [record for record in records if record.trial_group_id == selected_group_id]
        if not group_records:
            typer.echo(f"Trial group not found in ledger: {selected_group_id}")
            raise typer.Exit(2)
        records_for_pack = _latest_records_by_trial_id(group_records)
        try:
            signal_frame, signal_manifest, current_run_id = _current_signal_context(
                settings.data_dir
            )
            current_signal = latest_signal_row(signal_frame)
        except (FileNotFoundError, ValueError) as exc:
            signal_frame = pl.DataFrame()
            signal_manifest = _read_signal_manifest(settings.data_dir)
            current_run_id = signal_manifest.signal_artifact_run_id if signal_manifest else ""
            current_signal = {}
            if any(record.selected_for_next_stage for record in records_for_pack):
                typer.echo(str(exc))
                raise typer.Exit(2) from exc
        now = datetime.now(timezone.utc)
        candidates: list[TradeCandidate] = []
        selected_ids: list[str] = []
        rejected_ids: list[str] = []
        for record in records_for_pack:
            status = "candidate" if record.selected_for_next_stage else "blocked"
            signal = current_signal if record.selected_for_next_stage else {}
            if record.selected_for_next_stage:
                record_run_id = _record_run_id(record)
                if record_run_id != current_run_id:
                    typer.echo(
                        "Trial run_id does not match current strategy signal artifact: "
                        f"{record_run_id} != {current_run_id}"
                    )
                    raise typer.Exit(2)
                signal_id = str(signal.get("signal_id") or "")
                candidate_id = f"candidate-{record.trial_id}-{signal_id}"
            else:
                signal_id = None
                candidate_id = f"candidate-{record.trial_id}-no-signal"
                if "no_signals" in record.rejection_reasons:
                    status = "no_signal"
            side = str(signal.get("side") or ("long" if record.selected_for_next_stage else "none"))
            if side not in {"long", "short"}:
                side = "none"
            reason_codes = list(signal.get("reason_codes") or [])
            if record.selected_for_next_stage and not reason_codes:
                reason_codes = ["trial_selected"]
            if signal:
                execution_symbol = str(signal.get("execution_symbol") or "XYZ100")
                real_market_symbol = str(signal.get("real_market_symbol") or "QQQ")
                execution_venue = signal.get("execution_venue") or "trade_xyz"
                timeframe = str(signal.get("timeframe") or "4h")
                feature_snapshot_ref = signal.get("feature_snapshot_ref") or record.feature_snapshot_id
            elif signal_manifest is not None:
                binding = signal_manifest.symbol_bindings[0]
                execution_symbol = binding.execution_symbol
                real_market_symbol = binding.real_market_symbol
                execution_venue = binding.execution_venue
                timeframe = "4h"
                feature_snapshot_ref = record.feature_snapshot_id
            else:
                typer.echo("Strategy signal manifest not found for blocked/no-signal candidate.")
                raise typer.Exit(2)
            candidates.append(
                TradeCandidate(
                    schema_version="trade_candidate.v1",
                    candidate_id=candidate_id,
                    generated_at=now,
                    signal_id=signal_id,
                    strategy_id=record.strategy_id,
                    trial_id=record.trial_id,
                    execution_venue=execution_venue,
                    execution_symbol=execution_symbol,
                    real_market_symbol=real_market_symbol,
                    side=side,
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
                    block_reasons=[]
                    if record.selected_for_next_stage
                    else record.rejection_reasons,
                    feature_snapshot_ref=feature_snapshot_ref,
                    quote_ref=signal.get("quote_ref"),
                    tracking_ref=signal.get("tracking_ref"),
                )
            )
            (selected_ids if record.selected_for_next_stage else rejected_ids).append(candidate_id)
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
                "candidate_selection_policy": "latest_signal_by_ts",
            },
            reason_codes=["from_trial_ledger"],
            block_reasons=[],
        )
        out = settings.data_dir / "research/paper_candidate_pack.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
        report_path = settings.data_dir / "reports/paper_candidate_pack.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Paper Candidate Pack\n\n"
            f"- candidates: {len(candidates)}\n"
            f"- selected: {len(selected_ids)}\n",
            encoding="utf-8",
        )
        typer.echo(f"paper_candidate_pack={out}")

    @app.command("promotion-decision")
    def promotion_decision_cmd(
        source_pack: Path | None = typer.Option(None, "--source-pack"),
        decision: str = typer.Option("hold", "--decision"),
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
        source_pack: Path | None = typer.Option(None, "--source-pack"),
        promotion_decision: Path | None = typer.Option(None, "--promotion-decision"),
    ) -> None:
        settings = get_settings()
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        decision_path = promotion_decision or (
            settings.data_dir / "research/promotion_decision.json"
        )
        if not decision_path.exists():
            typer.echo(f"PromotionDecision not found: {decision_path}")
            raise typer.Exit(2)
        if not pack_path.exists():
            typer.echo(f"PaperCandidatePack not found: {pack_path}")
            raise typer.Exit(2)
        pack = PaperCandidatePack.model_validate(json.loads(pack_path.read_text(encoding="utf-8")))
        promotion = PromotionDecision.model_validate(
            json.loads(decision_path.read_text(encoding="utf-8"))
        )
        if promotion.source_pack_id != pack.pack_id:
            typer.echo(
                "PromotionDecision source_pack_id does not match PaperCandidatePack pack_id: "
                f"{promotion.source_pack_id} != {pack.pack_id}"
            )
            raise typer.Exit(2)
        intents: list[PaperIntentPreview] = []
        if promotion.decision == "promote":
            selected = {
                candidate.candidate_id: candidate
                for candidate in pack.candidates
                if candidate.candidate_id in pack.selected_candidate_ids
            }
            for candidate_id, candidate in selected.items():
                intents.append(
                    PaperIntentPreview(
                        schema_version="paper_intent_preview.v1",
                        intent_id=f"intent-{candidate_id}",
                        generated_at=datetime.now(timezone.utc),
                        valid_until=datetime.now(timezone.utc) + timedelta(minutes=15),
                        source_pack_id=pack.pack_id,
                        candidate_id=candidate_id,
                        strategy_id=candidate.strategy_id,
                        execution_venue=candidate.execution_venue,
                        execution_symbol=candidate.execution_symbol,
                        real_market_symbol=candidate.real_market_symbol,
                        action="enter" if candidate.side in {"long", "short"} else "skip",
                        side=candidate.side,
                        order_style="paper_taker" if candidate.side != "none" else "skip",
                        price_reference="mark",
                        notional_usd=1000.0 if candidate.side != "none" else None,
                        quantity=None,
                        source_quote_ts=None,
                        source_tracking_ts=None,
                        source_feature_ts=None,
                        source_phase_gate_run_id=None,
                    )
                )
        out = settings.data_dir / "bot/paper_intent_preview.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
            encoding="utf-8",
        )
        report_path = settings.data_dir / "reports/paper_intent_preview.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f"# Paper Intent Preview\n\n- intents: {len(intents)}\n", encoding="utf-8"
        )
        typer.echo(f"paper_intent_preview={out}")

    @app.command("check-research-quality")
    def check_research_quality_cmd() -> None:
        settings = get_settings()
        out = build_research_quality_report(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("alpaca-smoke")
    def alpaca_smoke_cmd(
        symbol: str = typer.Option("NVDA", "--symbol", help="Alpaca stock symbol."),
        timeframe: str = typer.Option("15m", "--timeframe", help="Alpaca bars timeframe."),
        start: str | None = typer.Option(
            None,
            "--start",
            help="Optional ISO start time for historical connectivity smoke.",
        ),
        end: str | None = typer.Option(
            None,
            "--end",
            help="Optional ISO end time for historical connectivity smoke.",
        ),
        limit: int = typer.Option(1, "--limit", min=1, help="Number of bars to request."),
        feed: str = typer.Option("iex", "--feed", help="Alpaca data feed."),
        timeout: float = typer.Option(10.0, "--timeout", min=0.1, help="Request timeout seconds."),
        raw_payload_path: Path | None = typer.Option(
            None,
            "--raw-payload-path",
            help="Optional raw payload output path. Defaults under data/raw/real_market/alpaca.",
        ),
    ) -> None:
        settings = get_settings()
        summary = run_alpaca_live_smoke(
            data_dir=settings.data_dir,
            symbol=symbol,
            timeframe=timeframe,
            start=_parse_optional_datetime(start),
            end=_parse_optional_datetime(end),
            limit=limit,
            feed=feed,
            timeout=timeout,
            raw_payload_path=raw_payload_path,
        )
        typer.echo(f"status={summary['status']}")
        typer.echo(f"provider_connectivity_status={summary['provider_connectivity_status']}")
        typer.echo(f"data_availability_status={summary['data_availability_status']}")
        typer.echo(f"symbol={summary['symbol']}")
        typer.echo(f"timeframe={summary['timeframe']}")
        typer.echo(f"effective_timeframe={summary['effective_timeframe']}")
        typer.echo(f"feed={summary['feed']}")
        typer.echo(f"requested_window={summary['requested_window']}")
        typer.echo(f"request_endpoint={summary['request_endpoint']}")
        typer.echo(f"start={summary['start']}")
        typer.echo(f"end={summary['end']}")
        typer.echo(f"bar_count={summary['bar_count']}")
        typer.echo(f"latest_bar_ts={summary.get('latest_bar_ts')}")
        typer.echo(f"market_session={summary.get('market_session')}")
        typer.echo(f"source_confidence={summary['source_confidence']}")
        typer.echo(f"source_confidence_reason={summary.get('source_confidence_reason')}")
        live_suitability_reasons = summary.get("live_suitability_reasons")
        formatted_reasons = (
            ",".join(str(reason) for reason in live_suitability_reasons)
            if isinstance(live_suitability_reasons, list)
            else ""
        )
        typer.echo(f"live_suitability_reasons={formatted_reasons}")
        typer.echo(f"summary_path={summary['summary_path']}")
        typer.echo(f"report_path={summary['report_path']}")
        typer.echo(f"raw_payload_path={summary['raw_payload_path']}")
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        if summary.get("status") != "pass":
            typer.echo(f"error_class={summary.get('error_class')}")
            typer.echo(f"error_message={summary.get('error_message')}")
            raise typer.Exit(2)
