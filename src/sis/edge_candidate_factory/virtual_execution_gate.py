from __future__ import annotations

from datetime import datetime

from sis.edge_candidate_factory._contracts import (
    VIRTUAL_EXECUTION_GATE_REQUIRED_CONDITION_IDS,
    ConditionStatus,
    ExecutionEnvironment,
    VirtualExecutionGateStatus,
)
from sis.edge_candidate_factory.models import (
    ArtifactRef,
    GateCondition,
    ProducerInfo,
    VirtualExecutionGate,
)


def _condition(
    condition_id: str,
    condition_status: ConditionStatus,
    observed: str | int | float | bool | None,
    required: str | int | float | bool | None,
    source_ref: str = "virtual_execution_gate",
) -> GateCondition:
    return GateCondition(
        condition_id=condition_id,
        condition_status=condition_status,
        observed=observed,
        required=required,
        source_ref=source_ref,
    )


def _bool_status(value: bool) -> ConditionStatus:
    return ConditionStatus.PASS if value else ConditionStatus.FAIL


def build_virtual_execution_gate(
    *,
    gate_id: str,
    created_at: datetime,
    candidate_id: str,
    venue_id: str,
    source_refs: list[ArtifactRef] | None = None,
    execution_environment: ExecutionEnvironment = ExecutionEnvironment.FIXTURE,
    source_available: bool = True,
    execution_precheck_passed: bool = True,
    order_preview_ready: bool = True,
    order_accepted: bool = True,
    reject_reason_captured: bool = True,
    client_oid_unique: bool = True,
    partial_fill_handled: bool = True,
    cancel_handled: bool = True,
    reduce_only_close_checked: bool = True,
    flat_reconciliation_passed: bool = True,
    fee_like_fields_captured: bool = True,
    funding_like_fields_captured: bool = True,
    duplicate_order_prevented: bool = True,
) -> VirtualExecutionGate:
    accepted_or_rejected_with_reason = order_accepted or reject_reason_captured
    conditions = [
        _condition("source_available", _bool_status(source_available), source_available, True),
        _condition(
            "execution_precheck_passed",
            _bool_status(execution_precheck_passed),
            execution_precheck_passed,
            True,
        ),
        _condition(
            "order_preview_ready", _bool_status(order_preview_ready), order_preview_ready, True
        ),
        _condition(
            "order_accepted_or_rejected_with_reason",
            _bool_status(accepted_or_rejected_with_reason),
            "accepted" if order_accepted else reject_reason_captured,
            "accepted_or_rejected_with_reason",
        ),
        _condition("client_oid_unique", _bool_status(client_oid_unique), client_oid_unique, True),
        _condition(
            "partial_fill_handled",
            _bool_status(partial_fill_handled),
            partial_fill_handled,
            True,
        ),
        _condition("cancel_handled", _bool_status(cancel_handled), cancel_handled, True),
        _condition(
            "reduce_only_close_checked",
            _bool_status(reduce_only_close_checked),
            reduce_only_close_checked,
            True,
        ),
        _condition(
            "flat_reconciliation_passed",
            _bool_status(flat_reconciliation_passed),
            flat_reconciliation_passed,
            True,
        ),
        _condition(
            "fee_like_fields_captured",
            _bool_status(fee_like_fields_captured),
            fee_like_fields_captured,
            True,
        ),
        _condition(
            "funding_like_fields_captured",
            _bool_status(funding_like_fields_captured),
            funding_like_fields_captured,
            True,
        ),
        _condition(
            "duplicate_order_prevented",
            _bool_status(duplicate_order_prevented),
            duplicate_order_prevented,
            True,
        ),
        _condition("production_exchange_write_not_used", ConditionStatus.PASS, False, False),
    ]
    missing_conditions = VIRTUAL_EXECUTION_GATE_REQUIRED_CONDITION_IDS - {
        condition.condition_id for condition in conditions
    }
    if missing_conditions:
        raise ValueError(f"missing virtual execution conditions: {sorted(missing_conditions)}")

    failed_condition_ids = {
        condition.condition_id
        for condition in conditions
        if condition.condition_status is ConditionStatus.FAIL
    }
    lifecycle_condition_ids = {
        "order_preview_ready",
        "order_accepted_or_rejected_with_reason",
        "client_oid_unique",
        "partial_fill_handled",
        "cancel_handled",
        "reduce_only_close_checked",
        "fee_like_fields_captured",
        "funding_like_fields_captured",
        "duplicate_order_prevented",
    }
    if not source_available:
        gate_status = VirtualExecutionGateStatus.VIRTUAL_BLOCKED_SOURCE
        recommended_action = "collect_virtual_execution_source_before_actual_cash"
    elif not execution_precheck_passed:
        gate_status = VirtualExecutionGateStatus.VIRTUAL_BLOCKED_EXECUTION_PRECHECK
        recommended_action = "fix_execution_precheck_before_virtual_gate"
    elif failed_condition_ids & lifecycle_condition_ids:
        gate_status = VirtualExecutionGateStatus.VIRTUAL_FAILED_ORDER_LIFECYCLE
        recommended_action = "fix_virtual_order_lifecycle_before_actual_cash"
    elif "flat_reconciliation_passed" in failed_condition_ids:
        gate_status = VirtualExecutionGateStatus.VIRTUAL_FAILED_RECONCILIATION
        recommended_action = "fix_virtual_reconciliation_before_actual_cash"
    else:
        gate_status = VirtualExecutionGateStatus.VIRTUAL_PASSED_EXECUTION_LIFECYCLE
        recommended_action = "manual_review_virtual_lifecycle_before_actual_cash"

    known_gaps = ["virtual lifecycle is not actual cash evidence"]
    if execution_environment is ExecutionEnvironment.FIXTURE:
        known_gaps.append("fixture mode does not contact exchange demo or testnet")
    if gate_status is not VirtualExecutionGateStatus.VIRTUAL_PASSED_EXECUTION_LIFECYCLE:
        known_gaps.append("virtual execution gate did not pass")

    return VirtualExecutionGate(
        gate_id=gate_id,
        created_at=created_at,
        producer=ProducerInfo(command="edge-candidate-virtual-execution-gate"),
        candidate_id=candidate_id,
        execution_environment=execution_environment,
        venue_id=venue_id,
        source_refs=source_refs or [],
        order_lifecycle_summary={
            "fixture_mode": execution_environment is ExecutionEnvironment.FIXTURE,
            "orders_submitted": 1 if order_preview_ready else 0,
            "order_accepted": order_accepted,
            "order_rejected": not order_accepted,
            "reject_reason_captured": reject_reason_captured,
            "client_oid_unique": client_oid_unique,
            "partial_fill_handled": partial_fill_handled,
            "cancel_handled": cancel_handled,
            "reduce_only_close_checked": reduce_only_close_checked,
            "duplicate_order_prevented": duplicate_order_prevented,
        },
        fill_ledger_summary={
            "fills_observed": 1 if partial_fill_handled else 0,
            "partial_fill_handled": partial_fill_handled,
            "fee_like_fields_captured": fee_like_fields_captured,
            "funding_like_fields_captured": funding_like_fields_captured,
            "cash_metric_basis": "virtual_exchange",
        },
        reconciliation_summary={
            "flat_reconciliation_status": "PASS" if flat_reconciliation_passed else "FAIL",
            "flat": flat_reconciliation_passed,
            "actual_cash": False,
        },
        gate_status=gate_status,
        recommended_action=recommended_action,
        actual_cash=False,
        cash_metric_basis="virtual_exchange",
        exchange_write_used=False,
        production_exchange_write_used=False,
        permits_live_order=False,
        conditions=conditions,
        known_gaps=list(dict.fromkeys(known_gaps)),
    )
