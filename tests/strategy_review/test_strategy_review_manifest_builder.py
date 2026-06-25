from __future__ import annotations

from pathlib import Path

from sis.strategy_review.manifest import SourceArtifact, SourceArtifactStatus
from sis.strategy_review.manifest_builder import build_strategy_review_manifest


SHA256_A = "sha256:" + "a" * 64
SHA256_B = "sha256:" + "b" * 64


def _present_artifact(
    artifact_key: str,
    *,
    required: bool = True,
    summary: dict | None = None,
) -> SourceArtifact:
    return SourceArtifact(
        artifact_key=artifact_key,
        path=f"data/research/{artifact_key}.json",
        exists=True,
        required=required,
        status=SourceArtifactStatus.PRESENT,
        sha256=SHA256_A if artifact_key == "pack" else SHA256_B,
        bytes=123,
        summary=summary or {},
    )


def _missing_artifact(artifact_key: str, *, required: bool = True) -> SourceArtifact:
    return SourceArtifact(
        artifact_key=artifact_key,
        path=f"data/research/{artifact_key}.json",
        exists=False,
        required=required,
        status=SourceArtifactStatus.MISSING,
        summary={},
    )


def _invalid_artifact(artifact_key: str, *, required: bool = True) -> SourceArtifact:
    return SourceArtifact(
        artifact_key=artifact_key,
        path=f"data/research/{artifact_key}.json",
        exists=True,
        required=required,
        status=SourceArtifactStatus.INVALID,
        sha256=SHA256_B,
        bytes=123,
        error="invalid json",
        summary={},
    )


def _blocked_artifact(
    artifact_key: str,
    *,
    required: bool = True,
    summary: dict | None = None,
) -> SourceArtifact:
    return SourceArtifact(
        artifact_key=artifact_key,
        path=f"data/research/{artifact_key}.json",
        exists=True,
        required=required,
        status=SourceArtifactStatus.BLOCKED,
        sha256=SHA256_B,
        bytes=123,
        error="source boundary violation: wallet_used",
        summary=summary or {},
    )


def _manifest(
    tmp_path: Path,
    source_artifacts: list[SourceArtifact],
):
    return build_strategy_review_manifest(
        review_id="ndx-smoke-001",
        created_at="2026-06-16T09:00:00Z",
        strict=False,
        review_dir=tmp_path / "data/strategy_reviews/ndx-smoke-001",
        review_markdown_path=tmp_path / "data/strategy_reviews/ndx-smoke-001/review.md",
        manifest_path=tmp_path / "data/strategy_reviews/ndx-smoke-001/review_manifest.json",
        source_artifacts=source_artifacts,
    )


def test_build_strategy_review_manifest_ready_with_pack_validation_status(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    manifest = _manifest(
        tmp_path,
        [
            _present_artifact("pack"),
            _present_artifact("pack_validation", summary={"decision": "PASS"}),
        ],
    )

    assert manifest.review_status.value == "READY_FOR_HUMAN_REVIEW"
    assert manifest.source_safety.status.value == "PASS"
    assert manifest.evaluation_flags.pack_validation_status == "PASS"
    assert manifest.summary.missing_required_count == 0
    assert manifest.summary.invalid_required_count == 0
    assert manifest.paths.review_dir == "data/strategy_reviews/ndx-smoke-001"


def test_build_strategy_review_manifest_missing_required_is_incomplete_unknown(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    manifest = _manifest(
        tmp_path,
        [_present_artifact("pack"), _missing_artifact("pack_validation")],
    )

    assert manifest.review_status.value == "INCOMPLETE_ARTIFACTS"
    assert manifest.source_safety.status.value == "UNKNOWN"
    assert manifest.source_safety.unknown_boundary_count == 1
    assert manifest.summary.missing_required_count == 1
    assert manifest.summary.invalid_required_count == 0


def test_build_strategy_review_manifest_invalid_required_is_invalid_unknown(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    manifest = _manifest(
        tmp_path,
        [_present_artifact("pack"), _invalid_artifact("pack_validation")],
    )

    assert manifest.review_status.value == "INVALID_INPUT"
    assert manifest.source_safety.status.value == "UNKNOWN"
    assert manifest.source_safety.unknown_boundary_count == 1
    assert manifest.summary.missing_required_count == 0
    assert manifest.summary.invalid_required_count == 1


def test_build_strategy_review_manifest_boundary_violation_blocks_and_merges_flags(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    manifest = _manifest(
        tmp_path,
        [
            _present_artifact("pack"),
            _blocked_artifact(
                "pack_validation",
                summary={
                    "boundary_violations": ["wallet_used", "venue_write_used"],
                    "observed_boundary_flags": {
                        "wallet_used": True,
                        "venue_write_used": True,
                    },
                },
            ),
        ],
    )

    assert manifest.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert manifest.source_safety.status.value == "BLOCKED"
    assert manifest.source_safety.boundary_violation_count == 2
    assert manifest.summary.boundary_violation_count == 2
    assert manifest.source_safety.observed_flags.wallet_used is True
    assert manifest.source_safety.observed_flags.venue_write_used is True
