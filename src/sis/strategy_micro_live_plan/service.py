from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.execution.live_order_policy import MicroLivePolicy, load_micro_live_policy
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_micro_live_plan.models import (
    MicroLiveMonitoringPlan,
    MicroLivePlanStatus,
    MicroLivePolicySnapshot,
    MicroLiveRiskLimits,
    MicroLiveSourceArtifact,
    StrategyMicroLivePlan,
)
from sis.strategy_micro_live_plan.rendering import render_micro_live_plan_markdown
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_stage.models import (
    StageCondition,
    StageDecisionStatus,
    StageName,
    StageProducer,
)


@dataclass(frozen=True)
class StrategyMicroLivePlanResult:
    plan: StrategyMicroLivePlan
    plan_path: Path
    report_path: Path


class StrategyMicroLivePlanError(ValueError):
    pass


class StrategyMicroLivePlanOutputExistsError(StrategyMicroLivePlanError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(artifact_key: str, path: Path) -> MicroLiveSourceArtifact:
    return MicroLiveSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _condition(
    condition_id: str,
    passed: bool,
    observed: Any,
    required: Any,
    severity: Literal["error", "warning"] = "error",
) -> StageCondition:
    return StageCondition(
        condition_id=condition_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
        severity=severity,
    )


def _policy_snapshot(policy: MicroLivePolicy, policy_path: Path | None) -> MicroLivePolicySnapshot:
    return MicroLivePolicySnapshot(
        policy_path=repo_relative_path(policy_path) if policy_path is not None else None,
        policy_hash=sha256_file(policy_path)
        if policy_path is not None and policy_path.exists()
        else None,
        enabled=policy.enabled,
        venue=policy.venue,
        max_notional_usd=policy.max_notional_usd,
        max_daily_loss_usd=policy.max_daily_loss_usd,
        max_open_positions=policy.max_open_positions,
        max_leverage=policy.max_leverage,
        allowed_symbols=list(policy.allowed_symbols),
        schedule_cancel_deadline_seconds_after_now=(
            policy.schedule_cancel_deadline_seconds_after_now
        ),
        close_require_reduce_only=policy.close_require_reduce_only,
    )


def _status_from_conditions(
    *,
    boundary_violations: list[str],
    stage_ok: bool,
    drift_ok: bool,
    human_approval_present: bool,
    risk_ok: bool,
) -> MicroLivePlanStatus:
    if boundary_violations:
        return MicroLivePlanStatus.BLOCKED_BOUNDARY_VIOLATION
    if not stage_ok:
        return MicroLivePlanStatus.NEEDS_STAGE_DECISION
    if not drift_ok:
        return MicroLivePlanStatus.NEEDS_DRIFT_REVIEW
    if not human_approval_present:
        return MicroLivePlanStatus.NEEDS_HUMAN_APPROVAL
    if not risk_ok:
        return MicroLivePlanStatus.NEEDS_RISK_LIMITS
    return MicroLivePlanStatus.READY_FOR_HUMAN_MICRO_LIVE_REVIEW


def build_strategy_micro_live_plan(
    *,
    strategy_id: str,
    stage_decision_path: Path,
    drift_review_path: Path,
    risk_limits: MicroLiveRiskLimits,
    monitoring_plan: MicroLiveMonitoringPlan,
    out_dir: Path,
    plan_id: str | None = None,
    human_approval_path: Path | None = None,
    micro_live_policy_path: Path | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyMicroLivePlanResult:
    if not stage_decision_path.exists():
        raise FileNotFoundError(f"stage decision missing: {stage_decision_path}")
    if not drift_review_path.exists():
        raise FileNotFoundError(f"drift review missing: {drift_review_path}")
    if human_approval_path is not None and not human_approval_path.exists():
        raise FileNotFoundError(f"human approval missing: {human_approval_path}")

    stage_payload = read_json_object(stage_decision_path)
    drift_payload = read_json_object(drift_review_path)
    approval_payload = (
        read_json_object(human_approval_path) if human_approval_path is not None else None
    )
    boundary_violations = [
        f"stage_decision:{path}" for path in boundary_true_paths(stage_payload)
    ] + [f"drift_review:{path}" for path in boundary_true_paths(drift_payload)]
    if approval_payload is not None:
        boundary_violations.extend(
            f"human_approval:{path}" for path in boundary_true_paths(approval_payload)
        )

    stage_status = stage_payload.get("decision")
    selected_stage = stage_payload.get("selected_stage")
    stage_ok = (
        stage_status == StageDecisionStatus.READY_FOR_MICRO_LIVE_PLAN.value
        and selected_stage == StageName.MICRO_LIVE_PLAN.value
    )
    drift_status = drift_payload.get("review_status")
    drift_action = drift_payload.get("recommended_action")
    drift_ok = drift_status == "READY_FOR_HUMAN_DRIFT_REVIEW" and drift_action not in {
        "REVISE_STRATEGY",
        "REPAIR_ARTIFACTS",
    }
    human_approval_present = approval_payload is not None

    policy_snapshot: MicroLivePolicySnapshot | None = None
    policy_conditions: list[StageCondition] = []
    risk_ok = True
    if micro_live_policy_path is not None:
        try:
            policy = load_micro_live_policy(micro_live_policy_path)
            policy_snapshot = _policy_snapshot(policy, micro_live_policy_path)
            policy_checks = [
                (
                    "max_order_notional_within_existing_policy",
                    risk_limits.max_order_notional_usd <= policy.max_notional_usd,
                    risk_limits.max_order_notional_usd,
                    f"<= {policy.max_notional_usd}",
                ),
                (
                    "max_daily_loss_within_existing_policy",
                    risk_limits.max_daily_loss_usd <= policy.max_daily_loss_usd,
                    risk_limits.max_daily_loss_usd,
                    f"<= {policy.max_daily_loss_usd}",
                ),
                (
                    "max_open_positions_within_existing_policy",
                    risk_limits.max_open_positions <= policy.max_open_positions,
                    risk_limits.max_open_positions,
                    f"<= {policy.max_open_positions}",
                ),
                (
                    "allowed_symbols_within_existing_policy",
                    set(risk_limits.allowed_symbols).issubset(set(policy.allowed_symbols)),
                    ",".join(risk_limits.allowed_symbols),
                    ",".join(policy.allowed_symbols),
                ),
            ]
            for condition_id, passed, observed, required in policy_checks:
                condition = _condition(condition_id, passed, observed, required)
                policy_conditions.append(condition)
                risk_ok = risk_ok and passed
        except (OSError, ValueError, ValidationError) as exc:
            raise StrategyMicroLivePlanError(f"invalid micro live policy: {exc}") from exc

    passed_conditions = [
        _condition(
            "stage_decision_ready_for_micro_live_plan",
            stage_ok,
            f"{selected_stage}:{stage_status}",
            f"{StageName.MICRO_LIVE_PLAN.value}:{StageDecisionStatus.READY_FOR_MICRO_LIVE_PLAN.value}",
        ),
        _condition(
            "drift_review_ready_without_repair_or_revision",
            drift_ok,
            f"{drift_status}:{drift_action}",
            "READY_FOR_HUMAN_DRIFT_REVIEW and not REVISE_STRATEGY/REPAIR_ARTIFACTS",
        ),
        _condition(
            "human_micro_live_approval_present",
            human_approval_present,
            human_approval_present,
            True,
        ),
        _condition("risk_limits_complete", True, "complete", "complete"),
        _condition("monitoring_plan_complete", True, "complete", "complete"),
        *policy_conditions,
    ]
    failed_conditions = [condition for condition in passed_conditions if not condition.passed]
    passed_conditions = [condition for condition in passed_conditions if condition.passed]
    warning_conditions = (
        [
            _condition(
                "micro_live_policy_disabled",
                False,
                False,
                "true only for actual execution",
                severity="warning",
            )
        ]
        if policy_snapshot is not None and not policy_snapshot.enabled
        else []
    )
    for violation in boundary_violations:
        failed_conditions.append(
            _condition("boundary_violation", False, violation, "no true boundary flags")
        )

    plan = StrategyMicroLivePlan(
        plan_id=plan_id or f"{strategy_id}-micro-live-plan",
        strategy_id=strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-micro-live-plan"),
        plan_status=_status_from_conditions(
            boundary_violations=boundary_violations,
            stage_ok=stage_ok,
            drift_ok=drift_ok,
            human_approval_present=human_approval_present,
            risk_ok=risk_ok,
        ),
        stage_decision_status=stage_status if isinstance(stage_status, str) else None,
        drift_review_status=drift_status if isinstance(drift_status, str) else None,
        drift_recommended_action=drift_action if isinstance(drift_action, str) else None,
        human_approval_present=human_approval_present,
        source_artifacts=[
            _source_artifact("stage_decision", stage_decision_path),
            _source_artifact("drift_review", drift_review_path),
            *(
                [_source_artifact("human_approval", human_approval_path)]
                if human_approval_path is not None
                else []
            ),
            *(
                [_source_artifact("micro_live_policy", micro_live_policy_path)]
                if micro_live_policy_path is not None
                else []
            ),
        ],
        risk_limits=risk_limits,
        monitoring_plan=monitoring_plan,
        micro_live_policy_snapshot=policy_snapshot,
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=warning_conditions,
    )

    plan_dir = out_dir / strategy_id
    plan_path = plan_dir / "strategy_micro_live_plan.json"
    report_path = plan_dir / "strategy_micro_live_plan.md"
    if not replace_existing and (plan_path.exists() or report_path.exists()):
        raise StrategyMicroLivePlanOutputExistsError(
            f"output already exists: {repo_relative_path(plan_dir)}"
        )
    write_json_artifact(plan_path, plan.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_micro_live_plan_markdown(plan))
    return StrategyMicroLivePlanResult(plan=plan, plan_path=plan_path, report_path=report_path)
