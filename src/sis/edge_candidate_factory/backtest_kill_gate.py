from __future__ import annotations

from datetime import datetime

from sis.edge_candidate_factory._contracts import (
    BACKTEST_KILL_GATE_REQUIRED_CONDITION_IDS,
    ConditionStatus,
)
from sis.edge_candidate_factory.backtest_inputs import BacktestMetricInputs
from sis.edge_candidate_factory.generator import ZERO_HASH
from sis.edge_candidate_factory.models import (
    ArtifactRef,
    BacktestKillGate,
    BacktestKillGateStatus,
    BacktestMetrics,
    GateCondition,
    ProducerInfo,
    TrialMultiplicityAccount,
)


RARE_EVENT_FAMILIES = {"cross_market_basis_dislocation"}
MEDIUM_EVENT_FAMILIES = {
    "liquidation_exhaustion_reversal",
    "liquidation_cascade_continuation",
    "funding_pressure_reversion",
}
COMMON_EVENT_THRESHOLD = 100
MEDIUM_EVENT_THRESHOLD = 30
RARE_EVENT_THRESHOLD = 10
MAX_LARGEST_LOSS_USD = -1_000.0
MAX_PROFIT_CONCENTRATION = 0.60


def family_event_threshold(family_id: str) -> int:
    if family_id in RARE_EVENT_FAMILIES:
        return RARE_EVENT_THRESHOLD
    if family_id in MEDIUM_EVENT_FAMILIES:
        return MEDIUM_EVENT_THRESHOLD
    return COMMON_EVENT_THRESHOLD


def _fallback_multiplicity_ref() -> ArtifactRef:
    return ArtifactRef(
        ref_id="multiplicity-account",
        schema_version="trial_multiplicity_account.v1",
        path="data/edge_candidate_factory/trial_multiplicity_account.json",
        sha256=ZERO_HASH,
    )


def _condition(
    condition_id: str,
    condition_status: ConditionStatus,
    observed: str | int | float | bool | None,
    required: str | int | float | bool | None,
    source_ref: str = "backtest_kill_gate",
) -> GateCondition:
    return GateCondition(
        condition_id=condition_id,
        condition_status=condition_status,
        observed=observed,
        required=required,
        source_ref=source_ref,
    )


def _min_count_status(value: int | None, threshold: int) -> ConditionStatus:
    if value is None:
        return ConditionStatus.NOT_ESTIMABLE
    return ConditionStatus.PASS if value >= threshold else ConditionStatus.FAIL


def _positive_status(value: float | None) -> ConditionStatus:
    if value is None:
        return ConditionStatus.NOT_ESTIMABLE
    return ConditionStatus.PASS if value > 0 else ConditionStatus.FAIL


def _largest_loss_status(value: float | None) -> ConditionStatus:
    if value is None:
        return ConditionStatus.NOT_ESTIMABLE
    return ConditionStatus.PASS if value >= MAX_LARGEST_LOSS_USD else ConditionStatus.FAIL


def _profit_concentration_status(value: float | None) -> ConditionStatus:
    if value is None:
        return ConditionStatus.NOT_ESTIMABLE
    return ConditionStatus.PASS if value <= MAX_PROFIT_CONCENTRATION else ConditionStatus.FAIL


def _zero_count_status(value: int) -> ConditionStatus:
    return ConditionStatus.PASS if value == 0 else ConditionStatus.FAIL


def build_backtest_kill_gate(
    *,
    gate_id: str,
    created_at: datetime,
    candidate_id: str,
    family_id: str,
    candidate_source_refs: list[ArtifactRef],
    multiplicity_account: TrialMultiplicityAccount | None,
    metrics: BacktestMetricInputs,
    source_available: bool,
    bridge_technical_ready: bool,
    execution_precheck_passed: bool,
    multiplicity_account_ref: ArtifactRef | None = None,
    backtest_refs: list[ArtifactRef] | None = None,
) -> BacktestKillGate:
    threshold = family_event_threshold(family_id)
    source_status = ConditionStatus.PASS if source_available else ConditionStatus.FAIL
    bridge_status = ConditionStatus.PASS if bridge_technical_ready else ConditionStatus.FAIL
    execution_status = ConditionStatus.PASS if execution_precheck_passed else ConditionStatus.FAIL
    multiplicity_status = (
        ConditionStatus.PASS if multiplicity_account is not None else ConditionStatus.NOT_ESTIMABLE
    )
    metric_status = (
        ConditionStatus.NOT_ESTIMABLE
        if metrics.metric_not_estimable_reasons
        else ConditionStatus.PASS
    )
    conditions = [
        _condition("source_available", source_status, source_available, True),
        _condition("bridge_technical_ready", bridge_status, bridge_technical_ready, True),
        _condition(
            "candidate_scoped_backtest_exists",
            metric_status,
            not metrics.metric_not_estimable_reasons,
            True,
        ),
        _condition(
            "no_trade_comparison_available",
            ConditionStatus.PASS
            if metrics.after_cost_edge_over_no_trade_usd is not None
            else ConditionStatus.NOT_ESTIMABLE,
            metrics.after_cost_edge_over_no_trade_usd is not None,
            True,
        ),
        _condition(
            "event_count_meets_family_threshold",
            _min_count_status(metrics.event_count, threshold),
            metrics.event_count,
            threshold,
        ),
        _condition(
            "closed_trade_count_meets_threshold",
            _min_count_status(metrics.closed_trade_count, threshold),
            metrics.closed_trade_count,
            threshold,
        ),
        _condition(
            "after_cost_edge_positive",
            _positive_status(metrics.after_cost_edge_over_no_trade_usd),
            metrics.after_cost_edge_over_no_trade_usd,
            ">0",
        ),
        _condition(
            "stress_edge_positive",
            _positive_status(metrics.stress_edge_over_no_trade_usd),
            metrics.stress_edge_over_no_trade_usd,
            ">0",
        ),
        _condition(
            "largest_loss_within_limit",
            _largest_loss_status(metrics.largest_loss_usd),
            metrics.largest_loss_usd,
            f">={MAX_LARGEST_LOSS_USD}",
        ),
        _condition(
            "profit_concentration_within_limit",
            _profit_concentration_status(metrics.profit_concentration),
            metrics.profit_concentration,
            f"<={MAX_PROFIT_CONCENTRATION}",
        ),
        _condition(
            "multiplicity_account_available",
            multiplicity_status,
            multiplicity_account is not None,
            True,
        ),
        _condition(
            "unexecutable_reason_count_zero",
            _zero_count_status(metrics.unexecutable_reason_count),
            metrics.unexecutable_reason_count,
            0,
        ),
        _condition("sealed_test_not_used_for_selection", ConditionStatus.PASS, False, False),
        _condition("execution_precheck_passed", execution_status, execution_precheck_passed, True),
    ]
    condition_ids = {condition.condition_id for condition in conditions}
    missing_conditions = BACKTEST_KILL_GATE_REQUIRED_CONDITION_IDS - condition_ids
    if missing_conditions:
        raise ValueError(f"missing backtest kill gate conditions: {sorted(missing_conditions)}")

    fail_condition_ids = {
        condition.condition_id
        for condition in conditions
        if condition.condition_status is ConditionStatus.FAIL
    }
    not_estimable = [
        condition.condition_id
        for condition in conditions
        if condition.condition_status is ConditionStatus.NOT_ESTIMABLE
    ]
    hard_kill_conditions = {
        "after_cost_edge_positive",
        "stress_edge_positive",
        "largest_loss_within_limit",
        "profit_concentration_within_limit",
    }
    technical_blocker_conditions = {
        "bridge_technical_ready",
        "execution_precheck_passed",
        "unexecutable_reason_count_zero",
    }
    if not source_available or "multiplicity_account_available" in not_estimable:
        gate_status = BacktestKillGateStatus.INCONCLUSIVE_DATA
        recommended_action = "collect_missing_source_or_multiplicity_evidence"
    elif set(not_estimable):
        gate_status = BacktestKillGateStatus.INCONCLUSIVE_DATA
        recommended_action = "collect_missing_backtest_metrics"
    elif fail_condition_ids & technical_blocker_conditions:
        gate_status = BacktestKillGateStatus.INCONCLUSIVE_DATA
        recommended_action = "resolve_backtest_bridge_or_execution_precheck_blockers"
    elif fail_condition_ids & hard_kill_conditions:
        gate_status = BacktestKillGateStatus.KILL
        recommended_action = "kill_candidate"
    else:
        gate_status = BacktestKillGateStatus.RESEARCH_ONLY
        recommended_action = "manual_review_before_virtual_gate"

    source_gap_count = metrics.source_gap_count + (0 if source_available else 1)
    known_gaps = list(metrics.metric_not_estimable_reasons)
    if not bridge_technical_ready:
        known_gaps.append("bridge technical readiness failed")
    if not execution_precheck_passed:
        known_gaps.append("execution precheck failed")
    if metrics.unexecutable_reason_count:
        known_gaps.append("unexecutable reasons present")
    if gate_status is BacktestKillGateStatus.RESEARCH_ONLY:
        known_gaps.append(
            "backtest pass does not imply virtual, paper, live, or actual cash readiness"
        )
    return BacktestKillGate(
        gate_id=gate_id,
        created_at=created_at,
        producer=ProducerInfo(command="edge-candidate-backtest-kill-gate"),
        candidate_id=candidate_id,
        candidate_source_refs=candidate_source_refs,
        bridge_refs=[],
        multiplicity_account_ref=multiplicity_account_ref or _fallback_multiplicity_ref(),
        backtest_refs=backtest_refs or [],
        gate_status=gate_status,
        recommended_action=recommended_action,
        metric_extraction_status=metric_status,
        metric_source_refs=backtest_refs or [],
        metric_not_estimable_reasons=list(metrics.metric_not_estimable_reasons),
        conditions=conditions,
        metrics=BacktestMetrics(
            event_count=metrics.event_count,
            closed_trade_count=metrics.closed_trade_count,
            after_cost_edge_over_no_trade_usd=metrics.after_cost_edge_over_no_trade_usd,
            stress_edge_over_no_trade_usd=metrics.stress_edge_over_no_trade_usd,
            largest_loss_usd=metrics.largest_loss_usd,
            profit_concentration=metrics.profit_concentration,
            source_gap_count=source_gap_count,
            unexecutable_reason_count=metrics.unexecutable_reason_count,
            validation_peek_count=metrics.validation_peek_count,
            candidate_cluster_count=metrics.candidate_cluster_count,
            effective_trial_count=metrics.effective_trial_count,
        ),
        known_gaps=list(dict.fromkeys(known_gaps)),
    )
