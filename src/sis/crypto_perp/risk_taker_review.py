from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bias_guards import CryptoPerpBiasGuard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)
from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability, SourceId
from sis.crypto_perp.tournament import TOURNAMENT_ACTIONS, TournamentAction
from sis.crypto_perp.tournament_rows import CostAwareTournamentRow, CryptoPerpTournamentRowsV2


RISK_TAKER_REVIEW_SCHEMA_VERSION = "crypto_perp_risk_taker_review.v1"
OperatorJurisdictionStatus = Literal["allowed", "prohibited", "unknown"]
SourceFreshnessStatus = Literal["fresh", "stale", "unknown"]
RiskTakerReviewStatus = Literal[
    "READY_FOR_HUMAN_RISK_REVIEW",
    "NEEDS_ACTUAL_CASH",
    "BLOCKED_BY_VENUE",
    "INCONCLUSIVE_DATA",
    "KILL",
]
RiskTakerRecommendedAction = Literal[
    "PREPARE_HUMAN_REVIEW",
    "BUILD_ACTUAL_CASH_LEDGER",
    "KEEP_RESEARCH_LOCAL",
    "COLLECT_MISSING_SOURCES",
    "REJECT_CANDIDATE",
]

_ZERO = Decimal("0")
_DEFAULT_MAX_LARGEST_LOSS_USD = Decimal("25")
_DEFAULT_MAX_PROFIT_CONCENTRATION = Decimal("0.60")
_DEFAULT_MAX_OPERATOR_TIME_MINUTES = Decimal("120")
_REQUIRED_COST_ESTIMATE_SOURCES: tuple[SourceId, ...] = (
    "event",
    "bars",
    "ticker",
    "funding",
    "outcome",
)


class RiskTakerReviewCondition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: str
    passed: bool
    observed: str
    required: str
    severity: Literal["error", "warning"] = "error"


class CryptoPerpRiskTakerReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_risk_taker_review.v1"] = RISK_TAKER_REVIEW_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    review_id: str
    row_set_id: str
    source_availability_artifact_id: str
    bias_guard_id: str
    review_status: RiskTakerReviewStatus
    recommended_action: RiskTakerRecommendedAction
    operator_jurisdiction_status: OperatorJurisdictionStatus
    source_freshness_status: SourceFreshnessStatus
    venue_terms_checked_at: datetime | None = None
    leader_action: TournamentAction | None
    after_cost_edge_over_no_trade_usd: DecimalValue | None
    stress_edge_over_no_trade_usd: DecimalValue | None
    dollars_per_hour: DecimalValue | None
    largest_loss_usd: DecimalValue | None
    profit_concentration: DecimalValue | None
    liquidation_buffer_bps: DecimalValue | None
    conditions: list[RiskTakerReviewCondition]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_validator("venue_terms_checked_at", mode="before")
    @classmethod
    def validate_optional_utc(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc_aware("venue_terms_checked_at", value)

    @field_serializer("created_at", "venue_terms_checked_at")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return serialize_utc_z(value)

    @field_serializer(
        "after_cost_edge_over_no_trade_usd",
        "stress_edge_over_no_trade_usd",
        "dollars_per_hour",
        "largest_loss_usd",
        "profit_concentration",
        "liquidation_buffer_bps",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


def _condition(
    condition_id: str,
    passed: bool,
    observed: object,
    required: object,
) -> RiskTakerReviewCondition:
    return RiskTakerReviewCondition(
        condition_id=condition_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
    )


def _rows_for_action(
    rows: Sequence[CostAwareTournamentRow],
    action: TournamentAction,
) -> list[CostAwareTournamentRow]:
    return [row for row in rows if row.action == action]


def _sum_cost(rows: Sequence[CostAwareTournamentRow], action: TournamentAction) -> Decimal:
    return sum(
        (row.cost_adjusted_cash_estimate_usd for row in rows if row.action == action),
        _ZERO,
    )


def _sum_stress(rows: Sequence[CostAwareTournamentRow], action: TournamentAction) -> Decimal:
    return sum((row.stress_cash_estimate_usd for row in rows if row.action == action), _ZERO)


def _leader_action(rows: Sequence[CostAwareTournamentRow]) -> TournamentAction | None:
    totals = {action: _sum_cost(rows, action) for action in TOURNAMENT_ACTIONS}
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) < 2 or ordered[0][1] == ordered[1][1]:
        return None
    return ordered[0][0]


def _profit_concentration(values: Sequence[Decimal]) -> Decimal:
    positives = [value for value in values if value > 0]
    positive_total = sum(positives, _ZERO)
    if positive_total == 0:
        return _ZERO
    return max(positives) / positive_total


def _actual_cash_available(
    *,
    rows: Sequence[CostAwareTournamentRow],
    action: TournamentAction | None,
    source_availability: CryptoPerpSourceAvailability,
) -> bool:
    if action is None or action == "NO_TRADE":
        return False
    action_rows = _rows_for_action(rows, action)
    return bool(
        source_availability.can_compute_actual_cash
        and action_rows
        and all(
            row.evidence_level == "actual_cash" and row.actual_cash_result_usd is not None
            for row in action_rows
        )
    )


def _cost_source_gap_reasons(source_availability: CryptoPerpSourceAvailability) -> list[str]:
    reasons: list[str] = []
    by_source = {status.source_id: status for status in source_availability.source_statuses}
    if not source_availability.can_compute_cost_adjusted_estimate:
        reasons.append("COST_ADJUSTED_ESTIMATE_SOURCE_INSUFFICIENT")
    for source_id in _REQUIRED_COST_ESTIMATE_SOURCES:
        status = by_source.get(source_id)
        if status is None:
            reasons.append(f"{source_id.upper()}_SOURCE_STATUS_MISSING")
        elif not status.available:
            reasons.append(status.reason)
    return list(dict.fromkeys(reasons))


def _known_gap_list(
    *,
    rows_v2: CryptoPerpTournamentRowsV2,
    source_availability: CryptoPerpSourceAvailability,
    bias_guard: CryptoPerpBiasGuard,
    extra: Sequence[str],
) -> list[str]:
    gaps = [
        *rows_v2.known_gaps,
        *source_availability.known_gaps,
        *bias_guard.known_gaps,
        *bias_guard.stop_reasons,
        *extra,
    ]
    return [gap for gap in dict.fromkeys(gaps) if gap]


def _status_and_action(
    *,
    conditions: Sequence[RiskTakerReviewCondition],
) -> tuple[RiskTakerReviewStatus, RiskTakerRecommendedAction]:
    failed_ids = {condition.condition_id for condition in conditions if not condition.passed}
    if "operator_jurisdiction_allowed" in failed_ids:
        return "BLOCKED_BY_VENUE", "KEEP_RESEARCH_LOCAL"
    if failed_ids & {
        "source_freshness_fresh",
        "source_availability_cost_adjusted",
        "liquidation_buffer_present",
        "leader_present",
    }:
        return "INCONCLUSIVE_DATA", "COLLECT_MISSING_SOURCES"
    if failed_ids & {
        "leader_not_no_trade",
        "after_cost_edge_positive",
        "stress_edge_positive",
        "bias_guard_pass",
        "largest_loss_within_limit",
        "profit_concentration_within_limit",
        "operator_time_within_limit",
    }:
        return "KILL", "REJECT_CANDIDATE"
    if "actual_cash_available" in failed_ids:
        return "NEEDS_ACTUAL_CASH", "BUILD_ACTUAL_CASH_LEDGER"
    return "READY_FOR_HUMAN_RISK_REVIEW", "PREPARE_HUMAN_REVIEW"


def build_risk_taker_review(
    *,
    rows_v2: CryptoPerpTournamentRowsV2,
    source_availability: CryptoPerpSourceAvailability,
    bias_guard: CryptoPerpBiasGuard,
    created_at: datetime | str,
    operator_jurisdiction_status: OperatorJurisdictionStatus,
    source_freshness_status: SourceFreshnessStatus,
    venue_terms_checked_at: datetime | str | None = None,
    liquidation_buffer_bps: Decimal | None = None,
    source_refs: Sequence[dict[str, str]] | None = None,
    max_largest_loss_usd: Decimal = _DEFAULT_MAX_LARGEST_LOSS_USD,
    max_profit_concentration: Decimal = _DEFAULT_MAX_PROFIT_CONCENTRATION,
    max_operator_time_minutes: Decimal = _DEFAULT_MAX_OPERATOR_TIME_MINUTES,
    review_id: str | None = None,
    producer_command: str = "crypto-perp-risk-taker-review",
) -> CryptoPerpRiskTakerReview:
    if not rows_v2.rows:
        raise ValueError("rows_v2 must contain rows")
    for value_name, value in {
        "max_largest_loss_usd": max_largest_loss_usd,
        "max_profit_concentration": max_profit_concentration,
        "max_operator_time_minutes": max_operator_time_minutes,
    }.items():
        if value < 0:
            raise ValueError(f"{value_name} must be non-negative")
    if liquidation_buffer_bps is not None and liquidation_buffer_bps < 0:
        raise ValueError("liquidation_buffer_bps must be non-negative")

    created = ensure_utc_aware("created_at", created_at)
    leader = _leader_action(rows_v2.rows)
    no_trade_cost = _sum_cost(rows_v2.rows, "NO_TRADE")
    no_trade_stress = _sum_stress(rows_v2.rows, "NO_TRADE")
    leader_cost = _sum_cost(rows_v2.rows, leader) if leader is not None else None
    leader_stress = _sum_stress(rows_v2.rows, leader) if leader is not None else None
    after_edge = leader_cost - no_trade_cost if leader_cost is not None else None
    stress_edge = leader_stress - no_trade_stress if leader_stress is not None else None
    leader_rows = _rows_for_action(rows_v2.rows, leader) if leader is not None else []
    operator_time = sum((row.operator_time_minutes for row in leader_rows), _ZERO)
    dollars_per_hour = (
        after_edge / (operator_time / Decimal("60"))
        if after_edge is not None and operator_time > 0
        else None
    )
    actual_values = [
        row.actual_cash_result_usd for row in leader_rows if row.actual_cash_result_usd is not None
    ]
    loss_values = [row.stress_cash_estimate_usd for row in leader_rows]
    if actual_values:
        loss_values.extend(actual_values)
    largest_loss = min(loss_values) if loss_values else None
    profit_concentration = (
        _profit_concentration([row.cost_adjusted_cash_estimate_usd for row in leader_rows])
        if leader_rows
        else None
    )
    cost_source_gaps = _cost_source_gap_reasons(source_availability)
    actual_cash_available = _actual_cash_available(
        rows=rows_v2.rows,
        action=leader,
        source_availability=source_availability,
    )
    conditions = [
        _condition(
            "operator_jurisdiction_allowed",
            operator_jurisdiction_status == "allowed",
            operator_jurisdiction_status,
            "allowed",
        ),
        _condition(
            "source_freshness_fresh",
            source_freshness_status == "fresh",
            source_freshness_status,
            "fresh",
        ),
        _condition(
            "source_availability_cost_adjusted",
            not cost_source_gaps,
            ",".join(cost_source_gaps) or "available",
            "cost-adjusted estimate sources available",
        ),
        _condition(
            "liquidation_buffer_present",
            liquidation_buffer_bps is not None,
            liquidation_buffer_bps if liquidation_buffer_bps is not None else "missing",
            "non-null liquidation_buffer_bps",
        ),
        _condition(
            "leader_present", leader is not None, leader or "NONE", "non-null leader_action"
        ),
        _condition(
            "leader_not_no_trade",
            leader is not None and leader != "NO_TRADE",
            leader or "NONE",
            "leader_action other than NO_TRADE",
        ),
        _condition(
            "after_cost_edge_positive",
            after_edge is not None and after_edge > 0,
            after_edge if after_edge is not None else "missing",
            "> 0",
        ),
        _condition(
            "stress_edge_positive",
            stress_edge is not None and stress_edge > 0,
            stress_edge if stress_edge is not None else "missing",
            "> 0",
        ),
        _condition(
            "actual_cash_available",
            actual_cash_available,
            actual_cash_available,
            "leader action rows have actual_cash_result_usd and actual cash source",
        ),
        _condition(
            "bias_guard_pass", bias_guard.guard_status == "PASS", bias_guard.guard_status, "PASS"
        ),
        _condition(
            "largest_loss_within_limit",
            largest_loss is not None and abs(min(largest_loss, _ZERO)) <= max_largest_loss_usd,
            largest_loss if largest_loss is not None else "missing",
            f">= -{max_largest_loss_usd}",
        ),
        _condition(
            "profit_concentration_within_limit",
            profit_concentration is not None and profit_concentration <= max_profit_concentration,
            profit_concentration if profit_concentration is not None else "missing",
            f"<= {max_profit_concentration}",
        ),
        _condition(
            "operator_time_within_limit",
            operator_time <= max_operator_time_minutes,
            operator_time,
            f"<= {max_operator_time_minutes}",
        ),
    ]
    review_status, recommended_action = _status_and_action(conditions=conditions)
    extra_gaps: list[str] = [*cost_source_gaps]
    if operator_jurisdiction_status != "allowed":
        extra_gaps.append("OPERATOR_JURISDICTION_NOT_ALLOWED")
    if source_freshness_status != "fresh":
        extra_gaps.append("SOURCE_FRESHNESS_NOT_FRESH")
    if liquidation_buffer_bps is None:
        extra_gaps.append("LIQUIDATION_BUFFER_BPS_MISSING")
    if leader == "NO_TRADE":
        extra_gaps.append("NO_TRADE_LEADER")
    if after_edge is None or after_edge <= 0:
        extra_gaps.append("AFTER_COST_EDGE_NOT_POSITIVE")
    if stress_edge is None or stress_edge <= 0:
        extra_gaps.append("STRESS_EDGE_NOT_POSITIVE")
    if not actual_cash_available and leader is not None and leader != "NO_TRADE":
        extra_gaps.append("ACTUAL_CASH_RESULT_NOT_AVAILABLE")
    if bias_guard.guard_status != "PASS":
        extra_gaps.append("BIAS_GUARD_BLOCKED")
    if largest_loss is None:
        extra_gaps.append("LARGEST_LOSS_MISSING")
    elif abs(min(largest_loss, _ZERO)) > max_largest_loss_usd:
        extra_gaps.append("LARGEST_LOSS_EXCEEDS_LIMIT")
    if profit_concentration is None:
        extra_gaps.append("PROFIT_CONCENTRATION_MISSING")
    elif profit_concentration > max_profit_concentration:
        extra_gaps.append("PROFIT_CONCENTRATION_EXCEEDS_LIMIT")
    if operator_time > max_operator_time_minutes:
        extra_gaps.append("OPERATOR_TIME_EXCEEDS_LIMIT")

    resolved_review_id = review_id or stable_hash(
        [
            "crypto-perp-risk-taker-review",
            rows_v2.row_set_id,
            source_availability.artifact_id,
            bias_guard.guard_id,
            operator_jurisdiction_status,
            source_freshness_status,
            liquidation_buffer_bps,
        ]
    )
    known_gaps = _known_gap_list(
        rows_v2=rows_v2,
        source_availability=source_availability,
        bias_guard=bias_guard,
        extra=extra_gaps,
    )
    summary = {
        "review_id": resolved_review_id,
        "review_status": review_status,
        "recommended_action": recommended_action,
        "leader_action": leader,
        "after_cost_edge_over_no_trade_usd": after_edge,
        "stress_edge_over_no_trade_usd": stress_edge,
        "actual_cash_available": actual_cash_available,
        "source_gap_count": len(cost_source_gaps),
        "failed_condition_count": sum(1 for condition in conditions if not condition.passed),
        "known_gap_count": len(known_gaps),
        "permits_live_order": False,
    }
    venue_terms_checked = (
        ensure_utc_aware("venue_terms_checked_at", venue_terms_checked_at)
        if venue_terms_checked_at is not None
        else None
    )
    return CryptoPerpRiskTakerReview(
        artifact_id=stable_hash(
            [
                "crypto-perp-risk-taker-review-artifact",
                resolved_review_id,
                serialize_utc_z(created),
            ]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=[dict(ref) for ref in source_refs or []],
        review_id=resolved_review_id,
        row_set_id=rows_v2.row_set_id,
        source_availability_artifact_id=source_availability.artifact_id,
        bias_guard_id=bias_guard.guard_id,
        review_status=review_status,
        recommended_action=recommended_action,
        operator_jurisdiction_status=operator_jurisdiction_status,
        source_freshness_status=source_freshness_status,
        venue_terms_checked_at=venue_terms_checked,
        leader_action=leader,
        after_cost_edge_over_no_trade_usd=after_edge,
        stress_edge_over_no_trade_usd=stress_edge,
        dollars_per_hour=dollars_per_hour,
        largest_loss_usd=largest_loss,
        profit_concentration=profit_concentration,
        liquidation_buffer_bps=liquidation_buffer_bps,
        conditions=conditions,
        known_gaps=known_gaps,
        summary=summary,
    )
