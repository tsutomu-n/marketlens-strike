from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class TrialRecord(BaseModel):
    schema_version: Literal["trial_record.v1"]
    trial_id: str
    trial_group_id: str
    trial_index: int
    strategy_id: str
    strategy_family: str
    strategy_version: str
    evaluation_plan_id: str
    data_snapshot_id: str
    feature_snapshot_id: str | None
    parameter_hash: str
    parameter_count: int
    parameter_space_hash: str | None
    random_seed: int | None
    git_sha: str | None
    signal_count: int
    candidate_count: int
    paper_candidate_count: int
    executed_count: int
    blocked_count: int
    no_signal_count: int
    blocked_reason_counts: dict[str, int]
    metrics: dict[str, Any]
    baseline_strategy_id: str | None
    baseline_delta_metrics: dict[str, Any]
    selected_for_next_stage: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    profitability_claimed: bool = False
    paper_ready_claimed: bool = False
    tiny_live_ready_claimed: bool = False
    live_ready_claimed: bool = False

    @model_validator(mode="after")
    def validate_trial(self) -> TrialRecord:
        required_ids = (
            "trial_id",
            "trial_group_id",
            "strategy_id",
            "strategy_family",
            "strategy_version",
            "evaluation_plan_id",
            "data_snapshot_id",
            "parameter_hash",
        )
        for field_name in required_ids:
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.trial_index < 0:
            raise ValueError("trial_index must be >= 0")
        if self.parameter_count <= 0:
            raise ValueError("parameter_count must be positive")
        for field_name in (
            "signal_count",
            "candidate_count",
            "paper_candidate_count",
            "executed_count",
            "blocked_count",
            "no_signal_count",
        ):
            if int(getattr(self, field_name)) < 0:
                raise ValueError(f"{field_name} must be >= 0")
        if self.profitability_claimed:
            raise ValueError("profitability_claimed must remain false in TrialRecord")
        if self.paper_ready_claimed:
            raise ValueError("paper_ready_claimed must remain false in TrialRecord")
        if self.tiny_live_ready_claimed:
            raise ValueError("tiny_live_ready_claimed must remain false in TrialRecord")
        if self.live_ready_claimed:
            raise ValueError("live_ready_claimed must remain false in TrialRecord")
        return self


class TrialLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: TrialRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def read_all(self) -> list[TrialRecord]:
        if not self.path.exists():
            return []
        records: list[TrialRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                records.append(TrialRecord.model_validate(json.loads(text)))
        return records
