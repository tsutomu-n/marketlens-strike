from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from sis.strategy_drift_review.models import (
    DriftReviewAction,
    DriftReviewStatus,
    PaperVsBacktestDriftReview,
)
from sis.strategy_learning.models import (
    AuthoringUpdateHandoffStatus,
    LearningEventType,
    LearningRecommendedAction,
    RevisionRequestReviewDecision,
    RevisionRequestReviewSource,
    RevisionRequestStatus,
    StrategyLearningEvent,
    StrategyRevisionRequest,
    StrategyRevisionRequestReview,
)
from sis.strategy_review.provenance import boundary_true_paths
from sis.strategy_runtime_observation.models import RuntimeObservationSourceStage


@dataclass(frozen=True)
class AuthoringSpecStrategyMetadata:
    strategy_id: str | None
    strategy_id_matches: bool | None


def event_type_for_review(review: PaperVsBacktestDriftReview) -> LearningEventType:
    if review.review_status is DriftReviewStatus.BLOCKED_BOUNDARY_VIOLATION:
        return LearningEventType.ARTIFACT_BOUNDARY_VIOLATION
    if review.recommended_action is DriftReviewAction.EXTEND_OBSERVATION:
        return LearningEventType.INSUFFICIENT_OBSERVATION
    if review.recommended_action is DriftReviewAction.REVISE_STRATEGY:
        return LearningEventType.EXECUTION_ASSUMPTION_UPDATE
    return LearningEventType.HUMAN_REVIEW_REQUIRED


def recommended_action_for_review(
    review: PaperVsBacktestDriftReview,
) -> LearningRecommendedAction:
    if review.recommended_action is DriftReviewAction.REPAIR_ARTIFACTS:
        return LearningRecommendedAction.REPAIR_ARTIFACTS
    if review.recommended_action is DriftReviewAction.EXTEND_OBSERVATION:
        return LearningRecommendedAction.EXTEND_OBSERVATION
    if review.recommended_action is DriftReviewAction.REVISE_STRATEGY:
        return LearningRecommendedAction.REVISE_STRATEGY
    return LearningRecommendedAction.REVIEW_MANUALLY


def finding_for_review(review: PaperVsBacktestDriftReview) -> str:
    failed = [condition.condition_id for condition in review.failed_conditions]
    if failed:
        return "Drift review failed conditions: " + ", ".join(failed)
    if review.warning_conditions:
        warnings = [condition.condition_id for condition in review.warning_conditions]
        return "Drift review warning conditions: " + ", ".join(warnings)
    return f"Drift review recommended action is {review.recommended_action.value}."


def impact_for_review(review: PaperVsBacktestDriftReview) -> str:
    if review.recommended_action is DriftReviewAction.REVISE_STRATEGY:
        return "Runtime behavior may invalidate execution assumptions used by the backtest."
    if review.recommended_action is DriftReviewAction.EXTEND_OBSERVATION:
        return "Current runtime evidence is too thin to justify a strategy revision or advancement."
    if review.recommended_action is DriftReviewAction.REPAIR_ARTIFACTS:
        return "Source artifacts are not safe to use until boundary violations are repaired."
    return "A human must review the drift evidence before changing the strategy."


def source_stage_for_review(
    review: PaperVsBacktestDriftReview,
) -> RuntimeObservationSourceStage | Literal["drift_review"]:
    if review.runtime_summary is None:
        return "drift_review"
    return review.runtime_summary.source_stage


def revision_status_for_events(events: list[StrategyLearningEvent]) -> RevisionRequestStatus:
    if any(
        event.recommended_action is LearningRecommendedAction.REPAIR_ARTIFACTS for event in events
    ):
        return RevisionRequestStatus.BLOCKED_BOUNDARY_VIOLATION
    if any(
        event.recommended_action is LearningRecommendedAction.REVISE_STRATEGY for event in events
    ):
        return RevisionRequestStatus.READY_FOR_HUMAN_REVIEW
    return RevisionRequestStatus.NO_REVISION_REQUIRED


def revision_reason_for_events(events: list[StrategyLearningEvent]) -> str:
    if any(
        event.recommended_action is LearningRecommendedAction.REPAIR_ARTIFACTS for event in events
    ):
        return "artifact_boundary_violation"
    if any("runtime_no_fill_rate_within_limit" in event.finding for event in events):
        return "no_fill_drift"
    if any("runtime_blocked_rate_within_limit" in event.finding for event in events):
        return "blocked_drift"
    if any("runtime_spread_within_limit" in event.finding for event in events):
        return "spread_drift"
    if any(
        event.recommended_action is LearningRecommendedAction.EXTEND_OBSERVATION for event in events
    ):
        return "insufficient_observation"
    return "human_review_required"


def requested_changes_for_events(events: list[StrategyLearningEvent]) -> list[str]:
    changes: list[str] = []
    for event in events:
        if event.recommended_action is LearningRecommendedAction.REVISE_STRATEGY:
            changes.append("Review and revise execution assumptions before the next backtest.")
            if "runtime_no_fill_rate_within_limit" in event.finding:
                changes.append("Add or tighten no-fill / no-trade conditions.")
            if "runtime_blocked_rate_within_limit" in event.finding:
                changes.append("Investigate block reasons and revise entry or risk filters.")
            if "runtime_spread_within_limit" in event.finding:
                changes.append("Revise spread or slippage assumptions before authoring update.")
        elif event.recommended_action is LearningRecommendedAction.EXTEND_OBSERVATION:
            changes.append("Extend paper observation before changing the strategy.")
        elif event.recommended_action is LearningRecommendedAction.REPAIR_ARTIFACTS:
            changes.append("Repair source artifact boundary violations before using this evidence.")
        else:
            changes.append("Human review required before deciding whether to revise authoring.")
    return list(dict.fromkeys(changes))


def revision_request_review_source(
    *,
    revision_request_path: str,
    revision_request_sha256: str,
    request: StrategyRevisionRequest,
) -> RevisionRequestReviewSource:
    return RevisionRequestReviewSource(
        revision_request_path=revision_request_path,
        revision_request_sha256=revision_request_sha256,
        revision_request_id=request.revision_request_id,
        request_status=request.request_status,
        requested_change_count=len(request.requested_changes),
        source_learning_event_count=len(request.source_learning_event_ids),
        auto_applied=request.auto_applied,
        direct_spec_edit_allowed=request.direct_spec_edit_allowed,
        paper_execution_allowed=request.paper_execution_allowed,
        live_allowed=request.live_allowed,
    )


def reviewed_at_value(reviewed_at: datetime | None) -> datetime:
    value = reviewed_at or datetime.now(timezone.utc).replace(microsecond=0)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def handoff_status_for_payloads(
    *,
    request_payload: dict[str, Any],
    review_payload: dict[str, Any],
    authoring_payload: dict[str, Any],
    review: StrategyRevisionRequestReview,
) -> AuthoringUpdateHandoffStatus:
    boundary_violations = [
        *boundary_true_paths(request_payload),
        *boundary_true_paths(review_payload),
        *boundary_true_paths(authoring_payload),
    ]
    if boundary_violations:
        return AuthoringUpdateHandoffStatus.BLOCKED_BOUNDARY_VIOLATION
    if (
        review.decision is not RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE
        or not review.authoring_update_input_allowed
    ):
        return AuthoringUpdateHandoffStatus.NEEDS_REVISION_REVIEW_APPROVAL
    return AuthoringUpdateHandoffStatus.READY_FOR_HUMAN_AUTHORING_UPDATE


def authoring_spec_strategy_metadata(
    *,
    authoring_payload: dict[str, Any],
    expected_strategy_id: str,
) -> AuthoringSpecStrategyMetadata:
    strategy_id_raw = authoring_payload.get("strategy_id")
    strategy_id = (
        strategy_id_raw.strip()
        if isinstance(strategy_id_raw, str) and strategy_id_raw.strip()
        else None
    )
    strategy_id_matches = expected_strategy_id == strategy_id if strategy_id is not None else None
    return AuthoringSpecStrategyMetadata(
        strategy_id=strategy_id,
        strategy_id_matches=strategy_id_matches,
    )


def authoring_update_tasks_for_request(request: StrategyRevisionRequest) -> list[str]:
    tasks = [
        "Open the current Strategy Authoring YAML and review it before editing.",
        "Apply only the approved revision request changes in a separate human edit.",
    ]
    tasks.extend(f"Review requested change: {change}" for change in request.requested_changes)
    tasks.extend(
        [
            "Run Strategy Authoring validation after editing.",
            "Run a fresh backtest and build a new review packet before any stage decision.",
        ]
    )
    return list(dict.fromkeys(tasks))
