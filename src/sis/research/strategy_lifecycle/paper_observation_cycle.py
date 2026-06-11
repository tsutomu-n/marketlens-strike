from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from sis.paper.observation_session import (
    PaperObservationSession,
    PaperObservationThresholds,
    create_paper_observation_session,
)
from sis.paper.runner import PaperFromIntentsSummary, run_paper_from_intents
from sis.research.ndx.artifacts import read_json, write_json
from sis.research.ndx.paper_observation_review import (
    PaperObservationReviewResult,
    run_paper_observation_review,
)
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lifecycle.review import (
    StrategyLifecycleReviewResult,
    run_strategy_lifecycle_review,
)


@dataclass(frozen=True)
class PaperIntentPreviewBuildResult:
    intents_path: Path
    report_path: Path
    intent_count: int


@dataclass(frozen=True)
class StrategyPaperObservationCycleResult:
    session: PaperObservationSession
    intents: PaperIntentPreviewBuildResult
    paper_run: PaperFromIntentsSummary
    paper_review: PaperObservationReviewResult
    lifecycle_review: StrategyLifecycleReviewResult
    report_path: Path


def build_fresh_paper_intent_preview(
    *,
    data_dir: Path,
    source_pack_path: Path,
    promotion_decision_path: Path,
    reports_dir: Path,
) -> PaperIntentPreviewBuildResult:
    if not source_pack_path.exists():
        raise FileNotFoundError(f"PaperCandidatePack not found: {source_pack_path}")
    if not promotion_decision_path.exists():
        raise FileNotFoundError(f"PromotionDecision not found: {promotion_decision_path}")
    pack = PaperCandidatePack.model_validate(
        json.loads(source_pack_path.read_text(encoding="utf-8"))
    )
    promotion = PromotionDecision.model_validate(
        json.loads(promotion_decision_path.read_text(encoding="utf-8"))
    )
    if promotion.source_pack_id != pack.pack_id:
        raise ValueError(
            "PromotionDecision source_pack_id does not match PaperCandidatePack pack_id: "
            f"{promotion.source_pack_id} != {pack.pack_id}"
        )
    intents = _paper_intents_from_pack(pack=pack, promotion=promotion)
    out = data_dir / "bot/paper_intent_preview.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
        encoding="utf-8",
    )
    report_path = reports_dir / "paper_intent_preview.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Paper Intent Preview\n\n"
        f"- intents: {len(intents)}\n"
        f"- source_pack_path: {source_pack_path.as_posix()}\n"
        f"- promotion_decision_path: {promotion_decision_path.as_posix()}\n"
        f"- scorecard_schema_version: {promotion.scorecard_summary.get('schema_version')}\n",
        encoding="utf-8",
    )
    return PaperIntentPreviewBuildResult(
        intents_path=out,
        report_path=report_path,
        intent_count=len(intents),
    )


def run_strategy_paper_observation_cycle(
    *,
    data_dir: Path,
    artifact_dir: Path,
    reports_dir: Path,
    session_id: str | None = None,
    backtest_acceptance_path: Path | None = None,
    source_pack_path: Path | None = None,
    promotion_decision_path: Path | None = None,
    operator_promotion_path: Path | None = None,
    min_fills_for_pass: int = 20,
    min_trading_days_for_pass: int = 10,
    max_blocked_rate: float = 0.5,
    max_consecutive_blocked: int = 3,
    max_open_position_age_hours: float = 0.0,
    paper_notional_usd: float = 1000.0,
    smoke: bool = False,
) -> StrategyPaperObservationCycleResult:
    selected_backtest_path = backtest_acceptance_path or (
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    )
    selected_source_pack_path = source_pack_path or (
        data_dir / "research/paper_candidate_pack.json"
    )
    selected_promotion_path = promotion_decision_path or (
        data_dir / "research/promotion_decision.json"
    )
    selected_operator_promotion_path = operator_promotion_path or (
        artifact_dir / "operator_promotion_decision.json"
    )
    _require_passed_backtest(selected_backtest_path)
    effective_min_fills = 1 if smoke else min_fills_for_pass
    effective_min_days = 1 if smoke else min_trading_days_for_pass

    intents = build_fresh_paper_intent_preview(
        data_dir=data_dir,
        source_pack_path=selected_source_pack_path,
        promotion_decision_path=selected_promotion_path,
        reports_dir=reports_dir,
    )
    if intents.intent_count < 1:
        raise ValueError("fresh paper intent preview has no intents.")

    session = create_paper_observation_session(
        data_dir=data_dir,
        source_backtest_acceptance_path=selected_backtest_path,
        source_operator_promotion_path=selected_operator_promotion_path,
        source_intent_preview_path=intents.intents_path,
        session_id=session_id,
        thresholds=PaperObservationThresholds(
            min_fills_for_pass=effective_min_fills,
            min_trading_days_for_pass=effective_min_days,
            max_blocked_rate=max_blocked_rate,
            max_consecutive_blocked=max_consecutive_blocked,
            max_open_position_age_hours=max_open_position_age_hours,
        ),
        smoke=smoke,
    )
    paper_run = run_paper_from_intents(
        data_dir,
        intents_path=intents.intents_path,
        observation_ledger_path=session.observation_ledger_path,
    )
    paper_review = run_paper_observation_review(
        data_dir=data_dir,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        session_manifest_path=session.manifest_path,
        min_fills_for_pass=effective_min_fills,
        min_trading_days_for_pass=effective_min_days,
        max_blocked_rate=max_blocked_rate,
        max_consecutive_blocked=max_consecutive_blocked,
        max_open_position_age_hours=max_open_position_age_hours,
        paper_notional_usd=paper_notional_usd,
    )
    session_review_path = session.session_dir / "paper_observation_review_decision.json"
    session_review_path.write_text(
        paper_review.decision_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    lifecycle_review = run_strategy_lifecycle_review(
        data_dir=data_dir,
        out_dir=data_dir / "research/strategy_lifecycle",
        reports_dir=reports_dir,
        backtest_decision_path=selected_backtest_path,
        paper_review_path=paper_review.decision_path,
    )
    report_path = _write_cycle_report(
        reports_dir / "paper_observation_session_report.md",
        session=session,
        intents=intents,
        paper_run=paper_run,
        paper_review=paper_review,
        lifecycle_review=lifecycle_review,
        smoke=smoke,
    )
    return StrategyPaperObservationCycleResult(
        session=session,
        intents=intents,
        paper_run=paper_run,
        paper_review=paper_review,
        lifecycle_review=lifecycle_review,
        report_path=report_path,
    )


def _paper_intents_from_pack(
    *,
    pack: PaperCandidatePack,
    promotion: PromotionDecision,
) -> list[PaperIntentPreview]:
    if promotion.decision != "promote":
        return []
    selected = {
        candidate.candidate_id: candidate
        for candidate in pack.candidates
        if candidate.candidate_id in pack.selected_candidate_ids
    }
    now = datetime.now(timezone.utc)
    intents: list[PaperIntentPreview] = []
    for candidate_id, candidate in selected.items():
        intents.append(
            PaperIntentPreview(
                schema_version="paper_intent_preview.v1",
                intent_id=f"intent-{candidate_id}",
                generated_at=now,
                valid_until=now + timedelta(minutes=15),
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
                scorecard_summary=promotion.scorecard_summary,
                operator_promotion_path=pack.operator_promotion_path,
                operator_promotion_hash=pack.operator_promotion_hash,
            )
        )
    return intents


def _require_passed_backtest(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"strategy backtest acceptance decision missing: {path}")
    payload = read_json(path)
    if payload.get("decision") != "PASS_BACKTEST_ACCEPTANCE":
        raise ValueError(f"strategy backtest acceptance is not passed: {payload.get('decision')}")
    for key in ("permits_live_order", "wallet_used", "venue_write_used", "exchange_write_used"):
        if payload.get(key) is not False:
            raise ValueError(f"strategy backtest acceptance must keep {key}=false.")


def _write_cycle_report(
    path: Path,
    *,
    session: PaperObservationSession,
    intents: PaperIntentPreviewBuildResult,
    paper_run: PaperFromIntentsSummary,
    paper_review: PaperObservationReviewResult,
    lifecycle_review: StrategyLifecycleReviewResult,
    smoke: bool,
) -> Path:
    write_json(
        session.session_dir / "paper_observation_cycle_summary.json",
        {
            "schema_version": "paper_observation_cycle_summary.v1",
            "session_id": session.session_id,
            "smoke": smoke,
            "paper_intent_preview_path": intents.intents_path.as_posix(),
            "paper_intent_count": intents.intent_count,
            "paper_orders_count": paper_run.orders_count,
            "paper_fills_count": paper_run.fills_count,
            "paper_blocked_count": paper_run.blocked_count,
            "paper_review_decision": paper_review.decision,
            "lifecycle_decision": lifecycle_review.decision,
            "permits_live_order": False,
            "wallet_used": False,
            "venue_write_used": False,
            "exchange_write_used": False,
        },
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Paper Observation Session Report\n\n"
        f"- session_id: {session.session_id}\n"
        f"- smoke: {str(smoke).lower()}\n"
        f"- paper_intents: {intents.intent_count}\n"
        f"- paper_fills: {paper_run.fills_count}\n"
        f"- paper_review_decision: {paper_review.decision}\n"
        f"- lifecycle_decision: {lifecycle_review.decision}\n"
        "- permits_live_order: false\n"
        "- wallet_used: false\n"
        "- venue_write_used: false\n"
        "- exchange_write_used: false\n",
        encoding="utf-8",
    )
    return path
