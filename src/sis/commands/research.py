from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
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


def _first_signal_row(frame: pl.DataFrame) -> dict[str, Any]:
    if frame.is_empty():
        return {}
    return frame.sort("ts_signal").to_dicts()[0]


SIGNAL_IDENTITY_COLUMNS = (
    "strategy_id",
    "strategy_family",
    "strategy_version",
    "execution_venue",
    "execution_symbol",
    "real_market_symbol",
)

SIGNAL_RUN_ID_COLUMNS = (
    "signal_id",
    "strategy_id",
    "strategy_family",
    "strategy_version",
    "execution_venue",
    "execution_symbol",
    "real_market_symbol",
    "side",
    "ts_signal",
    "timeframe",
    "raw_score",
    "rank_score",
    "tail_bucket",
    "reason_codes",
)


def _require_single_signal_identity(frame: pl.DataFrame) -> dict[str, Any]:
    if frame.is_empty():
        return {}
    missing = [column for column in SIGNAL_IDENTITY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Strategy signal artifact missing identity columns: {missing}")
    identities = frame.select(list(SIGNAL_IDENTITY_COLUMNS)).unique()
    if identities.height != 1:
        raise ValueError(
            "Strategy signal artifact contains mixed strategy/symbol identities; "
            "rebuild one generator per strategy_signals.parquet artifact."
        )
    return identities.to_dicts()[0]


def _strategy_signal_run_id(frame: pl.DataFrame) -> str:
    if frame.is_empty():
        return "no-signals"
    columns = [column for column in SIGNAL_RUN_ID_COLUMNS if column in frame.columns]
    if not columns:
        return hashlib.sha256(b"strategy-signals:missing-run-columns").hexdigest()[:12]
    sort_columns = [
        column
        for column in (
            "strategy_id",
            "strategy_version",
            "execution_symbol",
            "real_market_symbol",
            "ts_signal",
            "signal_id",
        )
        if column in columns
    ]
    stable_frame = frame.select(columns)
    if sort_columns:
        stable_frame = stable_frame.sort(sort_columns)
    payload = json.dumps(
        stable_frame.to_dicts(),
        ensure_ascii=True,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _run_id_from_trial_group(trial_group_id: str | None) -> str:
    text = str(trial_group_id or "").strip()
    if text.startswith("trial-group-"):
        return text.removeprefix("trial-group-")
    if not text:
        return "empty"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _run_id_from_pack_id(pack_id: str) -> str:
    text = str(pack_id).strip()
    if text.startswith("paper-pack-"):
        return text.removeprefix("paper-pack-")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _build_signals_or_exit(data_dir: Path, *, generator_id: str) -> Path:
    try:
        return build_signals(data_dir, generator_id=generator_id)
    except KeyError as exc:
        registered = ", ".join(default_signal_generator_registry().registered_ids())
        typer.echo(f"{exc.args[0]}; registered_generator_ids={registered}")
        raise typer.Exit(2) from exc


def _signal_rows_by_strategy(data_dir: Path) -> dict[str, dict[str, Any]]:
    signals_path = data_dir / "research/strategy_signals.parquet"
    if not signals_path.exists():
        return {}
    frame = pl.read_parquet(signals_path)
    rows: dict[str, dict[str, Any]] = {}
    for row in frame.sort("ts_signal").to_dicts():
        strategy_id = str(row.get("strategy_id") or "")
        if strategy_id and strategy_id not in rows:
            rows[strategy_id] = row
    return rows


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
        frame = pl.read_parquet(signals_path)
        try:
            signal_identity = _require_single_signal_identity(frame)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        run_id = _strategy_signal_run_id(frame)
        selected = frame.height > 0
        first_signal = signal_identity or _first_signal_row(frame)
        record = TrialRecord(
            schema_version="trial_record.v1",
            trial_id=f"trial-{run_id}",
            trial_group_id=f"trial-group-{run_id}",
            trial_index=0,
            strategy_id=str(first_signal.get("strategy_id") or "unknown_strategy"),
            strategy_family=str(first_signal.get("strategy_family") or "unknown"),
            strategy_version=str(first_signal.get("strategy_version") or "unknown"),
            evaluation_plan_id="initial_walkforward",
            data_snapshot_id="data-snap-current",
            feature_snapshot_id="feature-snap-current",
            parameter_hash=f"generator-default-{run_id}",
            parameter_count=1,
            parameter_space_hash="registered-generator-default-space",
            random_seed=None,
            git_sha=None,
            signal_count=frame.height,
            candidate_count=frame.height,
            paper_candidate_count=frame.height if selected else 0,
            executed_count=0,
            blocked_count=0,
            no_signal_count=0 if selected else 1,
            blocked_reason_counts={},
            metrics={"signal_count": frame.height, "signal_artifact_run_id": run_id},
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
        signal_by_strategy = _signal_rows_by_strategy(settings.data_dir)
        for record in records:
            candidate_id = f"candidate-{record.trial_id}"
            status = "candidate" if record.selected_for_next_stage else "blocked"
            signal = signal_by_strategy.get(record.strategy_id, {})
            side = str(signal.get("side") or ("long" if record.selected_for_next_stage else "none"))
            if side not in {"long", "short"}:
                side = "none"
            reason_codes = list(signal.get("reason_codes") or [])
            if record.selected_for_next_stage and not reason_codes:
                reason_codes = ["trial_selected"]
            candidates.append(
                TradeCandidate(
                    schema_version="trade_candidate.v1",
                    candidate_id=candidate_id,
                    generated_at=now,
                    signal_id=signal.get("signal_id"),
                    strategy_id=record.strategy_id,
                    trial_id=record.trial_id,
                    execution_venue=signal.get("execution_venue") or "trade_xyz",
                    execution_symbol=str(signal.get("execution_symbol") or "XYZ100"),
                    real_market_symbol=str(signal.get("real_market_symbol") or "QQQ"),
                    side=side,
                    timeframe=str(signal.get("timeframe") or "4h"),
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
                    confidence=_float_or_none(signal.get("confidence")) or 0.8,
                    entry_reason_codes=reason_codes if record.selected_for_next_stage else [],
                    block_reasons=[]
                    if record.selected_for_next_stage
                    else record.rejection_reasons,
                    feature_snapshot_ref=signal.get("feature_snapshot_ref")
                    or record.feature_snapshot_id,
                    quote_ref=signal.get("quote_ref"),
                    tracking_ref=signal.get("tracking_ref"),
                )
            )
            (selected_ids if record.selected_for_next_stage else rejected_ids).append(candidate_id)
        pack_run_id = _run_id_from_trial_group(records[-1].trial_group_id if records else None)
        pack = PaperCandidatePack(
            schema_version="paper_candidate_pack.v1",
            pack_id=f"paper-pack-{pack_run_id}",
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
        if pack_path.exists():
            pack = PaperCandidatePack.model_validate(
                json.loads(pack_path.read_text(encoding="utf-8"))
            )
            source_pack_id = pack.pack_id
        else:
            source_pack_id = "paper-pack-missing"
        promotion_run_id = _run_id_from_pack_id(source_pack_id)
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
