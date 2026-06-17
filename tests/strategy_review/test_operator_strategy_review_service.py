from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sis.strategy_review.operator_review import (
    OperatorReviewOutputExistsError,
    OperatorReviewRecordError,
    record_operator_review,
    validate_existing_operator_review,
)
from sis.strategy_review.service import build_strategy_review
from .test_strategy_review_build import (
    CREATED_AT,
    _write_lifecycle_review,
    _write_required_artifacts,
)


REVIEWED_AT = "2026-06-16T10:00:00Z"


def _build_ready_review(tmp_path: Path, *, lifecycle: bool = True) -> Path:
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    lifecycle_path = tmp_path / "data/research/strategy_lifecycle/strategy_lifecycle_review.json"
    if lifecycle:
        _write_lifecycle_review(lifecycle_path)
    result = build_strategy_review(
        review_id="operator-smoke",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )
    return result.manifest_path.parent


def test_record_operator_review_writes_yaml_and_validate_existing_passes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)

    result = record_operator_review(
        review_dir=review_dir,
        reviewer="operator-a",
        decision="PAPER_OBSERVATION_CANDIDATE",
        rationale="Complete review packet with clean boundaries.",
        reviewed_at=REVIEWED_AT,
    )

    assert result.operator_review_path == review_dir / "operator_review.yaml"
    payload = yaml.safe_load(result.operator_review_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "operator_strategy_review.v1"
    assert payload["reviewed_at"] == REVIEWED_AT
    assert payload["decision"] == "PAPER_OBSERVATION_CANDIDATE"
    assert payload["live_allowed"] is False
    assert payload["paper_execution_allowed"] is False
    assert payload["source_review"]["manifest_path"] == (
        "data/strategy_reviews/operator-smoke/review_manifest.json"
    )

    validated = validate_existing_operator_review(review_dir=review_dir)
    assert validated.operator_review.decision.value == "PAPER_OBSERVATION_CANDIDATE"


def test_record_operator_review_candidate_guard_failure_does_not_write(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path, lifecycle=False)

    with pytest.raises(ValidationError):
        record_operator_review(
            review_dir=review_dir,
            reviewer="operator-a",
            decision="PAPER_OBSERVATION_CANDIDATE",
            rationale="Trying to promote without lifecycle review.",
            reviewed_at=REVIEWED_AT,
        )

    assert not (review_dir / "operator_review.yaml").exists()


def test_record_operator_review_needs_fix_requires_action(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)

    with pytest.raises(ValidationError):
        record_operator_review(
            review_dir=review_dir,
            reviewer="operator-a",
            decision="NEEDS_FIX",
            rationale="Needs an action.",
            reviewed_at=REVIEWED_AT,
        )


def test_record_operator_review_refuses_existing_without_replace(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    record_operator_review(
        review_dir=review_dir,
        reviewer="operator-a",
        decision="REVIEWED_FOR_CONTEXT",
        rationale="Context only.",
        reviewed_at=REVIEWED_AT,
    )

    with pytest.raises(OperatorReviewOutputExistsError):
        record_operator_review(
            review_dir=review_dir,
            reviewer="operator-a",
            decision="REVIEWED_FOR_CONTEXT",
            rationale="Context only.",
            reviewed_at=REVIEWED_AT,
        )


def test_record_operator_review_replace_preserves_other_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    extra_path = review_dir / "operator-note.txt"
    extra_path.write_text("keep\n", encoding="utf-8")
    record_operator_review(
        review_dir=review_dir,
        reviewer="operator-a",
        decision="REVIEWED_FOR_CONTEXT",
        rationale="Context only.",
        reviewed_at=REVIEWED_AT,
    )

    record_operator_review(
        review_dir=review_dir,
        reviewer="operator-b",
        decision="NEEDS_FIX",
        rationale="Needs follow-up.",
        required_actions=["Explain residual diagnostics."],
        replace_existing=True,
        reviewed_at="2026-06-16T11:00:00Z",
    )

    payload = yaml.safe_load((review_dir / "operator_review.yaml").read_text(encoding="utf-8"))
    assert payload["reviewer"] == "operator-b"
    assert payload["required_actions"] == ["Explain residual diagnostics."]
    assert extra_path.read_text(encoding="utf-8") == "keep\n"


def test_validate_existing_detects_manifest_hash_stale(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    record_operator_review(
        review_dir=review_dir,
        reviewer="operator-a",
        decision="REVIEWED_FOR_CONTEXT",
        rationale="Context only.",
        reviewed_at=REVIEWED_AT,
    )
    manifest_path = review_dir / "review_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["strict"] = True
    manifest_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(OperatorReviewRecordError, match="review manifest hash mismatch"):
        validate_existing_operator_review(review_dir=review_dir)


def test_validate_existing_detects_review_markdown_hash_stale(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    record_operator_review(
        review_dir=review_dir,
        reviewer="operator-a",
        decision="REVIEWED_FOR_CONTEXT",
        rationale="Context only.",
        reviewed_at=REVIEWED_AT,
    )
    (review_dir / "review.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(OperatorReviewRecordError, match="review markdown hash mismatch"):
        validate_existing_operator_review(review_dir=review_dir)


def test_validate_existing_detects_path_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    record_operator_review(
        review_dir=review_dir,
        reviewer="operator-a",
        decision="REVIEWED_FOR_CONTEXT",
        rationale="Context only.",
        reviewed_at=REVIEWED_AT,
    )
    operator_path = review_dir / "operator_review.yaml"
    payload = yaml.safe_load(operator_path.read_text(encoding="utf-8"))
    payload["source_review"]["manifest_path"] = "data/strategy_reviews/other/review_manifest.json"
    operator_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(OperatorReviewRecordError, match="manifest path mismatch"):
        validate_existing_operator_review(review_dir=review_dir)


@pytest.mark.parametrize("filename", ["review_manifest.json", "review.md"])
def test_record_operator_review_requires_source_files(
    tmp_path: Path, monkeypatch, filename: str
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    (review_dir / filename).unlink()

    with pytest.raises(OperatorReviewRecordError):
        record_operator_review(
            review_dir=review_dir,
            reviewer="operator-a",
            decision="REVIEWED_FOR_CONTEXT",
            rationale="Context only.",
            reviewed_at=REVIEWED_AT,
        )


def test_validate_existing_rejects_invalid_existing_yaml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_ready_review(tmp_path)
    (review_dir / "operator_review.yaml").write_text("[not-object]\n", encoding="utf-8")

    with pytest.raises(OperatorReviewRecordError, match="must contain an object"):
        validate_existing_operator_review(review_dir=review_dir)
