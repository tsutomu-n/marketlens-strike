from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.trial_ledger import TrialRecord


def _paper_preview_trial_record(
    *,
    spec: StrategyAuthoringSpec,
    summary: dict[str, Any],
    parameter_hash: str,
    trial_id: str,
    trial_group_id: str,
    signal_count: int,
    selected_signal_ids: list[str],
    selected: bool,
) -> TrialRecord:
    rejection_reasons = [] if selected else ["insufficient_trades_or_no_signal"]
    return TrialRecord(
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
        signal_count=signal_count,
        candidate_count=signal_count,
        paper_candidate_count=len(selected_signal_ids) if selected else 0,
        executed_count=0,
        blocked_count=0 if selected else 1,
        no_signal_count=0 if selected_signal_ids else 1,
        blocked_reason_counts={} if selected else {"not_selected": 1},
        metrics={**summary, "selected_signal_ids": selected_signal_ids if selected else []},
        baseline_strategy_id=None,
        baseline_delta_metrics={},
        selected_for_next_stage=selected,
        rejection_reasons=rejection_reasons,
    )
