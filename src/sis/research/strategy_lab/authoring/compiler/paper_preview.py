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
from sis.research.strategy_lab.authoring.compiler.paper_preview_output_writers import (
    _write_paper_preview_json_outputs,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_outputs import (
    _paper_preview_candidate_pack,
    _paper_preview_promotion_decision,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_run_context import (
    _paper_preview_run_context,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_trial import (
    _paper_preview_trial_record,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_trial_ledger import (
    _append_paper_preview_trial_record_once,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


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
    ledger_path = _append_paper_preview_trial_record_once(
        data_dir=data_dir,
        record=record,
    )

    candidates, selected_candidate_ids, rejected_candidate_ids = _paper_preview_candidates(
        spec=spec,
        selected_rows=context.selected_rows,
        selected=context.selected,
        trial_id=context.trial_id,
        now=now,
        rejection_reasons=record.rejection_reasons,
    )

    pack = _paper_preview_candidate_pack(
        spec=spec,
        context=context,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        rejection_reasons=record.rejection_reasons,
        generated_at=now,
    )

    decision = _paper_preview_promotion_decision(
        spec=spec,
        context=context,
        pack=pack,
        generated_at=now,
    )
    json_paths = _write_paper_preview_json_outputs(data_dir=data_dir, pack=pack, decision=decision)

    intent_paths = _write_empty_paper_intent_preview_outputs(
        data_dir=data_dir,
        decision=decision.decision,
        scorecard_summary=context.scorecard_summary,
    )
    return {
        "trial_ledger": ledger_path,
        **json_paths,
        **intent_paths,
    }
