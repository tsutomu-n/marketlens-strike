from __future__ import annotations

import json
from pathlib import Path

from sis.strategy_review.lifecycle_summary import lifecycle_review_summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _lifecycle_payload(**overrides) -> dict:
    payload = {
        "schema_version": "strategy_lifecycle_review.v1",
        "decision": "CONTINUE_PAPER_OBSERVATION",
        "decision_reasons": ["PAPER_OBSERVATION_INSUFFICIENT"],
        "next_actions": ["Continue paper observation until thresholds are met."],
        "input_status": {
            "backtest_acceptance_present": True,
            "paper_review_present": True,
            "phase_gate_present": True,
        },
        "blocker_counts": {"P2_BLOCKER": 0, "LIVE_READINESS_BLOCKER": 1},
        "permits_live_order": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    payload.update(overrides)
    return payload


def test_lifecycle_review_summary_reports_missing_optional_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "missing-lifecycle.json"

    artifact, section = lifecycle_review_summary(path)

    assert artifact.artifact_key == "lifecycle_review"
    assert artifact.required is False
    assert artifact.status.value == "missing"
    assert section.section_id == "lifecycle_summary"
    assert section.status == "missing"
    assert "missing-lifecycle.json" in section.markdown


def test_lifecycle_review_summary_rejects_wrong_schema_version(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "lifecycle.json"
    _write_json(path, {"schema_version": "wrong"})

    artifact, section = lifecycle_review_summary(path)

    assert artifact.status.value == "invalid"
    assert artifact.error == "schema_version must be strategy_lifecycle_review.v1"
    assert artifact.summary["error"] == "schema_version must be strategy_lifecycle_review.v1"
    assert section.status == "invalid"
    assert "schema_version must be strategy_lifecycle_review.v1" in section.markdown


def test_lifecycle_review_summary_rejects_malformed_list_and_object_fields(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    bad_list_path = tmp_path / "bad-list.json"
    _write_json(bad_list_path, _lifecycle_payload(decision_reasons="not-a-list"))

    artifact, section = lifecycle_review_summary(bad_list_path)

    assert artifact.status.value == "invalid"
    assert "decision_reasons must be a list of strings" in artifact.summary["error"]
    assert "decision_reasons must be a list of strings" in section.markdown

    bad_object_path = tmp_path / "bad-object.json"
    _write_json(bad_object_path, _lifecycle_payload(input_status=[]))

    artifact, section = lifecycle_review_summary(bad_object_path)

    assert artifact.status.value == "invalid"
    assert "input_status must be an object" in artifact.summary["error"]
    assert "input_status must be an object" in section.markdown


def test_lifecycle_review_summary_builds_present_artifact_and_section(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "lifecycle.json"
    _write_json(path, _lifecycle_payload())

    artifact, section = lifecycle_review_summary(path)

    assert artifact.status.value == "present"
    assert artifact.summary["decision"] == "CONTINUE_PAPER_OBSERVATION"
    assert artifact.summary["decision_reasons"] == ["PAPER_OBSERVATION_INSUFFICIENT"]
    assert artifact.summary["next_actions"] == [
        "Continue paper observation until thresholds are met."
    ]
    assert artifact.summary["observed_boundary_flags"]["venue_write_used"] is False
    assert section.status == "present"
    assert "decision: `CONTINUE_PAPER_OBSERVATION`" in section.markdown
    assert "wallet_used: `false`" in section.markdown


def test_lifecycle_review_summary_blocks_boundary_violations(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "lifecycle.json"
    _write_json(path, _lifecycle_payload(venue_write_used=True))

    artifact, section = lifecycle_review_summary(path)

    assert artifact.status.value == "blocked"
    assert artifact.error == "source boundary violation: venue_write_used"
    assert artifact.summary["boundary_violations"] == ["venue_write_used"]
    assert artifact.summary["observed_boundary_flags"]["venue_write_used"] is True
    assert section.status == "present"
    assert "venue_write_used: `true`" in section.markdown
