from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_drift_review.models import (
    DriftReviewAction,
    DriftReviewStatus,
    PaperVsBacktestDriftReview,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_learning.models import (
    AuthoringUpdateHandoffStatus,
    LearningEventType,
    LearningRecommendedAction,
    LearningSourceArtifact,
    RevisionRequestReviewDecision,
    RevisionRequestReviewSource,
    RevisionRequestStatus,
    StrategyLearningEvent,
    StrategyAuthoringUpdateHandoff,
    StrategyRevisionRequest,
    StrategyRevisionRequestReview,
)
from sis.strategy_learning.rendering import (
    render_authoring_update_handoff_markdown,
    render_learning_summary_markdown,
    render_revision_request_markdown,
    render_revision_request_review_markdown,
)
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_runtime_observation.models import RuntimeObservationSourceStage
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class LearningLedgerUpdateResult:
    event: StrategyLearningEvent
    event_path: Path
    ledger_path: Path
    summary_path: Path


@dataclass(frozen=True)
class RevisionRequestBuildResult:
    request: StrategyRevisionRequest
    request_path: Path
    report_path: Path


@dataclass(frozen=True)
class RevisionRequestReviewRecordResult:
    review: StrategyRevisionRequestReview
    review_path: Path
    report_path: Path


@dataclass(frozen=True)
class AuthoringUpdateHandoffBuildResult:
    handoff: StrategyAuthoringUpdateHandoff
    handoff_path: Path
    report_path: Path


class StrategyLearningError(ValueError):
    pass


class StrategyLearningOutputExistsError(StrategyLearningError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(artifact_key: str, path: Path) -> LearningSourceArtifact:
    return LearningSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _stable_id(prefix: str, path: Path) -> str:
    return f"{prefix}-{sha256_file(path).removeprefix('sha256:')[:12]}"


def _read_drift_review(path: Path) -> tuple[dict[str, Any], PaperVsBacktestDriftReview]:
    payload = read_json_object(path)
    try:
        return payload, PaperVsBacktestDriftReview.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise StrategyLearningError(f"invalid drift review: {exc}") from exc


def _read_revision_request(path: Path) -> tuple[dict[str, Any], StrategyRevisionRequest]:
    payload = read_json_object(path)
    try:
        return payload, StrategyRevisionRequest.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise StrategyLearningError(f"invalid revision request: {exc}") from exc


def _read_revision_request_review(
    path: Path,
) -> tuple[dict[str, Any], StrategyRevisionRequestReview]:
    payload = read_json_object(path)
    try:
        return payload, StrategyRevisionRequestReview.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise StrategyLearningError(f"invalid revision request review: {exc}") from exc


def _event_type_for(review: PaperVsBacktestDriftReview) -> LearningEventType:
    if review.review_status is DriftReviewStatus.BLOCKED_BOUNDARY_VIOLATION:
        return LearningEventType.ARTIFACT_BOUNDARY_VIOLATION
    if review.recommended_action is DriftReviewAction.EXTEND_OBSERVATION:
        return LearningEventType.INSUFFICIENT_OBSERVATION
    if review.recommended_action is DriftReviewAction.REVISE_STRATEGY:
        return LearningEventType.EXECUTION_ASSUMPTION_UPDATE
    return LearningEventType.HUMAN_REVIEW_REQUIRED


def _recommended_action_for(review: PaperVsBacktestDriftReview) -> LearningRecommendedAction:
    if review.recommended_action is DriftReviewAction.REPAIR_ARTIFACTS:
        return LearningRecommendedAction.REPAIR_ARTIFACTS
    if review.recommended_action is DriftReviewAction.EXTEND_OBSERVATION:
        return LearningRecommendedAction.EXTEND_OBSERVATION
    if review.recommended_action is DriftReviewAction.REVISE_STRATEGY:
        return LearningRecommendedAction.REVISE_STRATEGY
    return LearningRecommendedAction.REVIEW_MANUALLY


def _finding_for(review: PaperVsBacktestDriftReview) -> str:
    failed = [condition.condition_id for condition in review.failed_conditions]
    if failed:
        return "Drift review failed conditions: " + ", ".join(failed)
    if review.warning_conditions:
        warnings = [condition.condition_id for condition in review.warning_conditions]
        return "Drift review warning conditions: " + ", ".join(warnings)
    return f"Drift review recommended action is {review.recommended_action.value}."


def _impact_for(review: PaperVsBacktestDriftReview) -> str:
    if review.recommended_action is DriftReviewAction.REVISE_STRATEGY:
        return "Runtime behavior may invalidate execution assumptions used by the backtest."
    if review.recommended_action is DriftReviewAction.EXTEND_OBSERVATION:
        return "Current runtime evidence is too thin to justify a strategy revision or advancement."
    if review.recommended_action is DriftReviewAction.REPAIR_ARTIFACTS:
        return "Source artifacts are not safe to use until boundary violations are repaired."
    return "A human must review the drift evidence before changing the strategy."


def _source_stage_for(
    review: PaperVsBacktestDriftReview,
) -> RuntimeObservationSourceStage | Literal["drift_review"]:
    if review.runtime_summary is None:
        return "drift_review"
    return review.runtime_summary.source_stage


def _read_ledger(path: Path) -> list[StrategyLearningEvent]:
    if not path.exists():
        return []
    events: list[StrategyLearningEvent] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise StrategyLearningError(f"invalid learning ledger JSONL at {path}:{index}") from exc
        events.append(StrategyLearningEvent.model_validate(payload))
    return events


def _authoring_update_tasks(request: StrategyRevisionRequest) -> list[str]:
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


def _write_ledger(path: Path, events: list[StrategyLearningEvent]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"
    try:
        tmp_path.write_text(
            "".join(
                json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
                for event in events
            ),
            encoding="utf-8",
        )
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path


def update_learning_ledger(
    *,
    drift_review_path: Path,
    out_dir: Path,
    strategy_id: str | None = None,
    learning_event_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> LearningLedgerUpdateResult:
    if not drift_review_path.exists():
        raise FileNotFoundError(f"drift review missing: {drift_review_path}")
    drift_payload, review = _read_drift_review(drift_review_path)
    selected_strategy_id = strategy_id or review.strategy_id
    selected_event_id = learning_event_id or _stable_id("learn", drift_review_path)
    boundary_violations = boundary_true_paths(drift_payload)

    strategy_dir = out_dir / selected_strategy_id
    event_path = strategy_dir / "learning_events" / f"{selected_event_id}.json"
    ledger_path = strategy_dir / "learning_ledger.jsonl"
    summary_path = strategy_dir / "learning_summary.md"
    if event_path.exists() and not replace_existing:
        raise StrategyLearningOutputExistsError(
            f"learning event already exists: {repo_relative_path(event_path)}"
        )

    event = StrategyLearningEvent(
        learning_event_id=selected_event_id,
        strategy_id=selected_strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-learning-ledger-update"),
        source_stage=_source_stage_for(review),
        source_artifacts=[_source_artifact("paper_vs_backtest_drift_review", drift_review_path)],
        event_type=(
            LearningEventType.ARTIFACT_BOUNDARY_VIOLATION
            if boundary_violations
            else _event_type_for(review)
        ),
        finding=_finding_for(review),
        impact=_impact_for(review),
        recommended_action=(
            LearningRecommendedAction.REPAIR_ARTIFACTS
            if boundary_violations
            else _recommended_action_for(review)
        ),
        source_review_status=review.review_status.value,
        source_recommended_action=review.recommended_action.value,
    )

    existing_events = [
        existing
        for existing in _read_ledger(ledger_path)
        if existing.learning_event_id != event.learning_event_id
    ]
    events = [*existing_events, event]
    write_json_artifact(event_path, event.model_dump(mode="json", exclude_none=True))
    _write_ledger(ledger_path, events)
    write_text_artifact(summary_path, render_learning_summary_markdown(events))
    return LearningLedgerUpdateResult(
        event=event,
        event_path=event_path,
        ledger_path=ledger_path,
        summary_path=summary_path,
    )


def _revision_status(events: list[StrategyLearningEvent]) -> RevisionRequestStatus:
    if any(
        event.recommended_action is LearningRecommendedAction.REPAIR_ARTIFACTS for event in events
    ):
        return RevisionRequestStatus.BLOCKED_BOUNDARY_VIOLATION
    if any(
        event.recommended_action is LearningRecommendedAction.REVISE_STRATEGY for event in events
    ):
        return RevisionRequestStatus.READY_FOR_HUMAN_REVIEW
    return RevisionRequestStatus.NO_REVISION_REQUIRED


def _revision_reason(events: list[StrategyLearningEvent]) -> str:
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


def _requested_changes(events: list[StrategyLearningEvent]) -> list[str]:
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


def build_revision_request(
    *,
    strategy_id: str,
    learning_ledger_path: Path,
    out_dir: Path,
    revision_request_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> RevisionRequestBuildResult:
    if not learning_ledger_path.exists():
        raise FileNotFoundError(f"learning ledger missing: {learning_ledger_path}")
    all_events = _read_ledger(learning_ledger_path)
    events = [event for event in all_events if event.strategy_id == strategy_id]
    if not events:
        raise StrategyLearningError(f"no learning events for strategy_id: {strategy_id}")
    selected_request_id = revision_request_id or _stable_id("revise", learning_ledger_path)
    request_path = out_dir / f"{selected_request_id}.json"
    report_path = out_dir / f"{selected_request_id}.md"
    if not replace_existing and (request_path.exists() or report_path.exists()):
        raise StrategyLearningOutputExistsError(
            f"revision request already exists: {repo_relative_path(request_path)}"
        )

    request = StrategyRevisionRequest(
        revision_request_id=selected_request_id,
        strategy_id=strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-revision-request-build"),
        request_status=_revision_status(events),
        reason=_revision_reason(events),
        source_learning_event_ids=[event.learning_event_id for event in events],
        source_artifacts=[_source_artifact("strategy_learning_ledger", learning_ledger_path)],
        requested_changes=_requested_changes(events),
    )
    write_json_artifact(request_path, request.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_revision_request_markdown(request))
    return RevisionRequestBuildResult(
        request=request, request_path=request_path, report_path=report_path
    )


def _reviewed_at_value(reviewed_at: datetime | None) -> datetime:
    value = reviewed_at or _utc_now()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def record_revision_request_review(
    *,
    revision_request_path: Path,
    out_dir: Path | None,
    reviewer: str,
    decision: RevisionRequestReviewDecision,
    rationale: str,
    required_actions: list[str] | None = None,
    replace_existing: bool = False,
    reviewed_at: datetime | None = None,
) -> RevisionRequestReviewRecordResult:
    if not revision_request_path.exists():
        raise FileNotFoundError(f"revision request missing: {revision_request_path}")
    revision_payload, request = _read_revision_request(revision_request_path)
    boundary_violations = boundary_true_paths(revision_payload)
    if boundary_violations:
        raise StrategyLearningError(
            "revision request boundary violation: " + ", ".join(boundary_violations)
        )
    selected_out_dir = out_dir or revision_request_path.parent
    review_path = selected_out_dir / f"{request.revision_request_id}_review.json"
    report_path = selected_out_dir / f"{request.revision_request_id}_review.md"
    if not replace_existing and (review_path.exists() or report_path.exists()):
        raise StrategyLearningOutputExistsError(
            f"revision request review already exists: {repo_relative_path(review_path)}"
        )

    source = RevisionRequestReviewSource(
        revision_request_path=repo_relative_path(revision_request_path),
        revision_request_sha256=sha256_file(revision_request_path),
        revision_request_id=request.revision_request_id,
        request_status=request.request_status,
        requested_change_count=len(request.requested_changes),
        source_learning_event_count=len(request.source_learning_event_ids),
        auto_applied=request.auto_applied,
        direct_spec_edit_allowed=request.direct_spec_edit_allowed,
        paper_execution_allowed=request.paper_execution_allowed,
        live_allowed=request.live_allowed,
    )
    review = StrategyRevisionRequestReview(
        revision_request_id=request.revision_request_id,
        strategy_id=request.strategy_id,
        reviewed_at=_reviewed_at_value(reviewed_at),
        producer=StageProducer(command="strategy-revision-request-review"),
        reviewer=reviewer,
        decision=decision,
        rationale=rationale,
        required_actions=required_actions or [],
        source_revision_request=source,
        authoring_update_input_allowed=(
            decision is RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE
        ),
    )
    write_json_artifact(review_path, review.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_revision_request_review_markdown(review))
    return RevisionRequestReviewRecordResult(
        review=review, review_path=review_path, report_path=report_path
    )


def _handoff_status(
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


def build_authoring_update_handoff(
    *,
    revision_request_path: Path,
    revision_review_path: Path,
    authoring_spec_path: Path,
    out_dir: Path,
    handoff_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> AuthoringUpdateHandoffBuildResult:
    if not revision_request_path.exists():
        raise FileNotFoundError(f"revision request missing: {revision_request_path}")
    if not revision_review_path.exists():
        raise FileNotFoundError(f"revision request review missing: {revision_review_path}")
    if not authoring_spec_path.exists():
        raise FileNotFoundError(f"authoring spec missing: {authoring_spec_path}")

    request_payload, request = _read_revision_request(revision_request_path)
    review_payload, review = _read_revision_request_review(revision_review_path)
    authoring_payload = read_mapping_file(authoring_spec_path)

    if request.revision_request_id != review.revision_request_id:
        raise StrategyLearningError("revision request id mismatch between request and review")
    if request.strategy_id != review.strategy_id:
        raise StrategyLearningError("strategy id mismatch between request and review")

    selected_handoff_id = handoff_id or _stable_id("authoring-handoff", revision_review_path)
    handoff_path = out_dir / f"{selected_handoff_id}.json"
    report_path = out_dir / f"{selected_handoff_id}.md"
    if not replace_existing and (handoff_path.exists() or report_path.exists()):
        raise StrategyLearningOutputExistsError(
            f"authoring update handoff already exists: {repo_relative_path(handoff_path)}"
        )

    authoring_strategy_id_raw = authoring_payload.get("strategy_id")
    authoring_strategy_id = (
        authoring_strategy_id_raw.strip()
        if isinstance(authoring_strategy_id_raw, str) and authoring_strategy_id_raw.strip()
        else None
    )
    strategy_id_matches = (
        request.strategy_id == authoring_strategy_id if authoring_strategy_id is not None else None
    )

    handoff = StrategyAuthoringUpdateHandoff(
        handoff_id=selected_handoff_id,
        revision_request_id=request.revision_request_id,
        strategy_id=request.strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-authoring-update-handoff"),
        handoff_status=_handoff_status(
            request_payload=request_payload,
            review_payload=review_payload,
            authoring_payload=authoring_payload,
            review=review,
        ),
        review_decision=review.decision,
        authoring_update_input_allowed=review.authoring_update_input_allowed,
        source_artifacts=[
            _source_artifact("strategy_revision_request", revision_request_path),
            _source_artifact("strategy_revision_request_review", revision_review_path),
            _source_artifact("strategy_authoring_spec", authoring_spec_path),
        ],
        requested_changes=request.requested_changes,
        authoring_update_tasks=_authoring_update_tasks(request),
        authoring_spec_path=repo_relative_path(authoring_spec_path),
        authoring_spec_sha256=sha256_file(authoring_spec_path),
        authoring_spec_schema_version=detect_json_schema_version(authoring_spec_path),
        authoring_spec_strategy_id=authoring_strategy_id,
        strategy_id_matches_authoring_spec=strategy_id_matches,
    )

    write_json_artifact(handoff_path, handoff.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_authoring_update_handoff_markdown(handoff))
    return AuthoringUpdateHandoffBuildResult(
        handoff=handoff, handoff_path=handoff_path, report_path=report_path
    )
