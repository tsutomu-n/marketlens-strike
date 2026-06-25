from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
from sis.strategy_review.path_manifest_helpers import (
    created_at_value,
    derive_authoring_spec_path,
    manifest_json_payload,
    summary_paths,
)


def test_created_at_value_preserves_strings_and_normalizes_datetimes() -> None:
    assert created_at_value("2026-06-16T09:00:00Z") == "2026-06-16T09:00:00Z"
    assert created_at_value(datetime(2026, 6, 16, 9, 0, 1, 123456)) == ("2026-06-16T09:00:01Z")
    assert (
        created_at_value(datetime(2026, 6, 16, 18, 0, tzinfo=timezone(timedelta(hours=9))))
        == "2026-06-16T09:00:00Z"
    )


def test_summary_paths_use_research_sibling_framework_run_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json"
    validation_path = (
        tmp_path / "data/research/backtest_pack_validation/strategy_backtest_pack_validation.json"
    )

    paths = summary_paths(pack_path, validation_path)

    assert paths["pack_path"] == pack_path
    assert paths["validation_path"] == validation_path
    assert paths["framework_run_path"] == (
        tmp_path / "data/research/backtest_framework_run/strategy_backtest_framework_run.json"
    )
    assert paths["stress_path"] == (
        tmp_path / "data/research/backtest_stress/strategy_backtest_stress.json"
    )


def test_summary_paths_use_pack_sibling_framework_run_path_for_non_default_layout(
    tmp_path: Path,
) -> None:
    pack_path = tmp_path / "custom/backtest_pack/strategy_backtest_pack.json"
    validation_path = tmp_path / "custom/validation.json"

    paths = summary_paths(pack_path, validation_path)

    assert paths["framework_run_path"] == (
        tmp_path / "custom/backtest_pack/strategy_backtest_framework_run.json"
    )


def test_derive_authoring_spec_path_from_pack_spec_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json"
    pack_path.parent.mkdir(parents=True)
    pack_path.write_text(
        json.dumps({"spec_path": "configs/strategy_authoring/spec.yaml"}),
        encoding="utf-8",
    )

    assert derive_authoring_spec_path(pack_path) == (
        tmp_path / "configs/strategy_authoring/spec.yaml"
    )

    absolute_spec = tmp_path / "absolute/spec.yaml"
    pack_path.write_text(json.dumps({"spec_path": absolute_spec.as_posix()}), encoding="utf-8")
    assert derive_authoring_spec_path(pack_path) == absolute_spec


def test_derive_authoring_spec_path_returns_none_for_missing_or_invalid_pack(
    tmp_path: Path,
) -> None:
    missing_pack = tmp_path / "missing.json"
    assert derive_authoring_spec_path(missing_pack) is None

    invalid_pack = tmp_path / "invalid.json"
    invalid_pack.write_text("{not json", encoding="utf-8")
    assert derive_authoring_spec_path(invalid_pack) is None

    empty_pack = tmp_path / "empty-spec.json"
    empty_pack.write_text(json.dumps({"spec_path": "  "}), encoding="utf-8")
    assert derive_authoring_spec_path(empty_pack) is None


def test_manifest_json_payload_omits_nullable_artifact_fields() -> None:
    manifest = StrategyReviewManifest(
        review_id="ndx-smoke-001",
        created_at="2026-06-16T09:00:00Z",
        review_status=ReviewStatus.READY_FOR_HUMAN_REVIEW,
        strict=False,
        paths=ReviewPaths(
            review_dir="data/strategy_reviews/ndx-smoke-001",
            review_markdown_path="data/strategy_reviews/ndx-smoke-001/review.md",
            manifest_path="data/strategy_reviews/ndx-smoke-001/review_manifest.json",
        ),
        source_artifacts=[
            SourceArtifact(
                artifact_key="optional_missing",
                path="data/optional.json",
                exists=False,
                required=False,
                status=SourceArtifactStatus.MISSING,
                summary={},
            )
        ],
        builder_safety=BuilderSafety(),
        source_safety=SourceSafety(
            status=SourceSafetyStatus.PASS,
            boundary_violation_count=0,
            unknown_boundary_count=0,
            observed_flags=SourceSafetyFlags(),
        ),
        evaluation_flags=EvaluationFlags(),
        summary=ReviewSummary(
            missing_required_count=0,
            invalid_required_count=0,
            boundary_violation_count=0,
            unknown_boundary_count=0,
        ),
    )

    payload = manifest_json_payload(manifest)

    artifact = payload["source_artifacts"][0]
    assert "sha256" not in artifact
    assert "bytes" not in artifact
    assert "detected_schema_version" not in artifact
    assert "error" not in artifact
