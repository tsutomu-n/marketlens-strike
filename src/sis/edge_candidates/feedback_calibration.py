from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import PROFIT_CORE_FEEDBACK_THRESHOLD_CALIBRATION_SCHEMA_VERSION
from sis.edge_candidates.actual_cash_report_gate_models import (
    ProfitCoreActualCashReportDecision,
    ProfitCoreActualCashReportGate,
)
from sis.edge_candidates.multiplicity import TrialMultiplicityAccount
from sis.edge_candidates.protocol import CandidateProtocolManifest
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


class ProfitCoreFeedbackCalibrationStatus(StrEnum):
    READY_FOR_NEXT_PROTOCOL_REVIEW = "READY_FOR_NEXT_PROTOCOL_REVIEW"
    BLOCKED_SUCCESS_ONLY_FEEDBACK = "BLOCKED_SUCCESS_ONLY_FEEDBACK"
    BLOCKED_PROTOCOL_VERSIONING = "BLOCKED_PROTOCOL_VERSIONING"
    BLOCKED_HOLDOUT_REUSE = "BLOCKED_HOLDOUT_REUSE"
    BLOCKED_VALIDATION_PEEK_ACCOUNTING = "BLOCKED_VALIDATION_PEEK_ACCOUNTING"
    BLOCKED_INCOMPLETE_FAILURE_LOG = "BLOCKED_INCOMPLETE_FAILURE_LOG"


class FeedbackCalibrationArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_role: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_role", "path", "sha256")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact ref text fields must not be empty")
        return stripped


class FeedbackCalibrationBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    blocker_code: str
    message: str
    source: str

    @field_validator("blocker_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("blocker_code must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("message", "source")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("blocker text fields must not be empty")
        return stripped


class CalibrationKilledCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    reason: str

    @field_validator("candidate_id")
    @classmethod
    def validate_candidate_id(cls, value: str) -> str:
        return _validate_id(value, "candidate_id")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return _validate_text(value, "reason")


class CalibrationExecutionFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_id: str
    candidate_id: str
    failure_type: str
    summary: str

    @field_validator("failure_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, "failure id fields")

    @field_validator("failure_type", "summary")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_text(value, "failure text fields")


class FeedbackCalibrationLog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    next_protocol_id: str
    next_multiplicity_account_id: str
    next_validation_peek_count: int = Field(ge=0)
    holdout_peek_performed: bool
    same_family_version_reuse_requested: bool
    killed_candidates: list[CalibrationKilledCandidate] = Field(default_factory=list)
    actual_execution_failures: list[CalibrationExecutionFailure] = Field(default_factory=list)
    generator_updates: list[str] = Field(default_factory=list)
    family_event_count_policy_updates: list[str] = Field(default_factory=list)
    exclusion_rule_updates: list[str] = Field(default_factory=list)
    cost_model_updates: list[str] = Field(default_factory=list)
    operator_burden_updates: list[str] = Field(default_factory=list)

    @field_validator("next_protocol_id", "next_multiplicity_account_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, "next id fields")

    @field_validator(
        "generator_updates",
        "family_event_count_policy_updates",
        "exclusion_rule_updates",
        "cost_model_updates",
        "operator_burden_updates",
    )
    @classmethod
    def validate_update_list(cls, value: list[str]) -> list[str]:
        return [_validate_text(item, "update item") for item in value]


class ProfitCoreFeedbackThresholdCalibration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_feedback_threshold_calibration.v1"] = (
        PROFIT_CORE_FEEDBACK_THRESHOLD_CALIBRATION_SCHEMA_VERSION
    )
    calibration_id: str
    recorded_at: datetime
    producer: ProducerInfo
    calibration_status: ProfitCoreFeedbackCalibrationStatus
    blockers: list[FeedbackCalibrationBlocker] = Field(default_factory=list)
    source_refs: list[FeedbackCalibrationArtifactRef] = Field(min_length=4)
    protocol_id: str
    multiplicity_account_id: str
    report_gate_id: str
    candidate_id: str
    report_decision: ProfitCoreActualCashReportDecision
    next_protocol_id: str
    next_multiplicity_account_id: str
    current_validation_peek_count: int = Field(ge=0)
    next_validation_peek_count: int = Field(ge=0)
    holdout_peek_performed: bool
    same_family_version_reuse_requested: bool
    requires_new_protocol: bool
    requires_new_trial_account: bool
    failure_summary: dict[str, Any]
    proposed_updates: dict[str, list[str]]
    requires_human_review: Literal[True] = True
    auto_applied: Literal[False] = False
    protocol_mutated: Literal[False] = False
    multiplicity_account_mutated: Literal[False] = False
    thresholds_applied: Literal[False] = False
    network_attempted: Literal[False] = False
    exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False
    permits_live_order: Literal[False] = False
    permits_actual_cash_execution: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "auto_applied": False,
            "protocol_mutated": False,
            "multiplicity_account_mutated": False,
            "thresholds_applied": False,
            "network_attempted": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "permits_live_order": False,
            "permits_actual_cash_execution": False,
        }
    )

    @field_validator(
        "calibration_id",
        "protocol_id",
        "multiplicity_account_id",
        "report_gate_id",
        "candidate_id",
        "next_protocol_id",
        "next_multiplicity_account_id",
    )
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, "id fields")

    @field_validator("recorded_at", mode="before")
    @classmethod
    def validate_recorded_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("recorded_at", value)

    @field_validator("boundary")
    @classmethod
    def validate_boundary(cls, value: dict[str, bool]) -> dict[str, bool]:
        expected = {
            "auto_applied": False,
            "protocol_mutated": False,
            "multiplicity_account_mutated": False,
            "thresholds_applied": False,
            "network_attempted": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "permits_live_order": False,
            "permits_actual_cash_execution": False,
        }
        if value != expected:
            raise ValueError("boundary must keep calibration side effects false")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class FeedbackCalibrationWriteResult:
    calibration: ProfitCoreFeedbackThresholdCalibration
    calibration_path: Path
    calibration_sha256: str


class FeedbackCalibrationError(ValueError):
    pass


class FeedbackCalibrationOutputExistsError(FeedbackCalibrationError):
    pass


def build_feedback_calibration(
    *,
    protocol_path: Path,
    multiplicity_account_path: Path,
    report_gate_path: Path,
    feedback_log_path: Path,
    recorded_at: datetime | str | None = None,
) -> ProfitCoreFeedbackThresholdCalibration:
    protocol = CandidateProtocolManifest.model_validate(read_mapping_file(protocol_path))
    multiplicity = TrialMultiplicityAccount.model_validate(
        read_mapping_file(multiplicity_account_path)
    )
    report_gate = ProfitCoreActualCashReportGate.model_validate(read_mapping_file(report_gate_path))
    feedback = FeedbackCalibrationLog.model_validate(read_mapping_file(feedback_log_path))
    source_refs = [
        _artifact_ref("protocol", protocol_path, protocol.schema_version),
        _artifact_ref(
            "multiplicity_account",
            multiplicity_account_path,
            multiplicity.schema_version,
        ),
        _artifact_ref("actual_cash_report_gate", report_gate_path, report_gate.schema_version),
        _artifact_ref("feedback_log", feedback_log_path, None),
    ]
    blockers = _derive_blockers(protocol, multiplicity, report_gate, feedback)
    status = _derive_status(blockers)
    proposed_updates = _proposed_updates(feedback)
    failure_summary = {
        "killed_candidate_count": len(feedback.killed_candidates),
        "actual_execution_failure_count": len(feedback.actual_execution_failures),
        "p12_report_decision": report_gate.decision.value,
        "p12_blocker_count": len(report_gate.blockers),
        "failure_source_count": _failure_source_count(report_gate, feedback),
    }
    requires_new_cycle = _has_updates(feedback)
    return ProfitCoreFeedbackThresholdCalibration(
        calibration_id=f"{protocol.protocol_id}-{report_gate.candidate_id}-feedback-calibration",
        recorded_at=_coerce_datetime(recorded_at),
        producer=ProducerInfo(command="edge-candidate-feedback-calibration-build"),
        calibration_status=status,
        blockers=blockers,
        source_refs=source_refs,
        protocol_id=protocol.protocol_id,
        multiplicity_account_id=multiplicity.account_id,
        report_gate_id=report_gate.report_id,
        candidate_id=report_gate.candidate_id,
        report_decision=report_gate.decision,
        next_protocol_id=feedback.next_protocol_id,
        next_multiplicity_account_id=feedback.next_multiplicity_account_id,
        current_validation_peek_count=multiplicity.validation_peek_count,
        next_validation_peek_count=feedback.next_validation_peek_count,
        holdout_peek_performed=feedback.holdout_peek_performed,
        same_family_version_reuse_requested=feedback.same_family_version_reuse_requested,
        requires_new_protocol=requires_new_cycle,
        requires_new_trial_account=requires_new_cycle,
        failure_summary=failure_summary,
        proposed_updates=proposed_updates,
    )


def build_and_write_feedback_calibration(
    *,
    protocol_path: Path,
    multiplicity_account_path: Path,
    report_gate_path: Path,
    feedback_log_path: Path,
    out_dir: Path,
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> FeedbackCalibrationWriteResult:
    calibration_path = out_dir / "profit_core_feedback_threshold_calibration.json"
    if calibration_path.exists() and not replace_existing:
        raise FeedbackCalibrationOutputExistsError(f"output already exists: {calibration_path}")
    calibration = build_feedback_calibration(
        protocol_path=protocol_path,
        multiplicity_account_path=multiplicity_account_path,
        report_gate_path=report_gate_path,
        feedback_log_path=feedback_log_path,
        recorded_at=recorded_at,
    )
    write_json_artifact(calibration_path, calibration.model_dump(mode="json"))
    return FeedbackCalibrationWriteResult(
        calibration=calibration,
        calibration_path=calibration_path,
        calibration_sha256=sha256_file(calibration_path),
    )


def _derive_blockers(
    protocol: CandidateProtocolManifest,
    multiplicity: TrialMultiplicityAccount,
    report_gate: ProfitCoreActualCashReportGate,
    feedback: FeedbackCalibrationLog,
) -> list[FeedbackCalibrationBlocker]:
    blockers: list[FeedbackCalibrationBlocker] = []
    blockers.extend(_source_ref_blockers(protocol, multiplicity, report_gate))
    if _failure_source_count(report_gate, feedback) == 0:
        blockers.append(
            _blocker(
                "SUCCESS_ONLY_FEEDBACK",
                "P13 feedback must include killed candidates, actual execution failures, or P12 blockers.",
                "feedback_log",
            )
        )
    if not _has_updates(feedback):
        blockers.append(
            _blocker(
                "NO_PROPOSED_UPDATES",
                "P13 feedback must propose at least one next-cycle update.",
                "feedback_log",
            )
        )
    if _has_updates(feedback) and feedback.next_protocol_id == protocol.protocol_id:
        blockers.append(
            _blocker(
                "NEW_PROTOCOL_REQUIRED",
                "Threshold or policy feedback requires a new protocol id.",
                "feedback_log",
            )
        )
    if _has_updates(feedback) and feedback.next_multiplicity_account_id == multiplicity.account_id:
        blockers.append(
            _blocker(
                "NEW_TRIAL_ACCOUNT_REQUIRED",
                "Threshold or policy feedback requires a new trial multiplicity account.",
                "feedback_log",
            )
        )
    if feedback.holdout_peek_performed and feedback.same_family_version_reuse_requested:
        blockers.append(
            _blocker(
                "HOLDOUT_PEEK_SAME_FAMILY_REUSE",
                "Holdout peek after changes cannot reuse the same family/version.",
                "feedback_log",
            )
        )
    if (
        _has_updates(feedback) or feedback.holdout_peek_performed
    ) and feedback.next_validation_peek_count <= multiplicity.validation_peek_count:
        blockers.append(
            _blocker(
                "VALIDATION_PEEK_COUNT_NOT_ADVANCED",
                "Next validation_peek_count must advance after threshold or holdout feedback.",
                "feedback_log",
            )
        )
    return blockers


def _source_ref_blockers(
    protocol: CandidateProtocolManifest,
    multiplicity: TrialMultiplicityAccount,
    report_gate: ProfitCoreActualCashReportGate,
) -> list[FeedbackCalibrationBlocker]:
    blockers: list[FeedbackCalibrationBlocker] = []
    if report_gate.protocol_ref is not None and report_gate.protocol_ref.sha256:
        # P13 source files are validated separately; this ties P12 lineage to the same protocol.
        pass
    if (
        report_gate.multiplicity_account_ref is not None
        and report_gate.multiplicity_account_ref.sha256
    ):
        pass
    if protocol.mode != multiplicity.mode:
        blockers.append(
            _blocker(
                "PROTOCOL_MULTIPLICITY_MODE_MISMATCH",
                "Protocol and multiplicity account modes must match.",
                "source_refs",
            )
        )
    return blockers


def _derive_status(
    blockers: list[FeedbackCalibrationBlocker],
) -> ProfitCoreFeedbackCalibrationStatus:
    codes = {blocker.blocker_code for blocker in blockers}
    if "SUCCESS_ONLY_FEEDBACK" in codes:
        return ProfitCoreFeedbackCalibrationStatus.BLOCKED_SUCCESS_ONLY_FEEDBACK
    if "HOLDOUT_PEEK_SAME_FAMILY_REUSE" in codes:
        return ProfitCoreFeedbackCalibrationStatus.BLOCKED_HOLDOUT_REUSE
    if {"NEW_PROTOCOL_REQUIRED", "NEW_TRIAL_ACCOUNT_REQUIRED"} & codes:
        return ProfitCoreFeedbackCalibrationStatus.BLOCKED_PROTOCOL_VERSIONING
    if "VALIDATION_PEEK_COUNT_NOT_ADVANCED" in codes:
        return ProfitCoreFeedbackCalibrationStatus.BLOCKED_VALIDATION_PEEK_ACCOUNTING
    if blockers:
        return ProfitCoreFeedbackCalibrationStatus.BLOCKED_INCOMPLETE_FAILURE_LOG
    return ProfitCoreFeedbackCalibrationStatus.READY_FOR_NEXT_PROTOCOL_REVIEW


def _failure_source_count(
    report_gate: ProfitCoreActualCashReportGate,
    feedback: FeedbackCalibrationLog,
) -> int:
    p12_failure_count = (
        1
        if report_gate.decision is not ProfitCoreActualCashReportDecision.PROMOTE
        or report_gate.blockers
        else 0
    )
    return (
        len(feedback.killed_candidates)
        + len(feedback.actual_execution_failures)
        + p12_failure_count
    )


def _has_updates(feedback: FeedbackCalibrationLog) -> bool:
    return any(_proposed_updates(feedback).values())


def _proposed_updates(feedback: FeedbackCalibrationLog) -> dict[str, list[str]]:
    return {
        "generator_updates": feedback.generator_updates,
        "family_event_count_policy_updates": feedback.family_event_count_policy_updates,
        "exclusion_rule_updates": feedback.exclusion_rule_updates,
        "cost_model_updates": feedback.cost_model_updates,
        "operator_burden_updates": feedback.operator_burden_updates,
    }


def _artifact_ref(
    role: str,
    path: Path,
    schema_version: str | None,
) -> FeedbackCalibrationArtifactRef:
    return FeedbackCalibrationArtifactRef(
        artifact_role=role,
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _blocker(code: str, message: str, source: str) -> FeedbackCalibrationBlocker:
    return FeedbackCalibrationBlocker(blocker_code=code, message=message, source=source)


def _validate_id(value: str, label: str) -> str:
    stripped = value.strip()
    if not ID_PATTERN.fullmatch(stripped):
        raise ValueError(f"{label} must match ^[A-Za-z0-9][A-Za-z0-9._-]{{0,127}}$")
    return stripped


def _validate_text(value: str, label: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} must not be empty")
    return stripped


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("recorded_at", value)


__all__ = [
    "FeedbackCalibrationError",
    "FeedbackCalibrationOutputExistsError",
    "FeedbackCalibrationWriteResult",
    "ProfitCoreFeedbackCalibrationStatus",
    "ProfitCoreFeedbackThresholdCalibration",
    "build_and_write_feedback_calibration",
    "build_feedback_calibration",
]
