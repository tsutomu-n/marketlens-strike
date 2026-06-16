from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_review.service import (
    StrategyReviewOutputExistsError,
    build_strategy_review,
)


CREATED_AT = "2026-06-16T09:00:00Z"


def _manifest_schema() -> dict:
    return json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas/strategy_review_manifest.v1.schema.json"
        ).read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_required_artifacts(root: Path, *, wallet_used: bool = False) -> tuple[Path, Path]:
    pack_path = root / "data/research/backtest_pack/strategy_backtest_pack.json"
    validation_path = root / "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    _write_json(
        pack_path,
        {
            "schema_version": "strategy_backtest_pack.v1",
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": wallet_used,
            "exchange_write_used": False,
            "summary": {"suite_run_count": 1, "suite_method_count": 1},
            "external_framework_policy": {
                "policy_id": "native_primary_external_evaluation_only.v1",
                "standard_engine": "strategy_authoring_native",
                "decision": "complete_without_locked_external_dependency",
                "locked_dependency_added": False,
                "external_adapters_required_for_completion": False,
            },
            "artifacts": {},
        },
    )
    _write_json(
        validation_path,
        {
            "schema_version": "strategy_backtest_pack_validation.v1",
            "decision": "PASS",
            "paper_only": True,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "summary": {
                "check_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "locked_dependency_added": False,
            },
        },
    )
    return pack_path, validation_path


def test_build_strategy_review_writes_markdown_and_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="ndx-smoke-001",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.review_markdown_path.exists()
    assert result.manifest_path.exists()
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["review_status"] == "READY_FOR_HUMAN_REVIEW"
    assert payload["evaluation_flags"]["pack_validation_status"] == "PASS"
    assert payload["evaluation_flags"]["pack_validation_pass_is_readiness_proof"] is False
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert pack["path"] == "data/research/backtest_pack/strategy_backtest_pack.json"
    assert pack["sha256"].startswith("sha256:")
    assert len(pack["sha256"]) == len("sha256:") + 64


def test_build_strategy_review_missing_required_artifact_is_incomplete(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json"
    validation_path = (
        tmp_path / "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    )

    result = build_strategy_review(
        review_id="missing-pack",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        strict=False,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INCOMPLETE_ARTIFACTS"
    assert result.manifest.summary.missing_required_count == 2
    assert result.review_markdown_path.exists()
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_manifest_schema()).validate(payload)
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert "sha256" not in pack


def test_build_strategy_review_detects_boundary_violation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path, wallet_used=True)

    result = build_strategy_review(
        review_id="blocked-wallet",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert result.manifest.summary.boundary_violation_count == 1


def test_build_strategy_review_invalid_required_json_is_invalid_input(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    pack_path.write_text("{not-json", encoding="utf-8")

    result = build_strategy_review(
        review_id="invalid-pack",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INVALID_INPUT"
    assert result.manifest.summary.invalid_required_count == 1
    pack = next(
        artifact for artifact in result.manifest.source_artifacts if artifact.artifact_key == "pack"
    )
    validation = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "pack_validation"
    )
    assert pack.exists is True
    assert pack.status.value == "invalid"
    assert "error" in pack.summary
    assert validation.status.value == "present"
    assert "error" not in validation.summary
    assert "summary_unavailable_due_to" in validation.summary
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_manifest_schema()).validate(payload)


def test_build_strategy_review_refuses_existing_output_without_replace(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    kwargs = {
        "review_id": "same-id",
        "out_dir": tmp_path / "data/strategy_reviews",
        "pack_path": pack_path,
        "validation_path": validation_path,
        "created_at": CREATED_AT,
    }
    build_strategy_review(**kwargs)

    try:
        build_strategy_review(**kwargs)
    except StrategyReviewOutputExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing output error")
