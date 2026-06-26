from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_drift_review.models import PaperVsBacktestDriftReview
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_learning.service_helpers import (
    authoring_update_tasks_for_request as _authoring_update_tasks,
)
from sis.strategy_learning.service_helpers import event_type_for_review as _event_type_for
from sis.strategy_learning.service_helpers import finding_for_review as _finding_for
from sis.strategy_learning.service_helpers import (
    handoff_status_for_payloads as _handoff_status,
)
from sis.strategy_learning.service_helpers import impact_for_review as _impact_for
from sis.strategy_learning.service_helpers import (
    recommended_action_for_review as _recommended_action_for,
)
from sis.strategy_learning.service_helpers import requested_changes_for_events as _requested_changes
from sis.strategy_learning.service_helpers import (
    reviewed_at_value as _reviewed_at_value,
)
from sis.strategy_learning.service_helpers import revision_reason_for_events as _revision_reason
from sis.strategy_learning.service_helpers import revision_status_for_events as _revision_status
from sis.strategy_learning.service_helpers import source_stage_for_review as _source_stage_for
from sis.strategy_learning.service_ledger import (
    LearningLedgerIOError as _LearningLedgerIOError,
)
from sis.strategy_learning.service_ledger import read_learning_ledger as _read_learning_ledger
from sis.strategy_learning.service_ledger import write_learning_ledger as _write_learning_ledger
from sis.strategy_learning.models import (
    LearningEventType,
    LearningRecommendedAction,
    LearningSourceArtifact,
    RevisionRequestReviewDecision,
    RevisionRequestReviewSource,
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


def _read_ledger(path: Path) -> list[StrategyLearningEvent]:
    try:
        return _read_learning_ledger(path)
    except _LearningLedgerIOError as exc:
        raise StrategyLearningError(str(exc)) from exc


def _write_ledger(path: Path, events: list[StrategyLearningEvent]) -> Path:
    return _write_learning_ledger(path, events)


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
