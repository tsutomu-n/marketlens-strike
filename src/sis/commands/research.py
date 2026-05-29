from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Callable, Literal, cast

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
from sis.research.signal_builder import build_signals
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
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
    def build_signals_cmd() -> None:
        settings = get_settings()
        out = build_signals(settings.data_dir)
        logger.info("written: {}", out)
        for index, item in enumerate(recommended_read_order_fn(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")

    @app.command("strategy-preview")
    def strategy_preview_cmd() -> None:
        settings = get_settings()
        legacy_path = build_signals(settings.data_dir)
        report_path = settings.data_dir / "reports/strategy_signals_preview.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Strategy Signals Preview\n\n"
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
        frame = pl.read_parquet(signals_path)
        selected = frame.height > 0
        record = TrialRecord(
            schema_version="trial_record.v1",
            trial_id="trial-001",
            trial_group_id="trial-group-001",
            trial_index=0,
            strategy_id="equity_index_momentum_v0",
            strategy_family="momentum",
            strategy_version="v0",
            evaluation_plan_id="initial_walkforward",
            data_snapshot_id="data-snap-current",
            feature_snapshot_id="feature-snap-current",
            parameter_hash="default",
            parameter_count=1,
            parameter_space_hash="default-space",
            random_seed=None,
            git_sha=None,
            signal_count=frame.height,
            candidate_count=frame.height,
            paper_candidate_count=frame.height if selected else 0,
            executed_count=0,
            blocked_count=0,
            no_signal_count=0 if selected else 1,
            blocked_reason_counts={},
            metrics={"signal_count": frame.height},
            baseline_strategy_id=None,
            baseline_delta_metrics={},
            selected_for_next_stage=selected,
            rejection_reasons=[] if selected else ["no_signals"],
        )
        ledger_path = settings.data_dir / "research/trial_ledger.jsonl"
        TrialLedger(ledger_path).append(record)
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
    ) -> None:
        settings = get_settings()
        ledger_path = trial_ledger or (settings.data_dir / "research/trial_ledger.jsonl")
        records = TrialLedger(ledger_path).read_all()
        now = datetime.now(timezone.utc)
        candidates: list[TradeCandidate] = []
        selected_ids: list[str] = []
        rejected_ids: list[str] = []
        for record in records:
            candidate_id = f"candidate-{record.trial_id}"
            status = "candidate" if record.selected_for_next_stage else "blocked"
            candidates.append(
                TradeCandidate(
                    schema_version="trade_candidate.v1",
                    candidate_id=candidate_id,
                    generated_at=now,
                    signal_id=None,
                    strategy_id=record.strategy_id,
                    trial_id=record.trial_id,
                    execution_venue="trade_xyz",
                    execution_symbol="XYZ100",
                    real_market_symbol="QQQ",
                    side="long" if record.selected_for_next_stage else "none",
                    timeframe="4h",
                    status=status,
                    raw_score=None,
                    rank_score=0.9 if record.selected_for_next_stage else None,
                    percentile_rank=0.9 if record.selected_for_next_stage else None,
                    tail_bucket="top" if record.selected_for_next_stage else "none",
                    confidence=0.8,
                    entry_reason_codes=["trial_selected"] if record.selected_for_next_stage else [],
                    block_reasons=[]
                    if record.selected_for_next_stage
                    else record.rejection_reasons,
                    feature_snapshot_ref=record.feature_snapshot_id,
                    quote_ref=None,
                    tracking_ref=None,
                )
            )
            (selected_ids if record.selected_for_next_stage else rejected_ids).append(candidate_id)
        pack = PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id="paper-pack-001",
            generated_at=now,
            evaluation_plan_id=records[-1].evaluation_plan_id if records else "unknown",
            data_snapshot_id=records[-1].data_snapshot_id if records else "unknown",
            feature_snapshot_id=records[-1].feature_snapshot_id if records else None,
            trial_group_id=records[-1].trial_group_id if records else None,
            candidates=candidates,
            selected_candidate_ids=selected_ids,
            rejected_candidate_ids=rejected_ids,
            selection_policy={"selected_for_next_stage": True},
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
        promotion = PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id="promotion-001",
            generated_at=datetime.now(timezone.utc),
            source_pack_id="paper-pack-001",
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
        pack = PaperCandidatePack.model_validate(json.loads(pack_path.read_text(encoding="utf-8")))
        promotion = PromotionDecision.model_validate(
            json.loads(decision_path.read_text(encoding="utf-8"))
        )
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
