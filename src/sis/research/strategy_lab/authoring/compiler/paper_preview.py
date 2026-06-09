from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal, cast

import polars as pl

from sis.research.strategy_lab.authoring.compiler.common import _float_or_default, _stable_digest
from sis.research.strategy_lab.authoring.contracts.base import DEFAULT_EXIT_PRIORITY
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.scorecard import _paper_preview_scorecard_summary
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import signal_artifact_run_id
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.venues.ids import VenueId
from sis.venues.suitability import venue_suitability_block_reasons


def write_authoring_paper_preview_outputs(
    spec: StrategyAuthoringSpec,
    frame: pl.DataFrame,
    summary: dict[str, Any],
    *,
    data_dir: Path,
) -> dict[str, Path]:
    now = datetime.now(timezone.utc)
    parameter_hash = _stable_digest(spec.model_dump(mode="json"))
    run_id = signal_artifact_run_id(frame) if not frame.is_empty() else parameter_hash
    trial_id = f"trial-{run_id}"
    trial_group_id = f"trial-group-{run_id}"
    scorecard_summary = _paper_preview_scorecard_summary(summary)
    selected_rows = [
        row
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower() in {"long", "short"}
        and not list(row.get("block_reasons") or [])
    ][:1]
    selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
    selected = bool(selected_signal_ids) and bool(summary.get("backtest_passed", False))
    record = TrialRecord(
        schema_version="trial_record.v1",
        trial_id=trial_id,
        trial_group_id=trial_group_id,
        trial_index=0,
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        parameter_hash=parameter_hash,
        parameter_count=1,
        parameter_space_hash="strategy-authoring-yaml-v1",
        random_seed=None,
        git_sha=None,
        signal_count=frame.height,
        candidate_count=frame.height,
        paper_candidate_count=len(selected_signal_ids) if selected else 0,
        executed_count=0,
        blocked_count=0 if selected else 1,
        no_signal_count=0 if selected_signal_ids else 1,
        blocked_reason_counts={} if selected else {"not_selected": 1},
        metrics={**summary, "selected_signal_ids": selected_signal_ids if selected else []},
        baseline_strategy_id=None,
        baseline_delta_metrics={},
        selected_for_next_stage=selected,
        rejection_reasons=[] if selected else ["insufficient_trades_or_no_signal"],
    )
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)

    candidates: list[TradeCandidate] = []
    selected_candidate_ids: list[str] = []
    rejected_candidate_ids: list[str] = []
    rows_for_candidates = selected_rows if selected_rows else [{}]
    for row in rows_for_candidates:
        candidate_id = (
            f"candidate-{trial_id}-{row['signal_id']}" if row else f"candidate-{trial_id}-no-signal"
        )
        status = "candidate" if selected else ("no_signal" if not row else "hold")
        binding = spec.experiment.symbol_bindings[0]
        execution_venue = cast(
            VenueId, row.get("execution_venue") if row else binding.execution_venue
        )
        side = cast(
            Literal["long", "short", "none"], row.get("side") if selected and row else "none"
        )
        entry_order_type = cast(
            Literal["market", "limit", "stop_market"],
            row.get("entry_order_type") if selected and row else "market",
        )
        tail_bucket = cast(
            Literal["top", "middle", "bottom", "none"],
            row.get("tail_bucket") if selected and row else "none",
        )
        confidence = _float_or_default(row.get("confidence") if selected and row else None, 0.0)
        candidate_block_reasons = [] if selected else list(record.rejection_reasons)
        if selected:
            candidate_block_reasons.extend(
                venue_suitability_block_reasons(
                    venue_id=str(execution_venue),
                    execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
                    real_market_symbol=str(
                        row.get("real_market_symbol") or binding.real_market_symbol
                    ),
                    stage="paper_candidate",
                )
            )
            candidate_block_reasons = list(dict.fromkeys(candidate_block_reasons))
        candidate_selected = selected and not candidate_block_reasons
        if selected and candidate_block_reasons:
            status = "blocked"
        candidate = TradeCandidate(
            schema_version="trade_candidate.v1",
            candidate_id=candidate_id,
            generated_at=now,
            signal_id=str(row.get("signal_id")) if row else None,
            strategy_id=spec.experiment.strategy_id,
            trial_id=trial_id,
            execution_venue=execution_venue,
            execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
            real_market_symbol=str(row.get("real_market_symbol") or binding.real_market_symbol),
            side=side,
            timeframe=str(row.get("timeframe") or spec.rules.timeframe),
            status=status,
            raw_score=row.get("raw_score") if row else None,
            rank_score=row.get("rank_score") if selected and row else None,
            percentile_rank=row.get("percentile_rank") if selected and row else None,
            tail_bucket=tail_bucket,
            confidence=confidence,
            entry_reason_codes=list(row.get("reason_codes") or []) if selected and row else [],
            block_reasons=candidate_block_reasons,
            stop_loss_bps=row.get("stop_loss_bps") if selected and row else None,
            min_stop_loss_bps=row.get("min_stop_loss_bps") if selected and row else None,
            max_stop_loss_bps=row.get("max_stop_loss_bps") if selected and row else None,
            take_profit_bps=row.get("take_profit_bps") if selected and row else None,
            min_take_profit_bps=row.get("min_take_profit_bps") if selected and row else None,
            max_take_profit_bps=row.get("max_take_profit_bps") if selected and row else None,
            min_reward_risk_ratio=(row.get("min_reward_risk_ratio") if selected and row else None),
            reward_risk_ratio=row.get("reward_risk_ratio") if selected and row else None,
            trailing_stop_bps=row.get("trailing_stop_bps") if selected and row else None,
            trailing_stop_activation_bps=(
                row.get("trailing_stop_activation_bps") if selected and row else None
            ),
            partial_take_profit_bps=(
                row.get("partial_take_profit_bps") if selected and row else None
            ),
            partial_exit_fraction=row.get("partial_exit_fraction") if selected and row else None,
            min_holding_minutes=row.get("min_holding_minutes") if selected and row else None,
            max_holding_minutes=row.get("max_holding_minutes") if selected and row else None,
            exit_priority=str(row.get("exit_priority") or DEFAULT_EXIT_PRIORITY)
            if selected and row
            else DEFAULT_EXIT_PRIORITY,
            exit_on_opposite_signal=(
                bool(row.get("exit_on_opposite_signal")) if selected and row else False
            ),
            bracket_type=cast(
                Literal["none", "oco"], row.get("bracket_type") if selected and row else "none"
            ),
            bracket_time_stop_minutes=(
                row.get("bracket_time_stop_minutes") if selected and row else None
            ),
            bracket_break_even_after_bps=(
                row.get("bracket_break_even_after_bps") if selected and row else None
            ),
            bracket_break_even_after_partial_take_profit=(
                bool(row.get("bracket_break_even_after_partial_take_profit"))
                if selected and row
                else False
            ),
            entry_order_type=entry_order_type,
            entry_limit_offset_bps=row.get("entry_limit_offset_bps") if selected and row else None,
            entry_stop_offset_bps=row.get("entry_stop_offset_bps") if selected and row else None,
            entry_timeout_minutes=row.get("entry_timeout_minutes") if selected and row else None,
            entry_time_in_force=(
                cast(
                    Literal["gtc", "gtd", "ioc", "fok"],
                    row.get("entry_time_in_force") if selected and row else "gtc",
                )
            ),
            entry_post_only=bool(row.get("entry_post_only")) if selected and row else False,
            entry_reduce_only=bool(row.get("entry_reduce_only")) if selected and row else False,
            slippage_bps=_float_or_default(
                row.get("slippage_bps") if selected and row else None,
                0.0,
            ),
            max_fill_fraction=_float_or_default(
                row.get("max_fill_fraction") if selected and row else None,
                0.0,
            ),
            min_fill_fraction=row.get("min_fill_fraction") if selected and row else None,
            max_spread_bps=row.get("max_spread_bps") if selected and row else None,
            min_depth_usd=row.get("min_depth_usd") if selected and row else None,
            depth_column=row.get("depth_column") if selected and row else None,
            depth_participation_rate=_float_or_default(
                row.get("depth_participation_rate") if selected and row else None,
                0.0,
            ),
            max_latency_ms=row.get("max_latency_ms") if selected and row else None,
            latency_ms=row.get("latency_ms") if selected and row else None,
            min_queue_position_score=(
                row.get("min_queue_position_score") if selected and row else None
            ),
            queue_position_score=row.get("queue_position_score") if selected and row else None,
            min_borrow_availability_ratio=(
                row.get("min_borrow_availability_ratio") if selected and row else None
            ),
            borrow_availability_ratio=(
                row.get("borrow_availability_ratio") if selected and row else None
            ),
            max_borrow_cost_bps=row.get("max_borrow_cost_bps") if selected and row else None,
            borrow_cost_bps=row.get("borrow_cost_bps") if selected and row else None,
            max_tax_drag_bps=row.get("max_tax_drag_bps") if selected and row else None,
            tax_drag_bps=row.get("tax_drag_bps") if selected and row else None,
            max_turnover_pressure=(row.get("max_turnover_pressure") if selected and row else None),
            turnover_pressure=row.get("turnover_pressure") if selected and row else None,
            max_capacity_usage_ratio=(
                row.get("max_capacity_usage_ratio") if selected and row else None
            ),
            capacity_usage_ratio=row.get("capacity_usage_ratio") if selected and row else None,
            max_correlation_crowding_score=(
                row.get("max_correlation_crowding_score") if selected and row else None
            ),
            correlation_crowding_score=(
                row.get("correlation_crowding_score") if selected and row else None
            ),
            min_fee_edge_bps=row.get("min_fee_edge_bps") if selected and row else None,
            fee_edge_bps=row.get("fee_edge_bps") if selected and row else None,
            position_weight=row.get("position_weight") if selected and row else None,
            notional_usd=row.get("notional_usd") if selected and row else None,
            feature_snapshot_ref=row.get("feature_snapshot_ref") if row else None,
            quote_ref=row.get("quote_ref") if row else None,
            tracking_ref=row.get("tracking_ref") if row else None,
        )
        candidates.append(candidate)
        (selected_candidate_ids if candidate_selected else rejected_candidate_ids).append(
            candidate_id
        )

    pack = PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id=f"paper-pack-{run_id}",
        generated_at=now,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        trial_group_id=trial_group_id,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        selection_policy={
            "source": "strategy_authoring",
            "default_decision": spec.promotion.default_decision,
        },
        reason_codes=["strategy_authoring_v1"],
        block_reasons=[] if selected else record.rejection_reasons,
    )
    pack_path = data_dir / "research/paper_candidate_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")

    decision = PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id=f"promotion-{run_id}",
        generated_at=now,
        source_pack_id=pack.pack_id,
        reviewer=None,
        from_stage="strategy_lab",
        to_stage="paper_observation",
        decision=spec.promotion.default_decision,
        required_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        observed_evidence=["trial_ledger", "paper_candidate_pack", "strategy_scorecard"],
        approval_reasons=[],
        rejection_reasons=["operator_review_required"],
        scorecard_summary=scorecard_summary,
    )
    decision_path = data_dir / "research/promotion_decision.json"
    decision_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    intents: list[PaperIntentPreview] = []
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
        encoding="utf-8",
    )
    report_path = data_dir / "reports/paper_intent_preview.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Paper Intent Preview\n\n"
        "- source: strategy_authoring\n"
        f"- decision: {decision.decision}\n"
        f"- intents: {len(intents)}\n"
        f"- scorecard_schema_version: {scorecard_summary.get('schema_version')}\n"
        f"- scorecard_failed_thresholds: {scorecard_summary.get('failed_thresholds', [])}\n"
        "- paper_only: true\n",
        encoding="utf-8",
    )
    return {
        "trial_ledger": ledger_path,
        "paper_candidate_pack": pack_path,
        "promotion_decision": decision_path,
        "paper_intent_preview": preview_path,
        "paper_intent_preview_report": report_path,
    }


def write_authoring_run_summary(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    through: str,
    artifacts: dict[str, Path],
    signal_count: int,
) -> Path:
    out = data_dir / "research/strategy_authoring_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_run.v1",
                "strategy_id": spec.experiment.strategy_id,
                "through": through,
                "signal_count": signal_count,
                "paper_only": True,
                "live_order_submitted": False,
                "artifacts": {key: str(value) for key, value in artifacts.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
