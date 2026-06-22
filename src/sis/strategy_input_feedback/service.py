from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_input_feedback.models import (
    StrategyInputContractUpdateProposal,
    StrategyInputContractUpdateReview,
    StrategyInputFeedbackProposedChange,
    StrategyInputFeedbackProposalStatus,
    StrategyInputFeedbackReviewDecision,
    StrategyInputFeedbackSourceArtifact,
    StrategyInputFeedbackSourceKind,
    StrategyInputFeedbackSourceProposal,
    StrategyInputFeedbackTargetSection,
)
from sis.strategy_input_feedback.rendering import (
    render_input_feedback_proposal_markdown,
    render_input_feedback_review_markdown,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import StrategyInputContract
from sis.strategy_learning.models import StrategyLearningEvent
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_runtime_observation.models import StrategyRuntimeObservationManifest
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class StrategyInputFeedbackProposalResult:
    proposal: StrategyInputContractUpdateProposal
    proposal_path: Path
    report_path: Path


@dataclass(frozen=True)
class StrategyInputFeedbackReviewResult:
    review: StrategyInputContractUpdateReview
    review_path: Path
    report_path: Path


class StrategyInputFeedbackError(ValueError):
    pass


class StrategyInputFeedbackOutputExistsError(StrategyInputFeedbackError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(
    *,
    artifact_kind: StrategyInputFeedbackSourceKind,
    path: Path,
    schema_version: str,
) -> StrategyInputFeedbackSourceArtifact:
    return StrategyInputFeedbackSourceArtifact(
        artifact_kind=artifact_kind,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _validate_json_source(
    *,
    path: Path,
    expected_schema_version: str,
    model_type: type[StrategyRuntimeObservationManifest] | type[StrategyLearningEvent],
) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"source artifact missing: {path}")
    payload = read_json_object(path)
    schema_version = payload.get("schema_version")
    if schema_version != expected_schema_version:
        raise StrategyInputFeedbackError(
            f"expected {expected_schema_version} at {path}, found {schema_version!r}"
        )
    violations = boundary_true_paths(payload)
    if not violations:
        try:
            model_type.model_validate(payload)
        except ValidationError as exc:
            raise StrategyInputFeedbackError(f"invalid source artifact {path}: {exc}") from exc
    return payload, violations


def _validate_source_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"source contract missing: {path}")
    payload = read_mapping_file(path)
    schema_version = payload.get("schema_version")
    if schema_version != "strategy_input_contract.v1":
        raise StrategyInputFeedbackError(
            f"expected strategy_input_contract.v1 at {path}, found {schema_version!r}"
        )
    violations = boundary_true_paths(payload)
    if not violations:
        try:
            StrategyInputContract.model_validate(payload)
        except ValidationError as exc:
            raise StrategyInputFeedbackError(f"invalid source contract {path}: {exc}") from exc
    return payload, violations


def _runtime_change(index: int, payload: dict[str, Any]) -> StrategyInputFeedbackProposedChange:
    raw_summary = payload.get("summary")
    summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
    no_fill = summary.get("no_fill_count", 0)
    blocked = summary.get("blocked_count", 0)
    spread = summary.get("max_observed_spread_bps")
    evidence = (
        f"runtime ingest_status={payload.get('ingest_status')}; "
        f"no_fill_count={no_fill}; blocked_count={blocked}; "
        f"max_observed_spread_bps={spread}"
    )
    return StrategyInputFeedbackProposedChange(
        change_id=f"runtime-{index:03d}",
        target_section=StrategyInputFeedbackTargetSection.EXECUTION_REALITY,
        recommendation=(
            "Review runtime observation evidence before manually updating execution reality "
            "or source validation expectations in the Strategy Input Contract."
        ),
        evidence_summary=evidence,
        source_reason=f"runtime_observation:{payload.get('ingest_status')}",
    )


def _learning_change(index: int, payload: dict[str, Any]) -> StrategyInputFeedbackProposedChange:
    event_type = str(payload.get("event_type", "unknown"))
    recommended_action = str(payload.get("recommended_action", "unknown"))
    finding = str(payload.get("finding", ""))
    return StrategyInputFeedbackProposedChange(
        change_id=f"learning-{index:03d}",
        target_section=StrategyInputFeedbackTargetSection.KNOWN_GAPS,
        recommendation=(
            "Review the learning event before manually updating known gaps or assumptions "
            "in the Strategy Input Contract."
        ),
        evidence_summary=f"event_type={event_type}; recommended_action={recommended_action}",
        source_reason=finding or f"learning_event:{event_type}",
    )


def _default_proposal_id(
    strategy_id: str, sources: list[StrategyInputFeedbackSourceArtifact]
) -> str:
    digest = "".join(source.sha256.removeprefix("sha256:")[:8] for source in sources)[:24]
    suffix = f"-input-feedback-{digest or 'manual'}"
    return f"{strategy_id[: 128 - len(suffix)]}{suffix}"


def _default_review_id(proposal_id: str) -> str:
    digest = hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()[:8]
    suffix = f"-review-{digest}"
    return f"{proposal_id[: 128 - len(suffix)]}{suffix}"


def build_input_feedback_proposal(
    *,
    strategy_id: str,
    runtime_observation_paths: list[Path] | None,
    learning_event_paths: list[Path] | None,
    out_dir: Path,
    source_contract_path: Path | None = None,
    proposal_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyInputFeedbackProposalResult:
    runtime_paths = runtime_observation_paths or []
    learning_paths = learning_event_paths or []
    if not runtime_paths and not learning_paths:
        raise StrategyInputFeedbackError(
            "at least one --runtime-observation or --learning-event is required"
        )

    source_artifacts: list[StrategyInputFeedbackSourceArtifact] = []
    proposed_changes: list[StrategyInputFeedbackProposedChange] = []
    blocked_reasons: list[str] = []

    if source_contract_path is not None:
        _, violations = _validate_source_contract(source_contract_path)
        schema_version = (
            detect_json_schema_version(source_contract_path) or "strategy_input_contract.v1"
        )
        source_artifacts.append(
            _source_artifact(
                artifact_kind=StrategyInputFeedbackSourceKind.STRATEGY_INPUT_CONTRACT,
                path=source_contract_path,
                schema_version=schema_version,
            )
        )
        blocked_reasons.extend(f"source_contract:{violation}" for violation in violations)

    for index, path in enumerate(runtime_paths, start=1):
        payload, violations = _validate_json_source(
            path=path,
            expected_schema_version="strategy_runtime_observation_manifest.v1",
            model_type=StrategyRuntimeObservationManifest,
        )
        source_artifacts.append(
            _source_artifact(
                artifact_kind=StrategyInputFeedbackSourceKind.RUNTIME_OBSERVATION,
                path=path,
                schema_version="strategy_runtime_observation_manifest.v1",
            )
        )
        if violations:
            blocked_reasons.extend(f"runtime_observation:{violation}" for violation in violations)
        else:
            proposed_changes.append(_runtime_change(index, payload))

    for index, path in enumerate(learning_paths, start=1):
        payload, violations = _validate_json_source(
            path=path,
            expected_schema_version="strategy_learning_event.v1",
            model_type=StrategyLearningEvent,
        )
        source_artifacts.append(
            _source_artifact(
                artifact_kind=StrategyInputFeedbackSourceKind.LEARNING_EVENT,
                path=path,
                schema_version="strategy_learning_event.v1",
            )
        )
        if violations:
            blocked_reasons.extend(f"learning_event:{violation}" for violation in violations)
        else:
            proposed_changes.append(_learning_change(index, payload))

    if blocked_reasons:
        status = StrategyInputFeedbackProposalStatus.BLOCKED_BOUNDARY_VIOLATION
    elif source_contract_path is None:
        status = StrategyInputFeedbackProposalStatus.NEEDS_SOURCE_CONTRACT_CONTEXT
    elif proposed_changes:
        status = StrategyInputFeedbackProposalStatus.READY_FOR_HUMAN_REVIEW
    else:
        status = StrategyInputFeedbackProposalStatus.NO_CHANGES_RECOMMENDED

    selected_id = proposal_id or _default_proposal_id(strategy_id, source_artifacts)
    proposal = StrategyInputContractUpdateProposal(
        proposal_id=selected_id,
        strategy_id=strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-input-feedback-proposal-build"),
        status=status,
        source_artifacts=source_artifacts,
        proposed_changes=proposed_changes,
        blocked_reasons=sorted(set(blocked_reasons)),
    )
    proposal_path = out_dir / strategy_id / f"{selected_id}.json"
    report_path = out_dir / strategy_id / f"{selected_id}.md"
    if not replace_existing and (proposal_path.exists() or report_path.exists()):
        raise StrategyInputFeedbackOutputExistsError(
            f"output already exists: {repo_relative_path(proposal_path.parent)}"
        )
    write_json_artifact(proposal_path, proposal.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_input_feedback_proposal_markdown(proposal))
    return StrategyInputFeedbackProposalResult(
        proposal=proposal,
        proposal_path=proposal_path,
        report_path=report_path,
    )


def build_input_feedback_review(
    *,
    proposal_path: Path,
    out_dir: Path | None,
    reviewer: str,
    decision: StrategyInputFeedbackReviewDecision,
    rationale: str,
    approved_change_ids: list[str] | None = None,
    required_actions: list[str] | None = None,
    review_id: str | None = None,
    replace_existing: bool = False,
    reviewed_at: datetime | None = None,
) -> StrategyInputFeedbackReviewResult:
    if not proposal_path.exists():
        raise FileNotFoundError(f"proposal missing: {proposal_path}")
    proposal_payload = read_json_object(proposal_path)
    proposal = StrategyInputContractUpdateProposal.model_validate(proposal_payload)
    selected_review_id = review_id or _default_review_id(proposal.proposal_id)
    source_proposal = StrategyInputFeedbackSourceProposal(
        proposal_path=repo_relative_path(proposal_path),
        proposal_sha256=sha256_file(proposal_path),
        proposal_id=proposal.proposal_id,
        proposal_status=proposal.status,
        proposed_change_ids=[change.change_id for change in proposal.proposed_changes],
        proposed_change_count=len(proposal.proposed_changes),
    )
    review = StrategyInputContractUpdateReview(
        review_id=selected_review_id,
        proposal_id=proposal.proposal_id,
        strategy_id=proposal.strategy_id,
        reviewed_at=reviewed_at or _utc_now(),
        producer=StageProducer(command="strategy-input-feedback-proposal-review"),
        reviewer=reviewer,
        decision=decision,
        rationale=rationale,
        approved_change_ids=approved_change_ids or [],
        required_actions=required_actions or [],
        source_proposal=source_proposal,
        manual_contract_update_input_allowed=(
            decision is StrategyInputFeedbackReviewDecision.APPROVE_FOR_MANUAL_CONTRACT_UPDATE
        ),
    )
    target_dir = out_dir or proposal_path.parent
    review_path = target_dir / f"{selected_review_id}.json"
    report_path = target_dir / f"{selected_review_id}.md"
    if not replace_existing and (review_path.exists() or report_path.exists()):
        raise StrategyInputFeedbackOutputExistsError(
            f"output already exists: {repo_relative_path(review_path.parent)}"
        )
    write_json_artifact(review_path, review.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_input_feedback_review_markdown(review))
    return StrategyInputFeedbackReviewResult(
        review=review,
        review_path=review_path,
        report_path=report_path,
    )
