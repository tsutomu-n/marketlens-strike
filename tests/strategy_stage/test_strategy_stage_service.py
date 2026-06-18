from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

from sis.strategy_stage.models import StageName
from sis.strategy_stage.service import build_stage_decision, validate_stage_policy

from .test_strategy_stage_policy_schema import valid_stage_policy_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
CREATED_AT = "2026-06-18T12:45:00Z"


def _write_yaml(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _decision_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_stage_decision.v1.schema.json").read_text(encoding="utf-8")
    )


def _validation_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_stage_policy_validation.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_policy(tmp_path: Path) -> Path:
    return _write_yaml(
        tmp_path / "configs/strategy_stage_policies/default.yaml", valid_stage_policy_payload()
    )


def _valid_operator_review_payload() -> dict:
    return {
        "schema_version": "operator_strategy_review.v1",
        "review_id": "ndx-review-001",
        "reviewed_at": CREATED_AT,
        "producer": {
            "tool": "sis",
            "command": "strategy-review-record",
            "schema_version": "operator_strategy_review.v1",
        },
        "reviewer": "operator-a",
        "decision": "PAPER_OBSERVATION_CANDIDATE",
        "rationale": "Clean review packet.",
        "required_actions": [],
        "live_allowed": False,
        "paper_execution_allowed": False,
        "source_review": {
            "manifest_path": "data/strategy_reviews/ndx-review-001/review_manifest.json",
            "review_manifest_sha256": "sha256:" + "a" * 64,
            "review_markdown_path": "data/strategy_reviews/ndx-review-001/review.md",
            "review_markdown_sha256": "sha256:" + "b" * 64,
            "review_status": "READY_FOR_HUMAN_REVIEW",
            "source_safety_status": "PASS",
            "pack_validation_status": "PASS",
            "lifecycle_review_status": "present",
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "boundary_violation_count": 0,
            "unknown_boundary_count": 0,
        },
    }


def _write_operator_review(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "data/strategy_reviews/ndx-review-001/operator_review.yaml"
    return _write_yaml(path, payload or _valid_operator_review_payload())


def _paper_status_payload(*, normal_thresholds_met: bool = True) -> dict:
    return {
        "schema_version": "strategy_paper_observation_status.v1",
        "status_id": "sha256:" + "c" * 64,
        "generated_at": CREATED_AT,
        "latest_normal_session_id": "normal-session-001",
        "normal_thresholds_met": normal_thresholds_met,
        "smoke_pass_present": True,
        "smoke_pass_counts_as_normal_pass": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "latest_normal_requirement_gaps": {
            "fills": {"observed": 20, "required": 20, "remaining": 0, "met": True},
            "trading_days": {"observed": 10, "required": 10, "remaining": 0, "met": True},
        },
    }


def _write_paper_status(tmp_path: Path, payload: dict | None = None) -> Path:
    path = tmp_path / "data/research/strategy_lifecycle/paper_observation_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload or _paper_status_payload(), sort_keys=True), encoding="utf-8"
    )
    return path


def test_validate_stage_policy_writes_schema_valid_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)

    result = validate_stage_policy(
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_policies/default",
    )

    assert result.validation.validation_status.value == "PASS"
    payload = json.loads(result.validation_path.read_text(encoding="utf-8"))
    Draft202012Validator(_validation_schema()).validate(payload)
    assert result.report_path.exists()


def test_stage_decision_ready_for_paper_smoke_plan(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    operator_review_path = _write_operator_review(tmp_path)

    result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=StageName.PAPER_SMOKE,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-paper-smoke",
        review_dir=operator_review_path.parent,
        created_at=None,
    )

    assert result.decision.decision.value == "READY_FOR_PAPER_SMOKE_PLAN"
    assert result.decision.paper_execution_allowed is False
    assert result.decision.live_allowed is False
    payload = json.loads(result.decision_path.read_text(encoding="utf-8"))
    Draft202012Validator(_decision_schema()).validate(payload)
    assert any(row["artifact_key"] == "operator_review" for row in payload["source_artifacts"])


def test_stage_decision_missing_operator_review_needs_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)

    result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=StageName.PAPER_SMOKE,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-paper-smoke",
        review_dir=tmp_path / "data/strategy_reviews/ndx-review-001",
    )

    assert result.decision.decision.value == "NEEDS_EVIDENCE"
    assert result.decision.failed_conditions[0].condition_id == "operator_review_present"


def test_stage_decision_ready_for_drift_review_from_normal_status(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    status_path = _write_paper_status(tmp_path)

    result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=StageName.DRIFT_REVIEW,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-drift",
        paper_observation_status_path=status_path,
    )

    assert result.decision.decision.value == "READY_FOR_DRIFT_REVIEW"
    assert not result.decision.failed_conditions
    assert result.decision.paper_evidence_summary is not None
    assert result.decision.paper_evidence_summary.smoke_pass_present is True
    assert result.decision.paper_evidence_summary.smoke_pass_counts_as_normal_pass is False
    assert result.decision.paper_evidence_summary.normal_thresholds_met is True
    assert result.decision.paper_evidence_summary.normal_fills is not None
    assert result.decision.paper_evidence_summary.normal_fills.observed == 20


def test_stage_decision_smoke_pass_does_not_satisfy_normal_paper_gap(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    status_path = _write_paper_status(
        tmp_path,
        {
            **_paper_status_payload(normal_thresholds_met=False),
            "latest_normal_requirement_gaps": {
                "fills": {"observed": 0, "required": 20, "remaining": 20, "met": False},
                "trading_days": {"observed": 0, "required": 10, "remaining": 10, "met": False},
            },
        },
    )

    result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=StageName.DRIFT_REVIEW,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-drift",
        paper_observation_status_path=status_path,
    )

    failed_ids = {condition.condition_id for condition in result.decision.failed_conditions}
    assert result.decision.decision.value == "NEEDS_EVIDENCE"
    assert "normal_thresholds_met" in failed_ids
    assert "normal_fills_for_policy" in failed_ids
    assert "normal_trading_days_for_policy" in failed_ids
    assert result.decision.paper_evidence_summary is not None
    assert result.decision.paper_evidence_summary.smoke_pass_present is True
    assert result.decision.paper_evidence_summary.smoke_pass_counts_as_normal_pass is False
    assert result.decision.paper_evidence_summary.normal_thresholds_met is False
    assert result.decision.paper_evidence_summary.normal_fills is not None
    assert result.decision.paper_evidence_summary.normal_fills.remaining == 20
    assert result.decision.paper_evidence_summary.normal_trading_days is not None
    assert result.decision.paper_evidence_summary.normal_trading_days.remaining == 10

    payload = json.loads(result.decision_path.read_text(encoding="utf-8"))
    Draft202012Validator(_decision_schema()).validate(payload)
    assert payload["paper_evidence_summary"]["normal_fills"]["remaining"] == 20
    report = result.report_path.read_text(encoding="utf-8")
    assert "## Paper Evidence Summary" in report
    assert "normal_fills" in report
