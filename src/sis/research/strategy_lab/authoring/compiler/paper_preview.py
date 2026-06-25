from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidates import (
    _paper_preview_candidates,
    _paper_preview_selected_rows,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_trial import (
    _paper_preview_trial_record,
)
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.scorecard import _paper_preview_scorecard_summary
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import signal_artifact_run_id
from sis.research.strategy_lab.trial_ledger import TrialLedger


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
    selected_rows = _paper_preview_selected_rows(frame)
    selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
    selected = bool(selected_signal_ids) and bool(summary.get("backtest_passed", False))
    record = _paper_preview_trial_record(
        spec=spec,
        summary=summary,
        parameter_hash=parameter_hash,
        trial_id=trial_id,
        trial_group_id=trial_group_id,
        signal_count=frame.height,
        selected_signal_ids=selected_signal_ids,
        selected=selected,
    )
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)

    candidates, selected_candidate_ids, rejected_candidate_ids = _paper_preview_candidates(
        spec=spec,
        selected_rows=selected_rows,
        selected=selected,
        trial_id=trial_id,
        now=now,
        rejection_reasons=record.rejection_reasons,
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
    source_signal_count: int | None = None,
    evaluation_signal_count: int | None = None,
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
                "source_signal_count": (
                    source_signal_count if source_signal_count is not None else signal_count
                ),
                "evaluation_signal_count": (
                    evaluation_signal_count if evaluation_signal_count is not None else signal_count
                ),
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
