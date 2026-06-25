from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.paper_preview_selected_rows import (
    _paper_preview_selected_rows,
)
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.scorecard import _paper_preview_scorecard_summary
from sis.research.strategy_lab.signal_artifact import signal_artifact_run_id


@dataclass(frozen=True)
class _PaperPreviewRunContext:
    parameter_hash: str
    run_id: str
    trial_id: str
    trial_group_id: str
    scorecard_summary: dict[str, Any]
    selected_rows: list[dict[str, Any]]
    selected_signal_ids: list[str]
    selected: bool


def _paper_preview_run_context(
    *, spec: StrategyAuthoringSpec, frame: pl.DataFrame, summary: dict[str, Any]
) -> _PaperPreviewRunContext:
    parameter_hash = _stable_digest(spec.model_dump(mode="json"))
    run_id = signal_artifact_run_id(frame) if not frame.is_empty() else parameter_hash
    selected_rows = [] if frame.is_empty() else _paper_preview_selected_rows(frame)
    selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
    return _PaperPreviewRunContext(
        parameter_hash=parameter_hash,
        run_id=run_id,
        trial_id=f"trial-{run_id}",
        trial_group_id=f"trial-group-{run_id}",
        scorecard_summary=_paper_preview_scorecard_summary(summary),
        selected_rows=selected_rows,
        selected_signal_ids=selected_signal_ids,
        selected=bool(selected_signal_ids) and bool(summary.get("backtest_passed", False)),
    )
