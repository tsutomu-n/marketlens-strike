from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shlex
from typing import Any

from pydantic import ValidationError

from sis.backtest.artifact_io import sha256_file
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_paper_smoke.models import (
    PaperSmokeExecutionPreview,
    PaperSmokePlanStatus,
    PaperSmokeSourceArtifact,
    PaperSmokeThresholds,
    StrategyPaperSmokePlan,
)
from sis.strategy_paper_smoke.rendering import render_paper_smoke_plan_markdown
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
    StageThresholds,
    StrategyStageDecision,
    StrategyStagePolicy,
)


@dataclass(frozen=True)
class PaperSmokePlanResult:
    plan: StrategyPaperSmokePlan
    plan_path: Path
    report_path: Path


class StrategyPaperSmokeError(ValueError):
    pass


class StrategyPaperSmokeOutputExistsError(StrategyPaperSmokeError):
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


def _source_artifact(artifact_key: str, path: Path, *, required: bool) -> PaperSmokeSourceArtifact:
    exists = path.exists()
    return PaperSmokeSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        exists=exists,
        required=required,
        sha256=sha256_file(path) if exists else None,
        schema_version=detect_json_schema_version(path) if exists else None,
    )


def _read_stage_decision(stage_decision_path: Path) -> StrategyStageDecision:
    try:
        return StrategyStageDecision.model_validate(read_mapping_file(stage_decision_path))
    except (ValidationError, ValueError) as exc:
        raise StrategyPaperSmokeError(f"invalid stage decision: {exc}") from exc


def _read_policy(policy_path: Path) -> StrategyStagePolicy:
    payload = read_mapping_file(policy_path)
    violations = boundary_true_paths(payload)
    if violations:
        raise StrategyPaperSmokeError("policy boundary violation: " + ", ".join(violations))
    try:
        return StrategyStagePolicy.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise StrategyPaperSmokeError(f"invalid stage policy: {exc}") from exc


def _selected_thresholds(
    policy: StrategyStagePolicy, stage: StageName, selected_profile: str
) -> StageThresholds:
    thresholds = policy.stages[stage]
    if selected_profile == "default":
        return thresholds
    profile = policy.strategy_profiles.get(selected_profile)
    if profile is None:
        raise StrategyPaperSmokeError(f"unknown strategy profile: {selected_profile}")
    return profile.get(stage, thresholds)


def _paper_smoke_thresholds(thresholds: StageThresholds) -> PaperSmokeThresholds:
    return PaperSmokeThresholds(
        min_fills_for_pass=max(thresholds.min_fills or 1, 1),
        min_trading_days_for_pass=max(thresholds.min_trading_days or 1, 1),
        max_blocked_rate=thresholds.max_blocked_rate
        if thresholds.max_blocked_rate is not None
        else 0.5,
        max_consecutive_blocked=thresholds.max_consecutive_blocked
        if thresholds.max_consecutive_blocked is not None
        else 3,
        max_open_position_age_hours=0.0,
        max_order_notional_usd=thresholds.max_order_notional_usd,
        max_position_notional_usd=thresholds.max_position_notional_usd,
        max_orders_per_day=thresholds.max_orders_per_day,
        stop_after_consecutive_errors=thresholds.stop_after_consecutive_errors,
    )


def _command_preview(
    *,
    data_dir: Path,
    artifact_dir: Path,
    reports_dir: Path,
    session_id: str,
    backtest_acceptance_path: Path,
    source_pack_path: Path,
    promotion_decision_path: Path,
    operator_promotion_path: Path,
    thresholds: PaperSmokeThresholds,
    paper_notional_usd: float,
) -> str:
    parts = [
        "uv",
        "run",
        "sis",
        "strategy-paper-observation-cycle",
        "--data-dir",
        data_dir.as_posix(),
        "--artifact-dir",
        artifact_dir.as_posix(),
        "--reports-dir",
        reports_dir.as_posix(),
        "--session-id",
        session_id,
        "--backtest-acceptance-path",
        backtest_acceptance_path.as_posix(),
        "--source-pack",
        source_pack_path.as_posix(),
        "--promotion-decision",
        promotion_decision_path.as_posix(),
        "--operator-promotion-path",
        operator_promotion_path.as_posix(),
        "--min-fills-for-pass",
        str(thresholds.min_fills_for_pass),
        "--min-trading-days-for-pass",
        str(thresholds.min_trading_days_for_pass),
        "--max-blocked-rate",
        str(thresholds.max_blocked_rate),
        "--max-consecutive-blocked",
        str(thresholds.max_consecutive_blocked),
        "--max-open-position-age-hours",
        str(thresholds.max_open_position_age_hours),
        "--paper-notional-usd",
        str(paper_notional_usd),
        "--smoke",
    ]
    return " ".join(shlex.quote(part) for part in parts)


def _status_for(
    *,
    boundary_failed: bool,
    stage_failed: bool,
    source_failed: bool,
) -> PaperSmokePlanStatus:
    if boundary_failed:
        return PaperSmokePlanStatus.BLOCKED_BOUNDARY_VIOLATION
    if stage_failed:
        return PaperSmokePlanStatus.NEEDS_STAGE_APPROVAL
    if source_failed:
        return PaperSmokePlanStatus.NEEDS_SOURCE_ARTIFACTS
    return PaperSmokePlanStatus.READY_TO_RUN_SMOKE_CYCLE


def build_paper_smoke_plan(
    *,
    stage_decision_path: Path,
    policy_path: Path,
    out_dir: Path,
    data_dir: Path,
    artifact_dir: Path,
    reports_dir: Path,
    session_id: str,
    backtest_acceptance_path: Path,
    source_pack_path: Path,
    promotion_decision_path: Path,
    operator_promotion_path: Path,
    paper_notional_usd: float = 1000.0,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> PaperSmokePlanResult:
    stage_decision = _read_stage_decision(stage_decision_path)
    policy = _read_policy(policy_path)
    selected_thresholds = _selected_thresholds(
        policy, StageName.PAPER_SMOKE, stage_decision.selected_profile
    )
    thresholds = _paper_smoke_thresholds(selected_thresholds)
    policy_hash = sha256_file(policy_path)

    source_artifacts = [
        _source_artifact("stage_decision", stage_decision_path, required=True),
        _source_artifact("stage_policy", policy_path, required=True),
        _source_artifact("backtest_acceptance", backtest_acceptance_path, required=True),
        _source_artifact("paper_candidate_pack", source_pack_path, required=True),
        _source_artifact("promotion_decision", promotion_decision_path, required=True),
        _source_artifact("operator_promotion", operator_promotion_path, required=True),
    ]

    conditions = [
        _condition(
            "stage_is_paper_smoke",
            stage_decision.selected_stage is StageName.PAPER_SMOKE,
            stage_decision.selected_stage.value,
            StageName.PAPER_SMOKE.value,
        ),
        _condition(
            "stage_decision_ready",
            stage_decision.decision is StageDecisionStatus.READY_FOR_PAPER_SMOKE_PLAN,
            stage_decision.decision.value,
            StageDecisionStatus.READY_FOR_PAPER_SMOKE_PLAN.value,
        ),
        _condition(
            "stage_paper_execution_allowed_false",
            stage_decision.paper_execution_allowed is False,
            stage_decision.paper_execution_allowed,
            False,
        ),
        _condition(
            "stage_live_allowed_false",
            stage_decision.live_allowed is False,
            stage_decision.live_allowed,
            False,
        ),
        _condition(
            "policy_hash_matches_stage",
            policy_hash == stage_decision.policy_hash,
            policy_hash,
            stage_decision.policy_hash,
        ),
    ]
    for artifact in source_artifacts:
        conditions.append(
            _condition(
                f"{artifact.artifact_key}_present",
                artifact.exists,
                "present" if artifact.exists else "missing",
                "present",
            )
        )

    boundary_violations = [
        *boundary_true_paths(stage_decision.model_dump(mode="json")),
        *boundary_true_paths(policy.model_dump(mode="json")),
    ]
    if boundary_violations:
        conditions.append(
            _condition(
                "no_boundary_violation",
                False,
                ", ".join(boundary_violations),
                "no true live/wallet/signing/write flags",
            )
        )

    failed_conditions = [condition for condition in conditions if not condition.passed]
    passed_conditions = [condition for condition in conditions if condition.passed]
    stage_failed = any(
        condition.condition_id
        in {
            "stage_is_paper_smoke",
            "stage_decision_ready",
            "stage_paper_execution_allowed_false",
            "stage_live_allowed_false",
            "policy_hash_matches_stage",
        }
        for condition in failed_conditions
    )
    source_failed = any(
        condition.condition_id.endswith("_present") for condition in failed_conditions
    )
    plan_status = _status_for(
        boundary_failed=bool(boundary_violations),
        stage_failed=stage_failed,
        source_failed=source_failed,
    )

    plan = StrategyPaperSmokePlan(
        strategy_id=stage_decision.strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-paper-smoke-plan"),
        plan_status=plan_status,
        source_artifacts=source_artifacts,
        thresholds=thresholds,
        execution_preview=PaperSmokeExecutionPreview(
            command=_command_preview(
                data_dir=data_dir,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                session_id=session_id,
                backtest_acceptance_path=backtest_acceptance_path,
                source_pack_path=source_pack_path,
                promotion_decision_path=promotion_decision_path,
                operator_promotion_path=operator_promotion_path,
                thresholds=thresholds,
                paper_notional_usd=paper_notional_usd,
            )
        ),
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=[],
    )

    plan_path = out_dir / "strategy_paper_smoke_plan.json"
    report_path = out_dir / "strategy_paper_smoke_plan.md"
    if not replace_existing and (plan_path.exists() or report_path.exists()):
        raise StrategyPaperSmokeOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(plan_path, plan.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_paper_smoke_plan_markdown(plan))
    return PaperSmokePlanResult(plan=plan, plan_path=plan_path, report_path=report_path)
