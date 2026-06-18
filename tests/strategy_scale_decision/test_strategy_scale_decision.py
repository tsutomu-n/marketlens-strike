from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_scale_decision.models import ScaleDecisionPolicy
from sis.strategy_scale_decision.service import build_strategy_scale_decision


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_scale_decision.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _live_observation(
    tmp_path: Path,
    *,
    ingest_status: str = "LIVE_OBSERVATION_INGESTED",
    rejection: bool = False,
    max_loss_breach: bool = False,
    actual_fill: bool = False,
    cancel_observed: bool = True,
) -> Path:
    return _write_json(
        tmp_path / "data/strategy_live_observations/ndx-breakout-001/live.json",
        {
            "schema_version": "strategy_live_observation_manifest.v1",
            "strategy_id": "ndx-breakout-001",
            "observation_id": "ndx-breakout-001-live-observation",
            "created_at": "2026-06-19T03:00:00Z",
            "ingest_status": ingest_status,
            "summary": {
                "canary_status": "completed_canceled_open_order",
                "blocked_reasons": [],
                "actual_fill_observed": actual_fill,
                "rejection_observed": rejection,
                "cancel_observed": cancel_observed,
                "close_submitted": False,
                "max_loss_breach_observed": max_loss_breach,
            },
            "scale_up_allowed": False,
            "live_allowed": False,
        },
    )


def _micro_live_plan(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_micro_live_plans/ndx-breakout-001/plan.json",
        {
            "schema_version": "strategy_micro_live_plan.v1",
            "strategy_id": "ndx-breakout-001",
            "plan_id": "ndx-breakout-001-micro-live-plan",
            "plan_status": "READY_FOR_HUMAN_MICRO_LIVE_REVIEW",
            "micro_live_execution_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )


def test_scale_decision_builds_ready_schema_valid_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_scale_decision(
        strategy_id="ndx-breakout-001",
        live_observation_path=_live_observation(tmp_path),
        micro_live_plan_path=_micro_live_plan(tmp_path),
        out_dir=tmp_path / "data/strategy_scale_decisions",
    )

    assert result.decision.decision_status == "READY_FOR_HUMAN_SCALE_REVIEW"
    assert result.decision.recommended_action == "PREPARE_NEXT_SCALE_PLAN"
    assert result.decision.next_scale_plan_allowed is False
    assert result.decision.scale_up_execution_allowed is False
    assert result.decision.live_allowed is False

    payload = json.loads(result.decision_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["next_scale_plan_allowed"] is False
    report = result.report_path.read_text(encoding="utf-8")
    assert "Strategy Scale Decision" in report
    assert "not scale-up execution permission" in report


def test_scale_decision_requires_live_observation_ingested(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_scale_decision(
        strategy_id="ndx-breakout-001",
        live_observation_path=_live_observation(tmp_path, ingest_status="BLOCKED_CANARY"),
        out_dir=tmp_path / "data/strategy_scale_decisions",
    )

    assert result.decision.decision_status == "REVISE_OR_RETIRE"
    assert result.decision.recommended_action == "HOLD_AT_MICRO_LIVE"


def test_scale_decision_revises_on_rejection_or_loss_breach(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_scale_decision(
        strategy_id="ndx-breakout-001",
        live_observation_path=_live_observation(
            tmp_path,
            rejection=True,
            max_loss_breach=True,
        ),
        out_dir=tmp_path / "data/strategy_scale_decisions",
    )

    assert result.decision.decision_status == "REVISE_OR_RETIRE"
    assert result.decision.recommended_action == "REVISE_STRATEGY"
    assert {"no_rejection_observed", "no_max_loss_breach"} <= {
        condition.condition_id for condition in result.decision.failed_conditions
    }


def test_scale_decision_can_require_actual_fill(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_scale_decision(
        strategy_id="ndx-breakout-001",
        live_observation_path=_live_observation(tmp_path, actual_fill=False),
        out_dir=tmp_path / "data/strategy_scale_decisions",
        policy=ScaleDecisionPolicy(require_actual_fill=True),
    )

    assert result.decision.decision_status == "NEEDS_REPAIR"
    assert "actual_fill_requirement" in {
        condition.condition_id for condition in result.decision.failed_conditions
    }
