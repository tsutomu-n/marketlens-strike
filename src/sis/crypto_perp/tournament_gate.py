from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)
from sis.crypto_perp.tournament import CryptoPerpTournamentReport, TournamentScore


TOURNAMENT_GATE_SCHEMA_VERSION = "crypto_perp_tournament_gate.v1"
TournamentGateStatus = Literal[
    "READY_FOR_HUMAN_TINY_LIVE_REVIEW",
    "NEEDS_MORE_EVIDENCE",
    "NEEDS_ACTUAL_CASH",
    "HOLD_NO_TRADE_LEADS",
    "REVISE_OR_RETIRE",
]
TournamentGateRecommendedAction = Literal[
    "PREPARE_TINY_LIVE_APPROVAL_PACKET",
    "COLLECT_MORE_EVENTS",
    "REBUILD_WITH_ACTUAL_CASH",
    "KEEP_CAPTURING_NO_TRADE",
    "REVISE_EVENT_DEFINITION",
]

PROXY_KNOWN_GAPS = {
    "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH",
    "FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED",
    "ESTIMATE_NOT_ACTUAL_CASH",
    "ACTUAL_CASH_RESULT_NOT_AVAILABLE",
}


class TournamentGatePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_largest_loss_usd: DecimalValue = Decimal("25")
    max_profit_concentration: DecimalValue = Decimal("0.60")
    max_operator_time_minutes: DecimalValue = Decimal("120")
    allow_no_trade_leader: bool = False

    @field_validator(
        "max_largest_loss_usd",
        "max_profit_concentration",
        "max_operator_time_minutes",
    )
    @classmethod
    def validate_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("policy thresholds must be non-negative")
        return value

    @field_serializer(
        "max_largest_loss_usd",
        "max_profit_concentration",
        "max_operator_time_minutes",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class TournamentGateCondition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: str
    passed: bool
    observed: str
    required: str
    severity: Literal["error", "warning"] = "error"


class CryptoPerpTournamentGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_tournament_gate.v1"] = TOURNAMENT_GATE_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    gate_id: str
    report_id: str
    gate_status: TournamentGateStatus
    recommended_action: TournamentGateRecommendedAction
    policy: TournamentGatePolicy
    passed_conditions: list[TournamentGateCondition]
    failed_conditions: list[TournamentGateCondition]
    warning_conditions: list[TournamentGateCondition]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_validator("artifact_id", "gate_id", "report_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _condition(
    condition_id: str, passed: bool, observed: Any, required: Any
) -> TournamentGateCondition:
    return TournamentGateCondition(
        condition_id=condition_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
    )


def _leader_score(report: CryptoPerpTournamentReport) -> TournamentScore | None:
    if report.leader_action is None:
        return None
    return next((score for score in report.scores if score.action == report.leader_action), None)


def _status_and_action(
    *,
    report: CryptoPerpTournamentReport,
    failed: list[TournamentGateCondition],
    proxy_gaps: set[str],
) -> tuple[TournamentGateStatus, TournamentGateRecommendedAction]:
    failed_ids = {condition.condition_id for condition in failed}
    if proxy_gaps or "actual_cash_basis" in failed_ids:
        return "NEEDS_ACTUAL_CASH", "REBUILD_WITH_ACTUAL_CASH"
    if report.tournament_status == "INCONCLUSIVE_DATA" or "report_complete" in failed_ids:
        return "NEEDS_MORE_EVIDENCE", "COLLECT_MORE_EVENTS"
    if "leader_not_no_trade" in failed_ids:
        return "HOLD_NO_TRADE_LEADS", "KEEP_CAPTURING_NO_TRADE"
    if failed:
        return "REVISE_OR_RETIRE", "REVISE_EVENT_DEFINITION"
    return "READY_FOR_HUMAN_TINY_LIVE_REVIEW", "PREPARE_TINY_LIVE_APPROVAL_PACKET"


def build_tournament_gate(
    *,
    report: CryptoPerpTournamentReport,
    created_at: datetime | str,
    policy: TournamentGatePolicy | None = None,
    source_refs: list[dict[str, str]] | None = None,
    gate_id: str | None = None,
    producer_command: str = "crypto-perp-tournament-gate",
) -> CryptoPerpTournamentGate:
    selected_policy = policy or TournamentGatePolicy()
    created = ensure_utc_aware("created_at", created_at)
    leader_score = _leader_score(report)
    proxy_gaps = set(report.known_gaps) & PROXY_KNOWN_GAPS
    actual_cash_basis = report.actual_cash and report.cash_metric_basis == "actual_cash"
    largest_loss = leader_score.largest_loss_usd if leader_score is not None else Decimal("0")
    profit_concentration = (
        leader_score.profit_concentration if leader_score is not None else Decimal("0")
    )
    operator_time = leader_score.operator_time_minutes if leader_score is not None else Decimal("0")
    conditions = [
        _condition(
            "report_complete",
            report.tournament_status == "COMPLETE",
            report.tournament_status,
            "COMPLETE",
        ),
        _condition(
            "leader_present",
            report.leader_action is not None,
            report.leader_action or "NONE",
            "non-null leader_action",
        ),
        _condition(
            "no_proxy_known_gap",
            not proxy_gaps,
            ",".join(sorted(proxy_gaps)) or "none",
            "no outcome_before_cost proxy gaps",
        ),
        _condition(
            "actual_cash_basis",
            actual_cash_basis,
            f"actual_cash={str(report.actual_cash).lower()}, cash_metric_basis={report.cash_metric_basis}",
            "actual_cash=true and cash_metric_basis=actual_cash",
        ),
        _condition(
            "leader_not_no_trade",
            selected_policy.allow_no_trade_leader or report.leader_action != "NO_TRADE",
            report.leader_action or "NONE",
            "leader_action other than NO_TRADE unless explicitly allowed",
        ),
        _condition(
            "largest_loss_within_limit",
            abs(min(largest_loss, Decimal("0"))) <= selected_policy.max_largest_loss_usd,
            largest_loss,
            f">= -{selected_policy.max_largest_loss_usd}",
        ),
        _condition(
            "profit_concentration_within_limit",
            profit_concentration <= selected_policy.max_profit_concentration,
            profit_concentration,
            f"<= {selected_policy.max_profit_concentration}",
        ),
        _condition(
            "operator_time_within_limit",
            operator_time <= selected_policy.max_operator_time_minutes,
            operator_time,
            f"<= {selected_policy.max_operator_time_minutes}",
        ),
    ]
    failed_conditions = [condition for condition in conditions if not condition.passed]
    passed_conditions = [condition for condition in conditions if condition.passed]
    gate_status, recommended_action = _status_and_action(
        report=report,
        failed=failed_conditions,
        proxy_gaps=proxy_gaps,
    )
    resolved_gate_id = gate_id or f"{report.report_id}-gate"
    summary = {
        "report_id": report.report_id,
        "gate_status": gate_status,
        "recommended_action": recommended_action,
        "leader_action": report.leader_action,
        "event_count": report.event_count,
        "actual_cash": report.actual_cash,
        "cash_metric_basis": report.cash_metric_basis,
        "proxy_gap_count": len(proxy_gaps),
        "failed_condition_count": len(failed_conditions),
    }
    return CryptoPerpTournamentGate(
        artifact_id=stable_hash(
            ["crypto-perp-tournament-gate-artifact", resolved_gate_id, serialize_utc_z(created)]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=list(source_refs or []),
        gate_id=resolved_gate_id,
        report_id=report.report_id,
        gate_status=gate_status,
        recommended_action=recommended_action,
        policy=selected_policy,
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=[],
        known_gaps=list(report.known_gaps),
        summary=summary,
    )
