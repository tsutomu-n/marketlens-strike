from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_scale_decision.models import (
    ScaleDecisionPolicy,
    ScaleDecisionSourceArtifact,
    ScaleDecisionStatus,
    ScaleRecommendedAction,
    StrategyScaleDecision,
)
from sis.strategy_scale_decision.rendering import render_scale_decision_markdown
from sis.strategy_stage.models import StageCondition, StageProducer


@dataclass(frozen=True)
class StrategyScaleDecisionResult:
    decision: StrategyScaleDecision
    decision_path: Path
    report_path: Path


class StrategyScaleDecisionError(ValueError):
    pass


class StrategyScaleDecisionOutputExistsError(StrategyScaleDecisionError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(artifact_key: str, path: Path) -> ScaleDecisionSourceArtifact:
    return ScaleDecisionSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


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


def _status_and_action(
    *, boundary_violations: list[str], failed: list[StageCondition], payload: dict[str, Any]
) -> tuple[ScaleDecisionStatus, ScaleRecommendedAction]:
    if boundary_violations:
        return (
            ScaleDecisionStatus.BLOCKED_BOUNDARY_VIOLATION,
            ScaleRecommendedAction.REPAIR_ARTIFACTS,
        )
    ingest_status = payload.get("ingest_status")
    if ingest_status != "LIVE_OBSERVATION_INGESTED":
        if ingest_status == "BLOCKED_CANARY":
            return (
                ScaleDecisionStatus.REVISE_OR_RETIRE,
                ScaleRecommendedAction.HOLD_AT_MICRO_LIVE,
            )
        return (
            ScaleDecisionStatus.NEEDS_LIVE_OBSERVATION,
            ScaleRecommendedAction.REPAIR_ARTIFACTS,
        )
    failed_ids = {condition.condition_id for condition in failed}
    if failed_ids & {"no_rejection_observed", "no_max_loss_breach"}:
        return (
            ScaleDecisionStatus.REVISE_OR_RETIRE,
            ScaleRecommendedAction.REVISE_STRATEGY,
        )
    if failed:
        return (
            ScaleDecisionStatus.NEEDS_REPAIR,
            ScaleRecommendedAction.HOLD_AT_MICRO_LIVE,
        )
    return (
        ScaleDecisionStatus.READY_FOR_HUMAN_SCALE_REVIEW,
        ScaleRecommendedAction.PREPARE_NEXT_SCALE_PLAN,
    )


def build_strategy_scale_decision(
    *,
    strategy_id: str,
    live_observation_path: Path,
    out_dir: Path,
    decision_id: str | None = None,
    micro_live_plan_path: Path | None = None,
    policy: ScaleDecisionPolicy | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyScaleDecisionResult:
    if not live_observation_path.exists():
        raise FileNotFoundError(f"live observation missing: {live_observation_path}")
    if micro_live_plan_path is not None and not micro_live_plan_path.exists():
        raise FileNotFoundError(f"micro live plan missing: {micro_live_plan_path}")

    selected_policy = policy or ScaleDecisionPolicy()
    payload = read_json_object(live_observation_path)
    if payload.get("schema_version") != "strategy_live_observation_manifest.v1":
        raise StrategyScaleDecisionError(
            "live observation schema_version must be strategy_live_observation_manifest.v1"
        )
    summary = _as_dict(payload.get("summary"))
    boundary_violations = boundary_true_paths(payload)
    ingest_status = payload.get("ingest_status")
    blocked_reasons = summary.get("blocked_reasons", [])
    if not isinstance(blocked_reasons, list):
        blocked_reasons = []
    actual_fill = summary.get("actual_fill_observed") is True
    rejection = summary.get("rejection_observed") is True
    cancel_or_close = (
        summary.get("cancel_observed") is True or summary.get("close_submitted") is True
    )
    max_loss_breach = summary.get("max_loss_breach_observed") is True

    conditions = [
        _condition(
            "live_observation_ingested",
            ingest_status == "LIVE_OBSERVATION_INGESTED",
            ingest_status,
            "LIVE_OBSERVATION_INGESTED",
        ),
        _condition(
            "blocked_reasons_empty",
            selected_policy.allow_blocked_canary or not blocked_reasons,
            ",".join(str(item) for item in blocked_reasons) or "none",
            "none unless allow_blocked_canary",
        ),
        _condition(
            "actual_fill_requirement",
            (not selected_policy.require_actual_fill) or actual_fill,
            actual_fill,
            f"true when require_actual_fill={selected_policy.require_actual_fill}",
        ),
        _condition(
            "cancel_or_close_safety_observed",
            (not selected_policy.require_cancel_or_close_observed) or cancel_or_close,
            cancel_or_close,
            f"true when require_cancel_or_close_observed={selected_policy.require_cancel_or_close_observed}",
        ),
        _condition(
            "no_rejection_observed",
            selected_policy.allow_rejection or not rejection,
            rejection,
            "false unless allow_rejection",
        ),
        _condition(
            "no_max_loss_breach",
            selected_policy.allow_max_loss_breach or not max_loss_breach,
            max_loss_breach,
            "false unless allow_max_loss_breach",
        ),
    ]
    failed_conditions = [condition for condition in conditions if not condition.passed]
    passed_conditions = [condition for condition in conditions if condition.passed]
    for violation in boundary_violations:
        failed_conditions.append(
            _condition("boundary_violation", False, violation, "no true boundary flags")
        )
    status, action = _status_and_action(
        boundary_violations=boundary_violations,
        failed=failed_conditions,
        payload=payload,
    )
    decision = StrategyScaleDecision(
        decision_id=decision_id or f"{strategy_id}-scale-decision",
        strategy_id=strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-scale-decision"),
        decision_status=status,
        recommended_action=action,
        policy=selected_policy,
        source_artifacts=[
            _source_artifact("live_observation", live_observation_path),
            *(
                [_source_artifact("micro_live_plan", micro_live_plan_path)]
                if micro_live_plan_path is not None
                else []
            ),
        ],
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=[],
    )
    decision_dir = out_dir / strategy_id
    decision_path = decision_dir / "strategy_scale_decision.json"
    report_path = decision_dir / "strategy_scale_decision.md"
    if not replace_existing and (decision_path.exists() or report_path.exists()):
        raise StrategyScaleDecisionOutputExistsError(
            f"output already exists: {repo_relative_path(decision_dir)}"
        )
    write_json_artifact(decision_path, decision.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_scale_decision_markdown(decision))
    return StrategyScaleDecisionResult(
        decision=decision,
        decision_path=decision_path,
        report_path=report_path,
    )
