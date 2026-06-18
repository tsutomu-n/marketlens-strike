from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_micro_live_plan.models import MicroLiveMonitoringPlan
from sis.strategy_next_scale_plan.models import (
    NextScaleGuardPolicy,
    NextScalePlanSourceArtifact,
    NextScalePlanStatus,
    NextScaleRiskLimits,
    StrategyNextScalePlan,
)
from sis.strategy_next_scale_plan.rendering import render_next_scale_plan_markdown
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_stage.models import StageCondition, StageProducer


@dataclass(frozen=True)
class StrategyNextScalePlanResult:
    plan: StrategyNextScalePlan
    plan_path: Path
    report_path: Path


class StrategyNextScalePlanError(ValueError):
    pass


class StrategyNextScalePlanOutputExistsError(StrategyNextScalePlanError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _condition(condition_id: str, passed: bool, observed: Any, required: Any) -> StageCondition:
    return StageCondition(
        condition_id=condition_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
        severity="error",
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _source_artifact(artifact_key: str, path: Path) -> NextScalePlanSourceArtifact:
    return NextScalePlanSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _previous_risk_limits(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = read_json_object(path)
    if payload.get("schema_version") != "strategy_micro_live_plan.v1":
        raise StrategyNextScalePlanError(
            "micro live plan schema_version must be strategy_micro_live_plan.v1"
        )
    return _as_dict(payload.get("risk_limits"))


def _within_multiplier(
    *,
    next_value: float,
    previous_value: Any,
    multiplier: float,
    condition_id: str,
) -> StageCondition:
    if not isinstance(previous_value, int | float):
        return _condition(condition_id, False, "missing", f"previous value * {multiplier}")
    maximum = float(previous_value) * multiplier
    return _condition(condition_id, next_value <= maximum, next_value, f"<= {maximum}")


def _status_for(
    *,
    boundary_violations: list[str],
    failed_conditions: list[StageCondition],
    scale_status: str | None,
) -> NextScalePlanStatus:
    if boundary_violations:
        return NextScalePlanStatus.BLOCKED_BOUNDARY_VIOLATION
    failed_ids = {condition.condition_id for condition in failed_conditions}
    if "scale_decision_ready" in failed_ids or scale_status != "READY_FOR_HUMAN_SCALE_REVIEW":
        return NextScalePlanStatus.NEEDS_SCALE_DECISION
    if failed_conditions:
        return NextScalePlanStatus.NEEDS_RISK_REPAIR
    return NextScalePlanStatus.READY_FOR_HUMAN_NEXT_SCALE_REVIEW


def build_strategy_next_scale_plan(
    *,
    strategy_id: str,
    scale_decision_path: Path,
    out_dir: Path,
    risk_limits: NextScaleRiskLimits,
    monitoring_plan: MicroLiveMonitoringPlan,
    micro_live_plan_path: Path | None = None,
    guard_policy: NextScaleGuardPolicy | None = None,
    plan_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyNextScalePlanResult:
    if not scale_decision_path.exists():
        raise FileNotFoundError(f"scale decision missing: {scale_decision_path}")
    if micro_live_plan_path is not None and not micro_live_plan_path.exists():
        raise FileNotFoundError(f"micro live plan missing: {micro_live_plan_path}")
    selected_guard = guard_policy or NextScaleGuardPolicy()
    scale_payload = read_json_object(scale_decision_path)
    if scale_payload.get("schema_version") != "strategy_scale_decision.v1":
        raise StrategyNextScalePlanError(
            "scale decision schema_version must be strategy_scale_decision.v1"
        )
    previous_limits = _previous_risk_limits(micro_live_plan_path)
    boundary_violations = boundary_true_paths(scale_payload)
    scale_status = scale_payload.get("decision_status")
    scale_action = scale_payload.get("recommended_action")
    conditions = [
        _condition(
            "scale_decision_ready",
            (not selected_guard.require_scale_decision_ready)
            or scale_status == "READY_FOR_HUMAN_SCALE_REVIEW",
            scale_status,
            "READY_FOR_HUMAN_SCALE_REVIEW",
        ),
        _condition(
            "scale_action_prepare_next_plan",
            scale_action == "PREPARE_NEXT_SCALE_PLAN",
            scale_action,
            "PREPARE_NEXT_SCALE_PLAN",
        ),
        _condition(
            "previous_micro_live_plan_present",
            (not selected_guard.require_previous_micro_live_plan)
            or micro_live_plan_path is not None,
            micro_live_plan_path is not None,
            "true unless require_previous_micro_live_plan=false",
        ),
        _within_multiplier(
            next_value=risk_limits.next_max_order_notional_usd,
            previous_value=previous_limits.get("max_order_notional_usd"),
            multiplier=selected_guard.max_scale_multiplier,
            condition_id="max_order_notional_multiplier",
        ),
        _within_multiplier(
            next_value=risk_limits.next_max_position_notional_usd,
            previous_value=previous_limits.get("max_position_notional_usd"),
            multiplier=selected_guard.max_scale_multiplier,
            condition_id="max_position_notional_multiplier",
        ),
        _within_multiplier(
            next_value=risk_limits.next_max_daily_loss_usd,
            previous_value=previous_limits.get("max_daily_loss_usd"),
            multiplier=selected_guard.max_scale_multiplier,
            condition_id="max_daily_loss_multiplier",
        ),
    ]
    failed_conditions = [condition for condition in conditions if not condition.passed]
    passed_conditions = [condition for condition in conditions if condition.passed]
    for violation in boundary_violations:
        failed_conditions.append(
            _condition("boundary_violation", False, violation, "no true boundary flags")
        )
    status = _status_for(
        boundary_violations=boundary_violations,
        failed_conditions=failed_conditions,
        scale_status=scale_status if isinstance(scale_status, str) else None,
    )
    source_artifacts = [
        _source_artifact("scale_decision", scale_decision_path),
        *(
            [_source_artifact("micro_live_plan", micro_live_plan_path)]
            if micro_live_plan_path is not None
            else []
        ),
    ]
    plan = StrategyNextScalePlan(
        plan_id=plan_id or f"{strategy_id}-next-scale-plan",
        strategy_id=strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-next-scale-plan"),
        plan_status=status,
        scale_decision_status=scale_status if isinstance(scale_status, str) else None,
        scale_recommended_action=scale_action if isinstance(scale_action, str) else None,
        guard_policy=selected_guard,
        risk_limits=risk_limits,
        monitoring_plan=monitoring_plan,
        source_artifacts=source_artifacts,
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=[],
    )
    plan_dir = out_dir / strategy_id
    plan_path = plan_dir / "strategy_next_scale_plan.json"
    report_path = plan_dir / "strategy_next_scale_plan.md"
    if not replace_existing and (plan_path.exists() or report_path.exists()):
        raise StrategyNextScalePlanOutputExistsError(
            f"output already exists: {repo_relative_path(plan_dir)}"
        )
    write_json_artifact(plan_path, plan.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_next_scale_plan_markdown(plan))
    return StrategyNextScalePlanResult(plan=plan, plan_path=plan_path, report_path=report_path)
