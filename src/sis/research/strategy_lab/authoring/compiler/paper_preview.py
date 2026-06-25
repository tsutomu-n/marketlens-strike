from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidates import (
    _paper_preview_candidates,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_intent_outputs import (
    _write_empty_paper_intent_preview_outputs,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_run_context import (
    _paper_preview_run_context,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_trial import (
    _paper_preview_trial_record,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.trial_ledger import TrialLedger


def write_authoring_paper_preview_outputs(
    spec: StrategyAuthoringSpec,
    frame: pl.DataFrame,
    summary: dict[str, Any],
    *,
    data_dir: Path,
) -> dict[str, Path]:
    now = datetime.now(timezone.utc)
    context = _paper_preview_run_context(spec=spec, frame=frame, summary=summary)
    record = _paper_preview_trial_record(
        spec=spec,
        summary=summary,
        parameter_hash=context.parameter_hash,
        trial_id=context.trial_id,
        trial_group_id=context.trial_group_id,
        signal_count=frame.height,
        selected_signal_ids=context.selected_signal_ids,
        selected=context.selected,
    )
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)

    candidates, selected_candidate_ids, rejected_candidate_ids = _paper_preview_candidates(
        spec=spec,
        selected_rows=context.selected_rows,
        selected=context.selected,
        trial_id=context.trial_id,
        now=now,
        rejection_reasons=record.rejection_reasons,
    )

    pack = PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id=f"paper-pack-{context.run_id}",
        generated_at=now,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        trial_group_id=context.trial_group_id,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        selection_policy={
            "source": "strategy_authoring",
            "default_decision": spec.promotion.default_decision,
        },
        reason_codes=["strategy_authoring_v1"],
        block_reasons=[] if context.selected else record.rejection_reasons,
    )
    pack_path = data_dir / "research/paper_candidate_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")

    decision = PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id=f"promotion-{context.run_id}",
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
        scorecard_summary=context.scorecard_summary,
    )
    decision_path = data_dir / "research/promotion_decision.json"
    decision_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    intent_paths = _write_empty_paper_intent_preview_outputs(
        data_dir=data_dir,
        decision=decision.decision,
        scorecard_summary=context.scorecard_summary,
    )
    return {
        "trial_ledger": ledger_path,
        "paper_candidate_pack": pack_path,
        "promotion_decision": decision_path,
        **intent_paths,
    }
