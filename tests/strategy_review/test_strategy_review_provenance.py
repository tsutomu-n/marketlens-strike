from __future__ import annotations

import json
from pathlib import Path

import pytest

from sis.strategy_review.provenance import (
    boundary_true_paths,
    build_source_artifact,
    compute_sha256_prefixed,
    observed_boundary_flags,
    repo_relative_posix_path,
    validate_review_id,
)


def test_validate_review_id_rejects_path_segments() -> None:
    assert validate_review_id("review_001-ok") == "review_001-ok"
    for review_id in ("", "../x", "/tmp/x", ".hidden", "a/b", r"a\b"):
        with pytest.raises(ValueError):
            validate_review_id(review_id)


def test_repo_relative_posix_path_rejects_unsafe_paths(tmp_path: Path) -> None:
    inside = tmp_path / "data/reviews/review.md"
    inside.parent.mkdir(parents=True)
    inside.write_text("ok\n", encoding="utf-8")

    assert repo_relative_posix_path(inside, repo_root=tmp_path) == "data/reviews/review.md"

    with pytest.raises(ValueError):
        repo_relative_posix_path(tmp_path / "../outside.json", repo_root=tmp_path)
    with pytest.raises(ValueError):
        repo_relative_posix_path(Path(r"data\bad.json"), repo_root=tmp_path)
    with pytest.raises(ValueError):
        repo_relative_posix_path(Path("/tmp/outside.json"), repo_root=tmp_path)


def test_build_source_artifact_hashes_existing_and_omits_missing_hash(tmp_path: Path) -> None:
    artifact_path = tmp_path / "data/source.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")

    present = build_source_artifact(
        artifact_key="source",
        path=artifact_path,
        required=True,
        repo_root=tmp_path,
    )
    assert present.path == "data/source.json"
    assert present.sha256 == compute_sha256_prefixed(artifact_path)
    assert present.sha256 is not None
    assert present.sha256.startswith("sha256:")
    assert len(present.sha256) == len("sha256:") + 64

    missing = build_source_artifact(
        artifact_key="missing",
        path=tmp_path / "data/missing.json",
        required=False,
        repo_root=tmp_path,
    )
    assert missing.status.value == "missing"
    assert missing.sha256 is None


def test_boundary_flag_extraction_detects_nested_true_flags() -> None:
    payload = {
        "permits_live_order": False,
        "nested": [
            {"wallet_used": True},
            {"venue_write_used": True},
            {"exchange_write_used": False},
        ],
        "signing_used": True,
    }

    assert boundary_true_paths(payload) == [
        "nested[0].wallet_used",
        "nested[1].venue_write_used",
        "signing_used",
    ]
    observed = observed_boundary_flags(payload)
    assert observed["wallet_used"] is True
    assert observed["venue_write_used"] is True
    assert observed["signing_used"] is True
    assert observed["exchange_write_used"] is False
