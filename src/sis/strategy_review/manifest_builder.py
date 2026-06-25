from __future__ import annotations

from pathlib import Path

from sis.strategy_review.manifest import (
    BuilderSafety,
    EvaluationFlags,
    ReviewPaths,
    ReviewStatus,
    ReviewSummary,
    SourceArtifact,
    SourceArtifactStatus,
    SourceSafety,
    SourceSafetyFlags,
    SourceSafetyStatus,
    StrategyReviewManifest,
)
from sis.strategy_review.provenance import repo_relative_path


def build_strategy_review_manifest(
    *,
    review_id: str,
    created_at: str,
    strict: bool,
    review_dir: Path,
    review_markdown_path: Path,
    manifest_path: Path,
    source_artifacts: list[SourceArtifact],
) -> StrategyReviewManifest:
    missing_required_count = sum(
        1
        for artifact in source_artifacts
        if artifact.required and artifact.status is SourceArtifactStatus.MISSING
    )
    invalid_required_count = sum(
        1
        for artifact in source_artifacts
        if artifact.required and artifact.status is SourceArtifactStatus.INVALID
    )
    boundary_violation_count = sum(
        len(artifact.summary.get("boundary_violations", [])) for artifact in source_artifacts
    )
    invalid_artifact_count = sum(
        1 for artifact in source_artifacts if artifact.status is SourceArtifactStatus.INVALID
    )
    unknown_boundary_count = sum(
        1
        for artifact in source_artifacts
        if artifact.required
        and artifact.status in {SourceArtifactStatus.MISSING, SourceArtifactStatus.INVALID}
    )
    observed_flags = dict.fromkeys(
        (
            "permits_live_order",
            "live_conversion_allowed",
            "wallet_used",
            "signing_used",
            "exchange_write_used",
            "venue_write_used",
        ),
        False,
    )
    for artifact in source_artifacts:
        for key, value in artifact.summary.get("observed_boundary_flags", {}).items():
            if key in observed_flags:
                observed_flags[key] = bool(observed_flags[key] or value)

    if boundary_violation_count:
        review_status = ReviewStatus.BLOCKED_BOUNDARY_VIOLATION
        source_safety_status = SourceSafetyStatus.BLOCKED
    elif invalid_artifact_count:
        review_status = ReviewStatus.INVALID_INPUT
        source_safety_status = (
            SourceSafetyStatus.UNKNOWN if unknown_boundary_count else SourceSafetyStatus.PASS
        )
    elif missing_required_count:
        review_status = ReviewStatus.INCOMPLETE_ARTIFACTS
        source_safety_status = SourceSafetyStatus.UNKNOWN
    else:
        review_status = ReviewStatus.READY_FOR_HUMAN_REVIEW
        source_safety_status = SourceSafetyStatus.PASS

    pack_validation = next(
        (artifact for artifact in source_artifacts if artifact.artifact_key == "pack_validation"),
        None,
    )
    pack_validation_status = None
    if pack_validation is not None:
        value = pack_validation.summary.get("decision")
        pack_validation_status = str(value) if value is not None else None

    return StrategyReviewManifest(
        review_id=review_id,
        created_at=created_at,
        review_status=review_status,
        strict=strict,
        paths=ReviewPaths(
            review_dir=repo_relative_path(review_dir),
            review_markdown_path=repo_relative_path(review_markdown_path),
            manifest_path=repo_relative_path(manifest_path),
        ),
        source_artifacts=source_artifacts,
        builder_safety=BuilderSafety(),
        source_safety=SourceSafety(
            status=source_safety_status,
            boundary_violation_count=boundary_violation_count,
            unknown_boundary_count=unknown_boundary_count,
            observed_flags=SourceSafetyFlags(**observed_flags),
        ),
        evaluation_flags=EvaluationFlags(pack_validation_status=pack_validation_status),
        summary=ReviewSummary(
            missing_required_count=missing_required_count,
            invalid_required_count=invalid_required_count,
            boundary_violation_count=boundary_violation_count,
            unknown_boundary_count=unknown_boundary_count,
        ),
    )
