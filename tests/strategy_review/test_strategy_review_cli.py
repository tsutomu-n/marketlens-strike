from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from sis.cli import app
from support.cli import invoke_cli
from support.cli import normalized_stdout
from .test_strategy_review_build import (
    CREATED_AT,
    _write_lifecycle_review,
    _write_required_artifacts,
)
from sis.strategy_review.service import build_strategy_review


runner = CliRunner()


def test_strategy_review_build_help() -> None:
    result = runner.invoke(app, ["strategy-review-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--review-id" in stdout
    assert "--out" in stdout
    assert "--strict" in stdout
    assert "--no-strict" in stdout
    assert "--pack-path" in stdout
    assert "--validation-path" in stdout
    assert "--authoring-spec" in stdout
    assert "--lifecycle-review" in stdout
    assert "--authoring-spec-path" not in stdout
    assert "--lifecycle-review-path" not in stdout
    assert "--replace-existing" in stdout


def test_strategy_review_build_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "cli-smoke",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
            "--pack-path",
            str(pack_path),
            "--validation-path",
            str(validation_path),
        ],
    )

    assert result.exit_code == 0
    assert "review_status=READY_FOR_HUMAN_REVIEW" in result.stdout
    assert "review_dir=data/strategy_reviews/cli-smoke" in result.stdout
    assert "manifest_path=data/strategy_reviews/cli-smoke/review_manifest.json" in result.stdout
    assert "markdown_path=data/strategy_reviews/cli-smoke/review.md" in result.stdout
    assert "missing_required_count=0" in result.stdout
    assert "invalid_required_count=0" in result.stdout
    assert "boundary_violation_count=0" in result.stdout
    manifest_path = tmp_path / "data/strategy_reviews/cli-smoke/review_manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["review_status"] == (
        "READY_FOR_HUMAN_REVIEW"
    )


def test_strategy_review_build_cli_lenient_missing_exits_zero(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "missing-lenient",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
            "--pack-path",
            str(tmp_path / "missing-pack.json"),
            "--validation-path",
            str(tmp_path / "missing-validation.json"),
        ],
    )

    assert result.exit_code == 0
    assert "review_status=INCOMPLETE_ARTIFACTS" in result.stdout
    assert (tmp_path / "data/strategy_reviews/missing-lenient/review.md").exists()


def test_strategy_review_build_cli_strict_missing_writes_then_exits_two(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "missing-strict",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
            "--pack-path",
            str(tmp_path / "missing-pack.json"),
            "--validation-path",
            str(tmp_path / "missing-validation.json"),
            "--strict",
        ],
    )

    assert result.exit_code == 2
    assert "review_status=INCOMPLETE_ARTIFACTS" in result.stdout
    assert (tmp_path / "data/strategy_reviews/missing-strict/review_manifest.json").exists()


def test_strategy_review_build_cli_rejects_bad_review_id(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "../bad",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
        ],
    )

    assert result.exit_code == 2
    assert "review_id" in result.stdout


def test_strategy_review_build_cli_invalid_json_exits_two_with_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    pack_path.write_text("{not-json", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "invalid-json",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
            "--pack-path",
            str(pack_path),
            "--validation-path",
            str(validation_path),
        ],
    )

    assert result.exit_code == 2
    assert "review_status=INVALID_INPUT" in result.stdout
    manifest_path = tmp_path / "data/strategy_reviews/invalid-json/review_manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["review_status"] == (
        "INVALID_INPUT"
    )


def test_strategy_review_build_cli_boundary_violation_exits_two_with_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path, wallet_used=True)

    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "blocked-wallet",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
            "--pack-path",
            str(pack_path),
            "--validation-path",
            str(validation_path),
        ],
    )

    assert result.exit_code == 2
    assert "review_status=BLOCKED_BOUNDARY_VIOLATION" in result.stdout
    manifest_path = tmp_path / "data/strategy_reviews/blocked-wallet/review_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert pack["status"] == "blocked"
    assert pack["error"] == "source boundary violation: wallet_used"


def test_strategy_review_build_cli_rejects_secret_path_without_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    secret_path = tmp_path / "data/secrets/pack.json"
    secret_path.parent.mkdir(parents=True)
    secret_path.write_text("{}\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "strategy-review-build",
            "--review-id",
            "secret-path",
            "--out",
            str(tmp_path / "data/strategy_reviews"),
            "--pack-path",
            str(secret_path),
            "--validation-path",
            str(tmp_path / "missing-validation.json"),
        ],
    )

    assert result.exit_code == 2
    assert "secret path segments" in result.stdout
    assert not (tmp_path / "data/strategy_reviews/secret-path/review_manifest.json").exists()


def _build_cli_record_review(tmp_path: Path) -> Path:
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    lifecycle_path = tmp_path / "data/research/strategy_lifecycle/strategy_lifecycle_review.json"
    _write_lifecycle_review(lifecycle_path)
    result = build_strategy_review(
        review_id="cli-record",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )
    return result.manifest_path.parent


def test_strategy_review_record_help() -> None:
    result = invoke_cli(["strategy-review-record", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--review-dir" in stdout
    assert "--decision" in stdout
    assert "--reviewer" in stdout
    assert "--rationale" in stdout
    assert "--required-action" in stdout
    assert "--replace-existing" in stdout
    assert "--validate-existing" in stdout


def test_strategy_review_record_cli_writes_and_validates_existing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_cli_record_review(tmp_path)

    result = runner.invoke(
        app,
        [
            "strategy-review-record",
            "--review-dir",
            str(review_dir),
            "--decision",
            "PAPER_OBSERVATION_CANDIDATE",
            "--reviewer",
            "operator-a",
            "--rationale",
            "Complete review packet with clean boundaries.",
        ],
    )

    assert result.exit_code == 0
    assert "status=pass" in result.stdout
    assert "operator_review_path=" in result.stdout
    assert "decision=PAPER_OBSERVATION_CANDIDATE" in result.stdout
    payload = yaml.safe_load((review_dir / "operator_review.yaml").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "operator_strategy_review.v1"

    validate_result = runner.invoke(
        app,
        [
            "strategy-review-record",
            "--review-dir",
            str(review_dir),
            "--validate-existing",
        ],
    )
    assert validate_result.exit_code == 0
    assert "status=pass" in validate_result.stdout


def test_strategy_review_record_cli_existing_output_without_replace_exits_two(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_cli_record_review(tmp_path)
    (review_dir / "operator_review.yaml").write_text("keep: true\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "strategy-review-record",
            "--review-dir",
            str(review_dir),
            "--decision",
            "REVIEWED_FOR_CONTEXT",
            "--reviewer",
            "operator-a",
            "--rationale",
            "Context only.",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "already exists" in result.stdout
    assert (review_dir / "operator_review.yaml").read_text(encoding="utf-8") == "keep: true\n"


def test_strategy_review_record_cli_validate_existing_detects_stale_review(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    review_dir = _build_cli_record_review(tmp_path)
    create_result = runner.invoke(
        app,
        [
            "strategy-review-record",
            "--review-dir",
            str(review_dir),
            "--decision",
            "REVIEWED_FOR_CONTEXT",
            "--reviewer",
            "operator-a",
            "--rationale",
            "Context only.",
        ],
    )
    assert create_result.exit_code == 0
    (review_dir / "review.md").write_text("changed\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "strategy-review-record",
            "--review-dir",
            str(review_dir),
            "--validate-existing",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "review markdown hash mismatch" in result.stdout
