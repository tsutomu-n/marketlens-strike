from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout
from .test_strategy_review_build import _write_required_artifacts


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
