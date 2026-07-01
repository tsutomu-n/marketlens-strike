from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import VIRTUAL_EXECUTION_GATE_SCHEMA_VERSION
from sis.edge_candidates.backtest_kill_gate import BacktestKillGateDecision
from sis.edge_candidates.multiplicity import TrialMultiplicityAccount
from sis.edge_candidates.protocol import CandidateProtocolMode
from sis.strategy_idea_candidates.models import (
    CandidateDecision,
    StrategyIdeaCandidate,
    StrategyIdeaCandidateSet,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact


class VirtualExecutionEventType(StrEnum):
    SUBMIT_ACK = "SUBMIT_ACK"
    PARTIAL_FILL = "PARTIAL_FILL"
    CANCEL_ACK = "CANCEL_ACK"
    SUBMIT_REJECTED = "SUBMIT_REJECTED"
    RECONCILED_FLAT = "RECONCILED_FLAT"
    UNKNOWN_STATE = "UNKNOWN_STATE"


class VirtualExecutionGateState(StrEnum):
    LOCAL_MOCK_VERIFIED = "LOCAL_MOCK_VERIFIED"
    BLOCKED_BY_CANDIDATE_STATE = "BLOCKED_BY_CANDIDATE_STATE"
    BLOCKED_BY_BACKTEST_GATE = "BLOCKED_BY_BACKTEST_GATE"
    BLOCKED_BY_MULTIPLICITY_ACCOUNT = "BLOCKED_BY_MULTIPLICITY_ACCOUNT"
    BLOCKED_BY_VIRTUAL_LIFECYCLE = "BLOCKED_BY_VIRTUAL_LIFECYCLE"
    BLOCKED_BY_ARTIFACT_MISMATCH = "BLOCKED_BY_ARTIFACT_MISMATCH"


class VirtualExecutionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: VirtualExecutionEventType
    order_id: str = "virtual-order-001"
    filled_quantity: float | None = Field(default=None, ge=0)
    position_after: float | None = None
    reject_reason: str | None = None

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("order_id must not be empty")
        return stripped

    @field_validator("reject_reason")
    @classmethod
    def validate_reject_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("reject_reason must not be empty when provided")
        return stripped


class VirtualExecutionGateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    mode: CandidateProtocolMode
    candidate_decision: CandidateDecision
    backtest_gate_state: str
    multiplicity_success_only_reporting: bool
    multiplicity_sealed_test_used_for_selection: bool
    unexecutable_reason_count: int = Field(ge=0)
    lifecycle_events: list[VirtualExecutionEvent] = Field(min_length=1)
    artifact_mismatch_blockers: list[str] = Field(default_factory=list)

    @field_validator("candidate_id")
    @classmethod
    def validate_candidate_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("candidate_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("backtest_gate_state")
    @classmethod
    def validate_backtest_gate_state(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("backtest_gate_state must not be empty")
        return stripped


class VirtualExecutionGateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["virtual_execution_gate.v1"] = VIRTUAL_EXECUTION_GATE_SCHEMA_VERSION
    gate_id: str
    evaluated_at: datetime
    candidate_id: str
    mode: CandidateProtocolMode
    gate_state: VirtualExecutionGateState
    blocker_codes: list[str] = Field(default_factory=list)
    lifecycle_events: list[VirtualExecutionEvent] = Field(min_length=1)
    cash_metric_basis: Literal["virtual_exchange"] = "virtual_exchange"
    evidence_basis: Literal["virtual_exchange"] = "virtual_exchange"
    actual_cash: Literal[False] = False
    permits_live_order: Literal[False] = False
    permits_paper_order: Literal[False] = False
    permits_actual_cash: Literal[False] = False
    production_exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    virtual_pnl_evaluated: Literal[False] = False
    artifact_refs: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, bool | float | int | str]

    @field_validator("gate_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
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


@dataclass(frozen=True)
class VirtualExecutionGateWriteResult:
    gate: VirtualExecutionGateDecision
    gate_path: Path
    gate_sha256: str


class VirtualExecutionGateError(ValueError):
    pass


class VirtualExecutionGateOutputExistsError(VirtualExecutionGateError):
    pass


def default_local_mock_lifecycle_events() -> list[VirtualExecutionEvent]:
    return [
        VirtualExecutionEvent(event_type=VirtualExecutionEventType.SUBMIT_ACK),
        VirtualExecutionEvent(
            event_type=VirtualExecutionEventType.PARTIAL_FILL,
            filled_quantity=0.5,
            position_after=0.5,
        ),
        VirtualExecutionEvent(event_type=VirtualExecutionEventType.CANCEL_ACK),
        VirtualExecutionEvent(
            event_type=VirtualExecutionEventType.RECONCILED_FLAT,
            position_after=0.0,
        ),
    ]


def build_virtual_execution_gate(
    gate_input: VirtualExecutionGateInput,
    *,
    gate_id: str,
    evaluated_at: datetime | str,
    artifact_refs: dict[str, Any] | None = None,
) -> VirtualExecutionGateDecision:
    blocker_codes: list[str] = []
    blocker_codes.extend(gate_input.artifact_mismatch_blockers)

    candidate_blockers = _candidate_blockers(gate_input)
    backtest_blockers = _backtest_blockers(gate_input)
    multiplicity_blockers = _multiplicity_blockers(gate_input)
    lifecycle_blockers, lifecycle_summary = _lifecycle_blockers(gate_input.lifecycle_events)
    blocker_codes.extend(candidate_blockers)
    blocker_codes.extend(backtest_blockers)
    blocker_codes.extend(multiplicity_blockers)
    blocker_codes.extend(lifecycle_blockers)

    gate_state = VirtualExecutionGateState.LOCAL_MOCK_VERIFIED
    if gate_input.artifact_mismatch_blockers:
        gate_state = VirtualExecutionGateState.BLOCKED_BY_ARTIFACT_MISMATCH
    elif candidate_blockers:
        gate_state = VirtualExecutionGateState.BLOCKED_BY_CANDIDATE_STATE
    elif backtest_blockers:
        gate_state = VirtualExecutionGateState.BLOCKED_BY_BACKTEST_GATE
    elif multiplicity_blockers:
        gate_state = VirtualExecutionGateState.BLOCKED_BY_MULTIPLICITY_ACCOUNT
    elif lifecycle_blockers:
        gate_state = VirtualExecutionGateState.BLOCKED_BY_VIRTUAL_LIFECYCLE

    evaluated_at_dt = ensure_utc_aware("evaluated_at", evaluated_at)
    return VirtualExecutionGateDecision(
        gate_id=gate_id,
        evaluated_at=evaluated_at_dt,
        candidate_id=gate_input.candidate_id,
        mode=gate_input.mode,
        gate_state=gate_state,
        blocker_codes=list(dict.fromkeys(blocker_codes)),
        lifecycle_events=gate_input.lifecycle_events,
        artifact_refs=artifact_refs or {},
        summary={
            **lifecycle_summary,
            "candidate_decision": gate_input.candidate_decision.value,
            "backtest_gate_state": gate_input.backtest_gate_state,
            "multiplicity_success_only_reporting": (gate_input.multiplicity_success_only_reporting),
            "multiplicity_sealed_test_used_for_selection": (
                gate_input.multiplicity_sealed_test_used_for_selection
            ),
            "unexecutable_reason_count": gate_input.unexecutable_reason_count,
            "blocker_count": len(set(blocker_codes)),
            "profit_evidence": False,
        },
    )


def build_and_write_virtual_execution_gate(
    *,
    candidate_set_path: Path,
    factory_summary_path: Path,
    multiplicity_account_path: Path,
    backtest_kill_gate_path: Path,
    candidate_id: str,
    out_dir: Path,
    lifecycle_events: list[VirtualExecutionEvent] | None = None,
    evaluated_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> VirtualExecutionGateWriteResult:
    gate_path = out_dir / "virtual_execution_gate.json"
    if gate_path.exists() and not replace_existing:
        raise VirtualExecutionGateOutputExistsError(f"output already exists: {gate_path}")

    candidate_set = StrategyIdeaCandidateSet.model_validate(read_mapping_file(candidate_set_path))
    factory_summary = read_mapping_file(factory_summary_path)
    multiplicity = TrialMultiplicityAccount.model_validate(
        read_mapping_file(multiplicity_account_path)
    )
    backtest_gate = BacktestKillGateDecision.model_validate(
        read_mapping_file(backtest_kill_gate_path)
    )
    candidate = _candidate_by_id(candidate_set, candidate_id)
    artifact_blockers = _artifact_mismatch_blockers(
        factory_summary=factory_summary,
        candidate_set_path=candidate_set_path,
        multiplicity_account_path=multiplicity_account_path,
    )
    artifact_refs = {
        "candidate_set_path": candidate_set_path.as_posix(),
        "candidate_set_sha256": sha256_file(candidate_set_path),
        "factory_summary_path": factory_summary_path.as_posix(),
        "factory_summary_sha256": sha256_file(factory_summary_path),
        "multiplicity_account_path": multiplicity_account_path.as_posix(),
        "multiplicity_account_sha256": sha256_file(multiplicity_account_path),
        "backtest_kill_gate_path": backtest_kill_gate_path.as_posix(),
        "backtest_kill_gate_sha256": sha256_file(backtest_kill_gate_path),
    }
    timestamp = evaluated_at or backtest_gate.evaluated_at
    gate_input = VirtualExecutionGateInput(
        candidate_id=candidate_id,
        mode=backtest_gate.mode,
        candidate_decision=candidate.decision,
        backtest_gate_state=backtest_gate.gate_state.value,
        multiplicity_success_only_reporting=multiplicity.success_only_reporting,
        multiplicity_sealed_test_used_for_selection=(multiplicity.sealed_test_used_for_selection),
        unexecutable_reason_count=_candidate_unexecutable_reason_count(candidate),
        lifecycle_events=lifecycle_events or default_local_mock_lifecycle_events(),
        artifact_mismatch_blockers=artifact_blockers,
    )
    gate = build_virtual_execution_gate(
        gate_input,
        gate_id=f"{candidate_id}-virtual-execution-gate",
        evaluated_at=timestamp,
        artifact_refs=artifact_refs,
    )
    write_json_artifact(gate_path, gate.model_dump(mode="json"))
    return VirtualExecutionGateWriteResult(
        gate=gate,
        gate_path=gate_path,
        gate_sha256=sha256_file(gate_path),
    )


def _candidate_blockers(gate_input: VirtualExecutionGateInput) -> list[str]:
    blockers: list[str] = []
    if gate_input.candidate_decision is not CandidateDecision.SHORTLISTED:
        blockers.append("candidate_not_shortlisted")
    if gate_input.unexecutable_reason_count > 0:
        blockers.append("unexecutable_reason_present")
    return blockers


def _backtest_blockers(gate_input: VirtualExecutionGateInput) -> list[str]:
    if gate_input.backtest_gate_state != "SHORTLIST_FOR_VIRTUAL":
        return ["backtest_gate_not_shortlist_for_virtual"]
    return []


def _multiplicity_blockers(gate_input: VirtualExecutionGateInput) -> list[str]:
    blockers: list[str] = []
    if gate_input.multiplicity_success_only_reporting:
        blockers.append("success_only_reporting")
    if gate_input.multiplicity_sealed_test_used_for_selection:
        blockers.append("sealed_test_used_for_selection")
    return blockers


def _lifecycle_blockers(
    events: list[VirtualExecutionEvent],
) -> tuple[list[str], dict[str, bool | float | int | str]]:
    event_types = [event.event_type for event in events]
    submit_events = [
        event
        for event in events
        if event.event_type
        in {VirtualExecutionEventType.SUBMIT_ACK, VirtualExecutionEventType.SUBMIT_REJECTED}
    ]
    partial_fills = [
        event for event in events if event.event_type is VirtualExecutionEventType.PARTIAL_FILL
    ]
    cancel_events = [
        event for event in events if event.event_type is VirtualExecutionEventType.CANCEL_ACK
    ]
    reconciliations = [
        event for event in events if event.event_type is VirtualExecutionEventType.RECONCILED_FLAT
    ]
    blockers: list[str] = []

    if VirtualExecutionEventType.UNKNOWN_STATE in event_types:
        blockers.append("unknown_lifecycle_state")
    if len(submit_events) > 1:
        blockers.append("duplicate_submit_detected")
    rejected = [
        event
        for event in submit_events
        if event.event_type is VirtualExecutionEventType.SUBMIT_REJECTED
    ]
    if rejected:
        if any(event.reject_reason is None for event in rejected):
            blockers.append("submit_reject_reason_missing")
        blockers.append("submit_rejected")
    if VirtualExecutionEventType.SUBMIT_ACK not in event_types:
        blockers.append("missing_submit_ack")
    if not any((event.filled_quantity or 0) > 0 for event in partial_fills):
        blockers.append("missing_partial_fill")
    if not cancel_events:
        blockers.append("missing_cancel_ack")
    if not reconciliations:
        blockers.append("missing_flat_reconciliation")
    elif any(event.position_after != 0 for event in reconciliations):
        blockers.append("flat_reconciliation_mismatch")

    return list(dict.fromkeys(blockers)), {
        "submit_ack_checked": VirtualExecutionEventType.SUBMIT_ACK in event_types,
        "partial_fill_checked": any((event.filled_quantity or 0) > 0 for event in partial_fills),
        "cancel_checked": bool(cancel_events),
        "duplicate_prevention_checked": len(submit_events) == 1,
        "flat_reconciliation_checked": bool(reconciliations)
        and all(event.position_after == 0 for event in reconciliations),
        "submit_reject_reason_checked": all(event.reject_reason for event in rejected)
        if rejected
        else True,
        "event_count": len(events),
    }


def _candidate_by_id(
    candidate_set: StrategyIdeaCandidateSet,
    candidate_id: str,
) -> StrategyIdeaCandidate:
    for candidate in candidate_set.candidate_inventory:
        if candidate.idea_candidate_id == candidate_id:
            return candidate
    raise VirtualExecutionGateError(f"candidate not found: {candidate_id}")


def _candidate_unexecutable_reason_count(candidate: StrategyIdeaCandidate) -> int:
    reason = candidate.rejection_reason or ""
    if reason.startswith("missing perp risk modeling fields"):
        return 1
    return 0


def _artifact_mismatch_blockers(
    *,
    factory_summary: dict[str, Any],
    candidate_set_path: Path,
    multiplicity_account_path: Path,
) -> list[str]:
    artifact_refs = factory_summary.get("artifact_refs")
    if not isinstance(artifact_refs, dict):
        return ["factory_summary_artifact_refs_missing"]
    blockers: list[str] = []
    expected_candidate_set_hash = artifact_refs.get("candidate_set_sha256")
    if expected_candidate_set_hash is not None and expected_candidate_set_hash != sha256_file(
        candidate_set_path
    ):
        blockers.append("candidate_set_sha_mismatch")
    expected_multiplicity_hash = artifact_refs.get("multiplicity_account_sha256")
    if expected_multiplicity_hash is not None and expected_multiplicity_hash != sha256_file(
        multiplicity_account_path
    ):
        blockers.append("multiplicity_account_sha_mismatch")
    return blockers


__all__ = [
    "VirtualExecutionEvent",
    "VirtualExecutionEventType",
    "VirtualExecutionGateDecision",
    "VirtualExecutionGateError",
    "VirtualExecutionGateInput",
    "VirtualExecutionGateOutputExistsError",
    "VirtualExecutionGateState",
    "VirtualExecutionGateWriteResult",
    "build_and_write_virtual_execution_gate",
    "build_virtual_execution_gate",
    "default_local_mock_lifecycle_events",
]
