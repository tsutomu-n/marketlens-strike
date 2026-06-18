from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_review.operator_review import OperatorStrategyReview
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_stage.models import (
    StageCondition,
    StageDecisionStatus,
    StageName,
    StagePaperEvidenceSummary,
    StagePaperRequirementGap,
    StagePolicyValidationStatus,
    StageProducer,
    StageSourceArtifact,
    StageThresholds,
    StrategyStageDecision,
    StrategyStagePolicy,
    StrategyStagePolicyValidation,
    StagePolicyValidationSummary,
)
from sis.strategy_stage.rendering import (
    render_stage_decision_markdown,
    render_stage_policy_validation_markdown,
)


@dataclass(frozen=True)
class StagePolicyValidationResult:
    validation: StrategyStagePolicyValidation
    validation_path: Path
    report_path: Path


@dataclass(frozen=True)
class StageDecisionResult:
    decision: StrategyStageDecision
    decision_path: Path
    report_path: Path


class StrategyStageError(ValueError):
    pass


class StrategyStageOutputExistsError(StrategyStageError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _read_policy(policy_path: Path) -> StrategyStagePolicy:
    payload = read_mapping_file(policy_path)
    violations = boundary_true_paths(payload)
    if violations:
        raise StrategyStageError("policy boundary violation: " + ", ".join(violations))
    return StrategyStagePolicy.model_validate(payload)


def _write_policy_validation(
    *, out_dir: Path, validation: StrategyStagePolicyValidation, replace_existing: bool
) -> StagePolicyValidationResult:
    validation_path = out_dir / "strategy_stage_policy_validation.json"
    report_path = out_dir / "strategy_stage_policy_validation.md"
    if not replace_existing and (validation_path.exists() or report_path.exists()):
        raise StrategyStageOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(validation_path, validation.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_stage_policy_validation_markdown(validation))
    return StagePolicyValidationResult(
        validation=validation,
        validation_path=validation_path,
        report_path=report_path,
    )


def validate_stage_policy(
    *,
    policy_path: Path,
    out_dir: Path,
    replace_existing: bool = False,
    validated_at: datetime | None = None,
) -> StagePolicyValidationResult:
    payload = read_mapping_file(policy_path)
    violations = boundary_true_paths(payload)
    if violations:
        raw_policy_id = payload.get("policy_id")
        policy_id = raw_policy_id if isinstance(raw_policy_id, str) else "unknown"
        validation = StrategyStagePolicyValidation(
            policy_id=policy_id,
            policy_path=repo_relative_path(policy_path),
            policy_hash=sha256_file(policy_path),
            validated_at=validated_at or _utc_now(),
            producer=StageProducer(command="strategy-stage-policy-validate"),
            validation_status=StagePolicyValidationStatus.BLOCKED_BOUNDARY_VIOLATION,
            summary=StagePolicyValidationSummary(
                stage_count=0,
                profile_count=0,
                boundary_violation_count=len(violations),
            ),
        )
        return _write_policy_validation(
            out_dir=out_dir, validation=validation, replace_existing=replace_existing
        )

    try:
        policy = StrategyStagePolicy.model_validate(payload)
    except ValidationError as exc:
        raise StrategyStageError(f"invalid stage policy: {exc}") from exc

    validation = StrategyStagePolicyValidation(
        policy_id=policy.policy_id,
        policy_path=repo_relative_path(policy_path),
        policy_hash=sha256_file(policy_path),
        validated_at=validated_at or _utc_now(),
        producer=StageProducer(command="strategy-stage-policy-validate"),
        validation_status=StagePolicyValidationStatus.PASS,
        summary=StagePolicyValidationSummary(
            stage_count=len(policy.stages),
            profile_count=len(policy.strategy_profiles),
            boundary_violation_count=0,
        ),
    )
    return _write_policy_validation(
        out_dir=out_dir, validation=validation, replace_existing=replace_existing
    )


def _write_stage_decision(
    *, out_dir: Path, decision: StrategyStageDecision, replace_existing: bool
) -> StageDecisionResult:
    decision_path = out_dir / "strategy_stage_decision.json"
    report_path = out_dir / "strategy_stage_decision.md"
    if not replace_existing and (decision_path.exists() or report_path.exists()):
        raise StrategyStageOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(decision_path, decision.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_stage_decision_markdown(decision))
    return StageDecisionResult(
        decision=decision, decision_path=decision_path, report_path=report_path
    )


def _source_artifact(artifact_key: str, path: Path) -> StageSourceArtifact:
    return StageSourceArtifact(
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


def _load_operator_review(review_dir: Path) -> tuple[OperatorStrategyReview | None, Path | None]:
    path = review_dir / "operator_review.yaml"
    if not path.exists():
        return None, None
    payload = read_mapping_file(path)
    return OperatorStrategyReview.model_validate(payload), path


def _load_paper_status(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return read_json_object(path)


def _selected_thresholds(
    policy: StrategyStagePolicy, stage: StageName, selected_profile: str
) -> StageThresholds:
    thresholds = policy.stages[stage]
    if selected_profile == "default":
        return thresholds
    profile = policy.strategy_profiles.get(selected_profile)
    if profile is None:
        raise StrategyStageError(f"unknown strategy profile: {selected_profile}")
    return profile.get(stage, thresholds)


def _count_gap_observed(status: dict[str, Any], field_name: str) -> int:
    gaps = status.get("latest_normal_requirement_gaps")
    if not isinstance(gaps, dict):
        return 0
    field = gaps.get(field_name)
    if not isinstance(field, dict):
        return 0
    observed = field.get("observed")
    return observed if isinstance(observed, int) else 0


def _paper_requirement_gap(status: dict[str, Any], field_name: str) -> StagePaperRequirementGap:
    gaps = status.get("latest_normal_requirement_gaps")
    field = gaps.get(field_name) if isinstance(gaps, dict) else None
    if not isinstance(field, dict):
        return StagePaperRequirementGap(observed=0, required=0, remaining=0, met=False)
    observed = field.get("observed")
    required = field.get("required")
    remaining = field.get("remaining")
    met = field.get("met")
    return StagePaperRequirementGap(
        observed=observed if isinstance(observed, int) else 0,
        required=required if isinstance(required, int) else 0,
        remaining=remaining if isinstance(remaining, int) else 0,
        met=met is True,
    )


def _paper_evidence_summary(status: dict[str, Any] | None) -> StagePaperEvidenceSummary:
    if status is None:
        return StagePaperEvidenceSummary(paper_status_present=False)
    latest_normal_session_id = status.get("latest_normal_session_id")
    return StagePaperEvidenceSummary(
        paper_status_present=True,
        smoke_pass_present=status.get("smoke_pass_present")
        if isinstance(status.get("smoke_pass_present"), bool)
        else None,
        smoke_pass_counts_as_normal_pass=status.get("smoke_pass_counts_as_normal_pass")
        if isinstance(status.get("smoke_pass_counts_as_normal_pass"), bool)
        else None,
        normal_thresholds_met=status.get("normal_thresholds_met")
        if isinstance(status.get("normal_thresholds_met"), bool)
        else None,
        latest_normal_session_id=latest_normal_session_id
        if isinstance(latest_normal_session_id, str)
        else None,
        normal_fills=_paper_requirement_gap(status, "fills"),
        normal_trading_days=_paper_requirement_gap(status, "trading_days"),
    )


def _paper_smoke_conditions(operator_review: OperatorStrategyReview | None) -> list[StageCondition]:
    if operator_review is None:
        return [
            _condition(
                "operator_review_present",
                False,
                "missing",
                "operator_review.yaml with PAPER_OBSERVATION_CANDIDATE",
            )
        ]
    source = operator_review.source_review
    return [
        _condition(
            "operator_decision_candidate",
            operator_review.decision.value == "PAPER_OBSERVATION_CANDIDATE",
            operator_review.decision.value,
            "PAPER_OBSERVATION_CANDIDATE",
        ),
        _condition(
            "operator_live_allowed_false",
            operator_review.live_allowed is False,
            operator_review.live_allowed,
            False,
        ),
        _condition(
            "operator_paper_execution_allowed_false",
            operator_review.paper_execution_allowed is False,
            operator_review.paper_execution_allowed,
            False,
        ),
        _condition(
            "source_review_status",
            source.review_status.value == "READY_FOR_HUMAN_REVIEW",
            source.review_status.value,
            "READY_FOR_HUMAN_REVIEW",
        ),
        _condition(
            "source_safety_status",
            source.source_safety_status.value == "PASS",
            source.source_safety_status.value,
            "PASS",
        ),
        _condition(
            "source_blocking_counts",
            source.missing_required_count
            + source.invalid_required_count
            + source.boundary_violation_count
            + source.unknown_boundary_count
            == 0,
            source.missing_required_count
            + source.invalid_required_count
            + source.boundary_violation_count
            + source.unknown_boundary_count,
            0,
        ),
    ]


def _paper_status_conditions(
    *,
    stage: StageName,
    status: dict[str, Any] | None,
    thresholds: StageThresholds,
) -> list[StageCondition]:
    if status is None:
        return [
            _condition(
                "paper_observation_status_present",
                False,
                "missing",
                "strategy_paper_observation_status.v1",
            )
        ]
    if stage is StageName.NORMAL_PAPER_OBSERVATION:
        return [
            _condition(
                "smoke_pass_present",
                status.get("smoke_pass_present") is True,
                status.get("smoke_pass_present"),
                True,
            ),
            _condition(
                "smoke_pass_counts_as_normal_pass",
                status.get("smoke_pass_counts_as_normal_pass") is False,
                status.get("smoke_pass_counts_as_normal_pass"),
                False,
            ),
        ]
    if stage is StageName.DRIFT_REVIEW:
        min_fills = thresholds.min_fills or 0
        min_days = thresholds.min_trading_days or 0
        fills = _count_gap_observed(status, "fills")
        days = _count_gap_observed(status, "trading_days")
        return [
            _condition(
                "normal_thresholds_met",
                status.get("normal_thresholds_met") is True,
                status.get("normal_thresholds_met"),
                True,
            ),
            _condition("normal_fills_for_policy", fills >= min_fills, fills, min_fills),
            _condition("normal_trading_days_for_policy", days >= min_days, days, min_days),
        ]
    if stage is StageName.MICRO_LIVE_PLAN:
        return [
            _condition(
                "normal_thresholds_met",
                status.get("normal_thresholds_met") is True,
                status.get("normal_thresholds_met"),
                True,
            ),
            _condition(
                "live_conversion_allowed_false",
                status.get("live_conversion_allowed") is False,
                status.get("live_conversion_allowed"),
                False,
            ),
            _condition(
                "wallet_used_false",
                status.get("wallet_used") is False,
                status.get("wallet_used"),
                False,
            ),
            _condition(
                "signing_used_false",
                status.get("signing_used") is False,
                status.get("signing_used"),
                False,
            ),
            _condition(
                "exchange_write_used_false",
                status.get("exchange_write_used") is False,
                status.get("exchange_write_used"),
                False,
            ),
        ]
    return []


def _decision_for_stage(
    stage: StageName, failed_conditions: list[StageCondition]
) -> StageDecisionStatus:
    if failed_conditions:
        return StageDecisionStatus.NEEDS_EVIDENCE
    if stage is StageName.PAPER_SMOKE:
        return StageDecisionStatus.READY_FOR_PAPER_SMOKE_PLAN
    if stage is StageName.NORMAL_PAPER_OBSERVATION:
        return StageDecisionStatus.READY_FOR_NORMAL_PAPER_OBSERVATION
    if stage is StageName.DRIFT_REVIEW:
        return StageDecisionStatus.READY_FOR_DRIFT_REVIEW
    return StageDecisionStatus.READY_FOR_MICRO_LIVE_PLAN


def build_stage_decision(
    *,
    strategy_id: str,
    stage: StageName,
    policy_path: Path,
    out_dir: Path,
    selected_profile: str = "default",
    review_dir: Path | None = None,
    paper_observation_status_path: Path | None = None,
    reviewer: str | None = None,
    override_reason: str | None = None,
    manual_overrides: list[str] | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StageDecisionResult:
    policy = _read_policy(policy_path)
    policy_hash = sha256_file(policy_path)
    thresholds = _selected_thresholds(policy, stage, selected_profile)

    source_artifacts = [_source_artifact("stage_policy", policy_path)]
    operator_review = None
    if review_dir is not None:
        operator_review, operator_review_path = _load_operator_review(review_dir)
        if operator_review_path is not None:
            source_artifacts.append(_source_artifact("operator_review", operator_review_path))
    paper_status = _load_paper_status(paper_observation_status_path)
    if paper_observation_status_path is not None and paper_observation_status_path.exists():
        source_artifacts.append(
            _source_artifact("paper_observation_status", paper_observation_status_path)
        )

    if stage is StageName.PAPER_SMOKE:
        conditions = _paper_smoke_conditions(operator_review)
        paper_evidence_summary = None
    else:
        conditions = _paper_status_conditions(
            stage=stage, status=paper_status, thresholds=thresholds
        )
        paper_evidence_summary = _paper_evidence_summary(paper_status)

    manual_override_values = manual_overrides or []
    if manual_override_values:
        conditions.append(
            _condition(
                "manual_override_reason_present",
                bool(override_reason),
                "present" if override_reason else "missing",
                "override_reason",
            )
        )

    failed_conditions = [condition for condition in conditions if not condition.passed]
    passed_conditions = [condition for condition in conditions if condition.passed]
    decision_status = _decision_for_stage(stage, failed_conditions)
    if boundary_true_paths(policy.model_dump(mode="json")):
        decision_status = StageDecisionStatus.BLOCKED

    decision = StrategyStageDecision(
        strategy_id=strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-stage-decision"),
        policy_id=policy.policy_id,
        policy_hash=policy_hash,
        selected_stage=stage,
        selected_profile=selected_profile,
        decision=decision_status,
        source_artifacts=source_artifacts,
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=[],
        manual_overrides=manual_override_values,
        paper_evidence_summary=paper_evidence_summary,
        override_reason=override_reason,
        reviewer=reviewer,
    )
    return _write_stage_decision(
        out_dir=out_dir, decision=decision, replace_existing=replace_existing
    )
