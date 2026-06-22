from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_case_lite.models import (
    StrategyCaseArtifactType,
    StrategyCaseLite,
    StrategyCaseLiteSummary,
    StrategyCaseSourceArtifact,
    StrategyCaseTimelineEntry,
)
from sis.strategy_case_lite.rendering import render_strategy_case_lite_markdown
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class StrategyCaseLiteResult:
    case: StrategyCaseLite
    case_path: Path
    report_path: Path


class StrategyCaseLiteError(ValueError):
    pass


class StrategyCaseLiteOutputExistsError(StrategyCaseLiteError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(
    artifact_type: StrategyCaseArtifactType, path: Path
) -> StrategyCaseSourceArtifact:
    return StrategyCaseSourceArtifact(
        artifact_type=artifact_type,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _artifact_type_for(schema_version: str | None) -> StrategyCaseArtifactType:
    return {
        "strategy_stage_decision.v1": StrategyCaseArtifactType.STAGE_DECISION,
        "strategy_runtime_observation_manifest.v1": StrategyCaseArtifactType.RUNTIME_OBSERVATION,
        "paper_vs_backtest_drift_review.v1": StrategyCaseArtifactType.DRIFT_REVIEW,
        "strategy_learning_event.v1": StrategyCaseArtifactType.LEARNING_EVENT,
        "strategy_revision_request.v1": StrategyCaseArtifactType.REVISION_REQUEST,
        "strategy_authoring_update_handoff.v1": StrategyCaseArtifactType.AUTHORING_UPDATE_HANDOFF,
        "strategy_micro_live_plan.v1": StrategyCaseArtifactType.MICRO_LIVE_PLAN,
        "strategy_live_observation_manifest.v1": StrategyCaseArtifactType.LIVE_OBSERVATION,
        "strategy_scale_decision.v1": StrategyCaseArtifactType.SCALE_DECISION,
        "strategy_next_scale_plan.v1": StrategyCaseArtifactType.NEXT_SCALE_PLAN,
        "strategy_input_contract_validation.v1": StrategyCaseArtifactType.INPUT_CONTRACT_VALIDATION,
        "strategy_authoring_backtest_result.v1": StrategyCaseArtifactType.AUTHORING_BACKTEST_RESULT,
        "strategy_backtest_pack.v1": StrategyCaseArtifactType.BACKTEST_PACK,
        "strategy_backtest_pack_validation.v1": StrategyCaseArtifactType.BACKTEST_PACK_VALIDATION,
        "strategy_backtest_suite_result.v1": StrategyCaseArtifactType.BACKTEST_SUITE_RESULT,
        "strategy_backtest_comparison.v1": StrategyCaseArtifactType.BACKTEST_COMPARISON,
        "strategy_review_manifest.v1": StrategyCaseArtifactType.STRATEGY_REVIEW_MANIFEST,
    }.get(schema_version or "", StrategyCaseArtifactType.GENERIC)


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _blocked_reasons(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for condition in payload.get("failed_conditions", []):
        if isinstance(condition, dict):
            condition_id = condition.get("condition_id")
            if isinstance(condition_id, str) and condition_id:
                reasons.append(condition_id)
    for path in boundary_true_paths(payload):
        reasons.append(f"boundary:{path}")
    return sorted(set(reasons))


def _timeline_entry(path: Path) -> StrategyCaseTimelineEntry:
    payload = read_json_object(path)
    schema_version = payload.get("schema_version")
    schema_text = schema_version if isinstance(schema_version, str) else None
    artifact_type = _artifact_type_for(schema_text)
    return StrategyCaseTimelineEntry(
        artifact_type=artifact_type,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=schema_text,
        event_time=_first_string(
            payload, ("created_at", "updated_at", "generated_at", "reviewed_at")
        ),
        status=_first_string(
            payload,
            (
                "decision",
                "status",
                "review_status",
                "ingest_status",
                "event_type",
                "request_status",
                "handoff_status",
                "plan_status",
                "decision_status",
                "validation_status",
            ),
        ),
        action=_first_string(payload, ("recommended_action", "next_action", "request_status")),
        blocked_reasons=_blocked_reasons(payload),
    )


def _sorted_timeline(entries: list[StrategyCaseTimelineEntry]) -> list[StrategyCaseTimelineEntry]:
    return sorted(entries, key=lambda entry: (entry.event_time or "", entry.path))


def _summary(entries: list[StrategyCaseTimelineEntry]) -> StrategyCaseLiteSummary:
    latest = entries[-1] if entries else None
    open_actions = sorted({entry.action for entry in entries if entry.action})
    blocked_reasons = sorted({reason for entry in entries for reason in entry.blocked_reasons})
    latest_hashes: dict[str, str] = {}
    for entry in entries:
        latest_hashes[entry.artifact_type.value] = entry.sha256
    return StrategyCaseLiteSummary(
        artifact_count=len(entries),
        timeline_count=len(entries),
        latest_status=latest.status if latest is not None else None,
        open_actions=open_actions,
        blocked_reasons=blocked_reasons,
        latest_source_hashes=latest_hashes,
    )


def build_strategy_case_lite(
    *,
    strategy_id: str,
    artifact_paths: list[Path],
    out_dir: Path,
    case_id: str | None = None,
    replace_existing: bool = False,
    updated_at: datetime | None = None,
) -> StrategyCaseLiteResult:
    if not artifact_paths:
        raise StrategyCaseLiteError("at least one source artifact is required")
    missing = [path for path in artifact_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"source artifact missing: {missing[0]}")

    timeline = _sorted_timeline([_timeline_entry(path) for path in artifact_paths])
    source_artifacts = [
        _source_artifact(entry.artifact_type, Path(entry.path)) for entry in timeline
    ]
    selected_case_id = case_id or strategy_id
    case = StrategyCaseLite(
        strategy_id=strategy_id,
        case_id=selected_case_id,
        updated_at=updated_at or _utc_now(),
        producer=StageProducer(command="strategy-case-lite-update"),
        source_artifacts=source_artifacts,
        timeline=timeline,
        summary=_summary(timeline),
    )

    case_dir = out_dir / strategy_id
    case_path = case_dir / "strategy_case_lite.json"
    report_path = case_dir / "strategy_case_lite.md"
    if not replace_existing and (case_path.exists() or report_path.exists()):
        raise StrategyCaseLiteOutputExistsError(
            f"output already exists: {repo_relative_path(case_dir)}"
        )
    write_json_artifact(case_path, case.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_strategy_case_lite_markdown(case))
    return StrategyCaseLiteResult(case=case, case_path=case_path, report_path=report_path)
