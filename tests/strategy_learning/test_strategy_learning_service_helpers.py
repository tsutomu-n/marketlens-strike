from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sis.strategy_drift_review.models import DriftReviewAction, PaperVsBacktestDriftReview
from sis.strategy_learning.models import (
    AuthoringUpdateHandoffStatus,
    LearningEventType,
    LearningRecommendedAction,
    LearningSourceArtifact,
    RevisionRequestReviewDecision,
    RevisionRequestReviewSource,
    RevisionRequestStatus,
    StrategyLearningEvent,
    StrategyRevisionRequest,
    StrategyRevisionRequestReview,
)
from sis.strategy_learning.service_helpers import authoring_update_tasks_for_request
from sis.strategy_learning.service_helpers import event_type_for_review
from sis.strategy_learning.service_helpers import finding_for_review
from sis.strategy_learning.service_helpers import handoff_status_for_payloads
from sis.strategy_learning.service_helpers import impact_for_review
from sis.strategy_learning.service_helpers import recommended_action_for_review
from sis.strategy_learning.service_helpers import requested_changes_for_events
from sis.strategy_learning.service_helpers import reviewed_at_value
from sis.strategy_learning.service_helpers import revision_reason_for_events
from sis.strategy_learning.service_helpers import revision_status_for_events
from sis.strategy_learning.service_helpers import source_stage_for_review
from sis.strategy_stage.models import StageProducer


def _condition(condition_id: str, passed: bool = False) -> dict[str, object]:
    return {
        "condition_id": condition_id,
        "passed": passed,
        "observed": "0.75",
        "required": "<= 0.5",
        "severity": "error",
    }


def _review(
    *,
    review_status: str = "READY_FOR_HUMAN_DRIFT_REVIEW",
    recommended_action: str = "REVISE_STRATEGY",
    failed_conditions: list[dict[str, object]] | None = None,
    warning_conditions: list[dict[str, object]] | None = None,
    include_runtime_summary: bool = True,
):
    payload: dict[str, object] = {
        "schema_version": "paper_vs_backtest_drift_review.v1",
        "strategy_id": "ndx-breakout-001",
        "created_at": "2026-06-19T00:00:00Z",
        "producer": {"tool": "sis", "command": "strategy-drift-review"},
        "review_status": review_status,
        "recommended_action": recommended_action,
        "source_artifacts": [
            {
                "artifact_key": "strategy_authoring_backtest_result",
                "path": "data/research/strategy_authoring/backtest_result.json",
                "sha256": "sha256:" + "a" * 64,
                "schema_version": "strategy_authoring_backtest_result.v1",
            }
        ],
        "drift_metrics": {},
        "passed_conditions": [],
        "failed_conditions": failed_conditions or [],
        "warning_conditions": warning_conditions or [],
        "paper_execution_allowed": False,
        "live_allowed": False,
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }
    if include_runtime_summary:
        payload["runtime_summary"] = {
            "strategy_id": "ndx-breakout-001",
            "session_id": "paper-001",
            "source_stage": "paper_smoke",
            "ingest_status": "INGESTED",
            "ledger_entry_count": 4,
            "paper_fill_count": 1,
            "blocked_count": 1,
            "no_fill_count": 3,
        }
    return PaperVsBacktestDriftReview.model_validate(payload)


def _learning_event(
    *,
    event_id: str,
    action: LearningRecommendedAction,
    finding: str,
) -> StrategyLearningEvent:
    return StrategyLearningEvent(
        learning_event_id=event_id,
        strategy_id="ndx-breakout-001",
        created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
        producer=StageProducer(command="strategy-learning-ledger-update"),
        source_stage="paper_smoke",
        source_artifacts=[
            LearningSourceArtifact(
                artifact_key="paper_vs_backtest_drift_review",
                path="data/review.json",
                sha256="sha256:" + "b" * 64,
                schema_version="paper_vs_backtest_drift_review.v1",
            )
        ],
        event_type=LearningEventType.EXECUTION_ASSUMPTION_UPDATE,
        finding=finding,
        impact="impact",
        recommended_action=action,
        source_review_status="READY_FOR_HUMAN_DRIFT_REVIEW",
        source_recommended_action=DriftReviewAction.REVISE_STRATEGY.value,
    )


def _revision_request() -> StrategyRevisionRequest:
    return StrategyRevisionRequest(
        revision_request_id="revise-001",
        strategy_id="ndx-breakout-001",
        created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
        producer=StageProducer(command="strategy-revision-request-build"),
        request_status=RevisionRequestStatus.READY_FOR_HUMAN_REVIEW,
        reason="no_fill_drift",
        source_learning_event_ids=["learn-001"],
        source_artifacts=[
            LearningSourceArtifact(
                artifact_key="strategy_learning_ledger",
                path="data/strategy_learning/ledger.jsonl",
                sha256="sha256:" + "c" * 64,
                schema_version=None,
            )
        ],
        requested_changes=[
            "Review and revise execution assumptions before the next backtest.",
            "Review and revise execution assumptions before the next backtest.",
        ],
    )


def _review_record(
    decision: RevisionRequestReviewDecision,
) -> StrategyRevisionRequestReview:
    return StrategyRevisionRequestReview(
        revision_request_id="revise-001",
        strategy_id="ndx-breakout-001",
        reviewed_at=datetime(2026, 6, 20, tzinfo=timezone.utc),
        producer=StageProducer(command="strategy-revision-request-review"),
        reviewer="reviewer",
        decision=decision,
        rationale="reviewed",
        required_actions=[],
        source_revision_request=RevisionRequestReviewSource(
            revision_request_path="data/revision_request.json",
            revision_request_sha256="sha256:" + "d" * 64,
            revision_request_id="revise-001",
            request_status=RevisionRequestStatus.READY_FOR_HUMAN_REVIEW,
            requested_change_count=1,
            source_learning_event_count=1,
        ),
        authoring_update_input_allowed=(
            decision is RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE
        ),
    )


def test_drift_review_helpers_map_actions_findings_impacts_and_source_stage() -> None:
    revise = _review(failed_conditions=[_condition("runtime_no_fill_rate_within_limit")])
    assert event_type_for_review(revise) is LearningEventType.EXECUTION_ASSUMPTION_UPDATE
    assert recommended_action_for_review(revise) is LearningRecommendedAction.REVISE_STRATEGY
    assert finding_for_review(revise) == (
        "Drift review failed conditions: runtime_no_fill_rate_within_limit"
    )
    assert impact_for_review(revise) == (
        "Runtime behavior may invalidate execution assumptions used by the backtest."
    )
    assert source_stage_for_review(revise) == "paper_smoke"

    extend = _review(recommended_action="EXTEND_OBSERVATION")
    assert event_type_for_review(extend) is LearningEventType.INSUFFICIENT_OBSERVATION
    assert recommended_action_for_review(extend) is LearningRecommendedAction.EXTEND_OBSERVATION
    assert impact_for_review(extend) == (
        "Current runtime evidence is too thin to justify a strategy revision or advancement."
    )

    blocked = _review(
        review_status="BLOCKED_BOUNDARY_VIOLATION",
        recommended_action="REPAIR_ARTIFACTS",
        include_runtime_summary=False,
    )
    assert event_type_for_review(blocked) is LearningEventType.ARTIFACT_BOUNDARY_VIOLATION
    assert recommended_action_for_review(blocked) is LearningRecommendedAction.REPAIR_ARTIFACTS
    assert source_stage_for_review(blocked) == "drift_review"

    warning = _review(
        recommended_action="HUMAN_REVIEW_REQUIRED",
        warning_conditions=[_condition("runtime_spread_within_limit")],
    )
    assert event_type_for_review(warning) is LearningEventType.HUMAN_REVIEW_REQUIRED
    assert recommended_action_for_review(warning) is LearningRecommendedAction.REVIEW_MANUALLY
    assert finding_for_review(warning) == (
        "Drift review warning conditions: runtime_spread_within_limit"
    )


def test_revision_helpers_prioritize_status_reason_and_requested_changes() -> None:
    repair = _learning_event(
        event_id="learn-repair",
        action=LearningRecommendedAction.REPAIR_ARTIFACTS,
        finding="boundary violation",
    )
    revise = _learning_event(
        event_id="learn-revise",
        action=LearningRecommendedAction.REVISE_STRATEGY,
        finding="runtime_no_fill_rate_within_limit failed",
    )
    extend = _learning_event(
        event_id="learn-extend",
        action=LearningRecommendedAction.EXTEND_OBSERVATION,
        finding="thin evidence",
    )

    assert revision_status_for_events([repair, revise, extend]) is (
        RevisionRequestStatus.BLOCKED_BOUNDARY_VIOLATION
    )
    assert revision_reason_for_events([repair, revise, extend]) == "artifact_boundary_violation"

    assert (
        revision_status_for_events([revise, extend]) is RevisionRequestStatus.READY_FOR_HUMAN_REVIEW
    )
    assert revision_reason_for_events([revise, extend]) == "no_fill_drift"
    assert requested_changes_for_events([revise, extend, repair]) == [
        "Review and revise execution assumptions before the next backtest.",
        "Add or tighten no-fill / no-trade conditions.",
        "Extend paper observation before changing the strategy.",
        "Repair source artifact boundary violations before using this evidence.",
    ]


def test_reviewed_at_value_normalizes_to_utc() -> None:
    assert reviewed_at_value(datetime(2026, 6, 20, 9, 0)) == datetime(
        2026, 6, 20, 9, 0, tzinfo=timezone.utc
    )
    assert reviewed_at_value(
        datetime(2026, 6, 20, 18, 0, tzinfo=timezone(timedelta(hours=9)))
    ) == datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc)


def test_handoff_status_and_authoring_tasks_preserve_manual_boundaries() -> None:
    request = _revision_request()
    approved = _review_record(RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE)
    hold = _review_record(RevisionRequestReviewDecision.HOLD)

    assert (
        handoff_status_for_payloads(
            request_payload={},
            review_payload={},
            authoring_payload={},
            review=approved,
        )
        is AuthoringUpdateHandoffStatus.READY_FOR_HUMAN_AUTHORING_UPDATE
    )
    assert (
        handoff_status_for_payloads(
            request_payload={},
            review_payload={},
            authoring_payload={},
            review=hold,
        )
        is AuthoringUpdateHandoffStatus.NEEDS_REVISION_REVIEW_APPROVAL
    )
    assert (
        handoff_status_for_payloads(
            request_payload={"boundary": {"wallet_used": True}},
            review_payload={},
            authoring_payload={},
            review=approved,
        )
        is AuthoringUpdateHandoffStatus.BLOCKED_BOUNDARY_VIOLATION
    )

    assert authoring_update_tasks_for_request(request) == [
        "Open the current Strategy Authoring YAML and review it before editing.",
        "Apply only the approved revision request changes in a separate human edit.",
        "Review requested change: Review and revise execution assumptions before the next backtest.",
        "Run Strategy Authoring validation after editing.",
        "Run a fresh backtest and build a new review packet before any stage decision.",
    ]
