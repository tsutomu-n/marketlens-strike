from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord
from sis.research.strategy_lab.evaluation_runner import EvaluationRunner


def _trial(trial_id: str, *, selected: bool = False) -> TrialRecord:
    return TrialRecord(
        schema_version="trial_record.v1",
        trial_id=trial_id,
        trial_group_id="group-001",
        trial_index=0 if trial_id.endswith("1") else 1,
        strategy_id="equity_index_momentum_v0",
        strategy_family="momentum",
        strategy_version="v0",
        evaluation_plan_id="initial_walkforward",
        data_snapshot_id="data-snap-001",
        feature_snapshot_id="feature-snap-001",
        parameter_hash=f"hash-{trial_id}",
        parameter_count=1,
        parameter_space_hash="space-hash",
        random_seed=42,
        git_sha=None,
        signal_count=10,
        candidate_count=8,
        paper_candidate_count=2,
        executed_count=0,
        blocked_count=6,
        no_signal_count=2,
        blocked_reason_counts={"BLOCK_LOW_SOURCE_CONFIDENCE": 6},
        metrics={"sharpe": 0.1},
        baseline_strategy_id=None,
        baseline_delta_metrics={},
        selected_for_next_stage=selected,
        rejection_reasons=[] if selected else ["below_threshold"],
    )


def test_trial_record_rejects_live_claims() -> None:
    with pytest.raises(ValidationError, match="live_ready_claimed"):
        TrialRecord(
            **{
                **_trial("trial-001").model_dump(),
                "live_ready_claimed": True,
            }
        )


def test_trial_record_requires_data_snapshot_id() -> None:
    with pytest.raises(ValidationError, match="data_snapshot_id"):
        TrialRecord(**{**_trial("trial-001").model_dump(), "data_snapshot_id": ""})


def test_trial_ledger_appends_all_trials(tmp_path: Path) -> None:
    ledger = TrialLedger(tmp_path / "trial_ledger.jsonl")

    ledger.append(_trial("trial-001", selected=False))
    ledger.append(_trial("trial-002", selected=True))

    records = ledger.read_all()
    assert [record.trial_id for record in records] == ["trial-001", "trial-002"]
    assert [record.selected_for_next_stage for record in records] == [False, True]


def test_evaluation_runner_records_selected_and_rejected_trials(tmp_path: Path) -> None:
    ledger = TrialLedger(tmp_path / "trial_ledger.jsonl")
    runner = EvaluationRunner(ledger=ledger)

    runner.record_trials([_trial("trial-001", selected=False), _trial("trial-002", selected=True)])

    records = ledger.read_all()
    assert len(records) == 2
    assert records[0].selected_for_next_stage is False
    assert records[1].selected_for_next_stage is True
