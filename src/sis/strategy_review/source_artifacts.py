from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sis.strategy_review.manifest import SourceArtifact, SourceArtifactStatus
from sis.strategy_review.provenance import (
    boundary_true_paths,
    collect_source_artifact,
    observed_boundary_flags,
    read_source_json,
)


REQUIRED_ARTIFACT_KEYS = {"pack", "pack_validation"}


def artifact_from_summary(artifact_key: str, row: dict[str, Any]) -> SourceArtifact:
    exists = row.get("exists") is True
    required = artifact_key in REQUIRED_ARTIFACT_KEYS
    path = Path(str(row.get("path", "")))
    summary = {key: value for key, value in row.items() if key not in {"path", "exists"}}
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        path=path,
        required=required,
        summary=summary,
    )
    if exists and artifact.status is SourceArtifactStatus.PRESENT:
        payload = read_source_json(path)
        artifact.summary["observed_boundary_flags"] = observed_boundary_flags(payload)
        violations = boundary_true_paths(payload)
        if violations:
            artifact.summary["boundary_violations"] = violations
            return artifact.model_copy(
                update={
                    "status": SourceArtifactStatus.BLOCKED,
                    "error": f"source boundary violation: {', '.join(violations)}",
                }
            )
    return artifact


def artifact_from_path_after_summary_error(
    artifact_key: str,
    path: Path,
    *,
    error: Exception,
) -> SourceArtifact:
    required = artifact_key in REQUIRED_ARTIFACT_KEYS
    exists = path.exists()
    if not exists:
        return collect_source_artifact(artifact_key=artifact_key, path=path, required=required)
    summary: dict[str, Any] = {}
    try:
        payload = read_source_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        artifact = collect_source_artifact(
            artifact_key=artifact_key,
            path=path,
            required=required,
            summary=summary,
        )
        if artifact.status is SourceArtifactStatus.INVALID:
            return artifact
        return artifact.model_copy(
            update={"status": SourceArtifactStatus.INVALID, "error": str(exc)}
        )

    violations = boundary_true_paths(payload)
    summary["observed_boundary_flags"] = observed_boundary_flags(payload)
    if violations:
        summary["boundary_violations"] = violations
    summary["summary_unavailable_due_to"] = str(error)
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        required=required,
        path=path,
        summary=summary,
    )
    if violations:
        return artifact.model_copy(
            update={
                "status": SourceArtifactStatus.BLOCKED,
                "error": f"source boundary violation: {', '.join(violations)}",
            }
        )
    return artifact


def missing_optional_artifact(artifact_key: str, path: Path) -> SourceArtifact:
    return collect_source_artifact(artifact_key=artifact_key, path=path, required=False)


def invalid_optional_artifact(
    artifact_key: str, path: Path, error: Exception | str
) -> SourceArtifact:
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        path=path,
        required=False,
        summary={"error": str(error)},
    )
    return artifact.model_copy(update={"status": SourceArtifactStatus.INVALID, "error": str(error)})


def present_optional_artifact(
    artifact_key: str,
    path: Path,
    summary: dict[str, Any],
    *,
    payload: Any,
) -> SourceArtifact:
    violations = boundary_true_paths(payload)
    summary["observed_boundary_flags"] = observed_boundary_flags(payload)
    if violations:
        summary = {**summary, "boundary_violations": violations}
    artifact = collect_source_artifact(
        artifact_key=artifact_key,
        required=False,
        path=path,
        summary=summary,
    )
    if violations:
        return artifact.model_copy(
            update={
                "status": SourceArtifactStatus.BLOCKED,
                "error": f"source boundary violation: {', '.join(violations)}",
            }
        )
    return artifact
