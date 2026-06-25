from __future__ import annotations

import json
from pathlib import Path

from sis.strategy_review.source_artifacts import (
    artifact_from_path_after_summary_error,
    artifact_from_summary,
    invalid_optional_artifact,
    missing_optional_artifact,
    present_optional_artifact,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_artifact_from_summary_blocks_boundary_violations(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json"
    _write_json(
        pack_path,
        {
            "schema_version": "strategy_backtest_pack.v1",
            "wallet_used": True,
            "exchange_write_used": False,
        },
    )

    artifact = artifact_from_summary(
        "pack",
        {
            "path": str(pack_path),
            "exists": True,
            "summary": {"suite_run_count": 1},
        },
    )

    assert artifact.required is True
    assert artifact.status.value == "blocked"
    assert artifact.error == "source boundary violation: wallet_used"
    assert artifact.summary["observed_boundary_flags"]["wallet_used"] is True
    assert artifact.summary["boundary_violations"] == ["wallet_used"]


def test_artifact_from_path_after_summary_error_preserves_source_error_context(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    validation_path = (
        tmp_path / "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    )
    _write_json(
        validation_path,
        {
            "schema_version": "strategy_backtest_pack_validation.v1",
            "decision": "PASS",
            "permits_live_order": False,
        },
    )

    artifact = artifact_from_path_after_summary_error(
        "pack_validation",
        validation_path,
        error=ValueError("summary unavailable"),
    )

    assert artifact.required is True
    assert artifact.status.value == "present"
    assert artifact.summary["summary_unavailable_due_to"] == "summary unavailable"
    assert artifact.summary["observed_boundary_flags"]["permits_live_order"] is False


def test_artifact_from_path_after_summary_error_blocks_boundary_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json"
    _write_json(pack_path, {"schema_version": "strategy_backtest_pack.v1", "wallet_used": True})

    artifact = artifact_from_path_after_summary_error(
        "pack",
        pack_path,
        error=ValueError("summary failed"),
    )

    assert artifact.status.value == "blocked"
    assert artifact.error == "source boundary violation: wallet_used"
    assert artifact.summary["summary_unavailable_due_to"] == "summary failed"
    assert artifact.summary["boundary_violations"] == ["wallet_used"]


def test_optional_artifact_helpers_classify_missing_invalid_and_present(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    missing = missing_optional_artifact("strategy_idea", tmp_path / "missing.yaml")
    assert missing.required is False
    assert missing.status.value == "missing"

    invalid_path = tmp_path / "configs/strategy_ideas/invalid.yaml"
    invalid_path.parent.mkdir(parents=True)
    invalid_path.write_text("schema_version: wrong\n", encoding="utf-8")
    invalid = invalid_optional_artifact("strategy_idea", invalid_path, "bad schema")
    assert invalid.required is False
    assert invalid.status.value == "invalid"
    assert invalid.error == "bad schema"
    assert invalid.summary["error"] == "bad schema"

    present_path = tmp_path / "configs/strategy_ideas/valid.json"
    _write_json(present_path, {"schema_version": "strategy_idea.v1", "wallet_used": False})
    present = present_optional_artifact(
        "strategy_idea",
        present_path,
        {"idea_id": "idea-1"},
        payload={"wallet_used": False},
    )
    assert present.required is False
    assert present.status.value == "present"
    assert present.summary["idea_id"] == "idea-1"
    assert present.summary["observed_boundary_flags"]["wallet_used"] is False


def test_present_optional_artifact_blocks_nested_boundary_flags(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "configs/strategy_ideas/blocked.json"
    _write_json(
        path, {"schema_version": "strategy_idea.v1", "boundary": {"venue_write_used": True}}
    )

    artifact = present_optional_artifact(
        "strategy_idea",
        path,
        {"idea_id": "idea-2"},
        payload={"boundary": {"venue_write_used": True}},
    )

    assert artifact.status.value == "blocked"
    assert artifact.error == "source boundary violation: boundary.venue_write_used"
    assert artifact.summary["boundary_violations"] == ["boundary.venue_write_used"]
    assert artifact.summary["observed_boundary_flags"]["venue_write_used"] is True
