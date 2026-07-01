from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import BACKTEST_KILL_GATE_SCHEMA_VERSION
from sis.edge_candidates.multiplicity import SelectionAdjustmentStatus
from sis.edge_candidates.protocol import CandidateProtocolMode, FamilyEventCountPolicy


class BacktestKillGateState(StrEnum):
    KILL = "KILL"
    INCONCLUSIVE_DATA = "INCONCLUSIVE_DATA"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    SHORTLIST_FOR_VIRTUAL = "SHORTLIST_FOR_VIRTUAL"


class BacktestKillGateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    mode: CandidateProtocolMode
    family_id: str
    event_count: int = Field(ge=0)
    closed_trade_count: int = Field(ge=0)
    no_trade_comparison_present: bool
    after_cost_edge_over_no_trade: float
    stress_edge_over_no_trade: float
    largest_loss_usd: float
    profit_concentration: float = Field(ge=0)
    regime_stability: str
    source_gap_count: int = Field(ge=0)
    unexecutable_reason_count: int = Field(ge=0)
    selection_adjustment_status: SelectionAdjustmentStatus
    family_event_count_policy: FamilyEventCountPolicy
    execution_candidate: bool = True

    @field_validator("candidate_id", "family_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("regime_stability")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("regime_stability must not be empty")
        return stripped


class BacktestKillGateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["backtest_kill_gate.v1"] = BACKTEST_KILL_GATE_SCHEMA_VERSION
    gate_id: str
    evaluated_at: datetime
    candidate_id: str
    mode: CandidateProtocolMode
    family_id: str
    gate_state: BacktestKillGateState
    blocker_codes: list[str] = Field(default_factory=list)
    actual_cash: Literal[False] = False
    permits_live_order: Literal[False] = False
    permits_paper_order: Literal[False] = False
    permits_actual_cash: Literal[False] = False
    summary: dict[str, bool | float | int | str]

    @field_validator("gate_id", "candidate_id", "family_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("evaluated_at", mode="before")
    @classmethod
    def validate_evaluated_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("evaluated_at", value)

    @field_serializer("evaluated_at")
    def serialize_evaluated_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


def build_backtest_kill_gate(
    gate_input: BacktestKillGateInput,
    *,
    gate_id: str,
    evaluated_at: datetime | str,
) -> BacktestKillGateDecision:
    evaluated_at_dt = ensure_utc_aware("evaluated_at", evaluated_at)
    blocker_codes: list[str] = []
    gate_state = BacktestKillGateState.SHORTLIST_FOR_VIRTUAL
    min_event_count = gate_input.family_event_count_policy.min_event_count_default

    if not gate_input.no_trade_comparison_present:
        blocker_codes.append("missing_no_trade_comparison")
        gate_state = BacktestKillGateState.INCONCLUSIVE_DATA
    elif min_event_count is not None and gate_input.event_count < min_event_count:
        blocker_codes.append("event_count_below_family_policy")
        gate_state = BacktestKillGateState(
            gate_input.family_event_count_policy.insufficient_data_state
        )
    elif gate_input.execution_candidate and gate_input.source_gap_count > 0:
        blocker_codes.append("source_gap_for_execution_candidate")
        gate_state = BacktestKillGateState.INCONCLUSIVE_DATA
    elif gate_input.after_cost_edge_over_no_trade <= 0:
        blocker_codes.append("after_cost_edge_over_no_trade_nonpositive")
        gate_state = BacktestKillGateState.KILL
    elif gate_input.stress_edge_over_no_trade <= 0:
        blocker_codes.append("stress_edge_over_no_trade_nonpositive")
        gate_state = BacktestKillGateState.KILL
    elif gate_input.unexecutable_reason_count > 0:
        blocker_codes.append("unexecutable_reason_present")
        gate_state = BacktestKillGateState.KILL
    elif gate_input.selection_adjustment_status is SelectionAdjustmentStatus.NOT_ESTIMABLE:
        blocker_codes.append("selection_adjustment_not_estimable")
        gate_state = BacktestKillGateState.RESEARCH_ONLY

    return BacktestKillGateDecision(
        gate_id=gate_id,
        evaluated_at=evaluated_at_dt,
        candidate_id=gate_input.candidate_id,
        mode=gate_input.mode,
        family_id=gate_input.family_id,
        gate_state=gate_state,
        blocker_codes=blocker_codes,
        summary={
            "event_count": gate_input.event_count,
            "closed_trade_count": gate_input.closed_trade_count,
            "no_trade_comparison_present": gate_input.no_trade_comparison_present,
            "after_cost_edge_over_no_trade": gate_input.after_cost_edge_over_no_trade,
            "stress_edge_over_no_trade": gate_input.stress_edge_over_no_trade,
            "largest_loss_usd": gate_input.largest_loss_usd,
            "profit_concentration": gate_input.profit_concentration,
            "regime_stability": gate_input.regime_stability,
            "source_gap_count": gate_input.source_gap_count,
            "unexecutable_reason_count": gate_input.unexecutable_reason_count,
            "selection_adjustment_status": gate_input.selection_adjustment_status.value,
            "execution_candidate": gate_input.execution_candidate,
        },
    )
