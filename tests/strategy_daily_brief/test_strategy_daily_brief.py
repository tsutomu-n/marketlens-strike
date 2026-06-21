from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_daily_brief.service import build_strategy_daily_brief


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_daily_brief.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_fixtures(data_dir: Path) -> None:
    _write_json(
        data_dir / "strategy_stage_decisions/ready_for_drift.json",
        {
            "schema_version": "strategy_stage_decision.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T00:00:00Z",
            "decision": "READY_FOR_DRIFT_REVIEW",
            "failed_conditions": [],
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_stage_decisions/normal_gap.json",
        {
            "schema_version": "strategy_stage_decision.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T00:10:00Z",
            "decision": "NEEDS_EVIDENCE",
            "paper_evidence_summary": {
                "paper_status_present": True,
                "smoke_pass_present": True,
                "smoke_pass_counts_as_normal_pass": False,
                "normal_thresholds_met": False,
                "normal_fills": {"observed": 3, "required": 20, "remaining": 17, "met": False},
                "normal_trading_days": {
                    "observed": 1,
                    "required": 10,
                    "remaining": 9,
                    "met": False,
                },
            },
            "failed_conditions": [
                {
                    "condition_id": "normal_fills_for_policy",
                    "passed": False,
                    "observed": "3",
                    "required": "20",
                    "severity": "error",
                }
            ],
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_drift_reviews/drift.json",
        {
            "schema_version": "paper_vs_backtest_drift_review.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T01:00:00Z",
            "review_status": "READY_FOR_HUMAN_DRIFT_REVIEW",
            "recommended_action": "HUMAN_REVIEW_REQUIRED",
            "failed_conditions": [],
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_learning/revision_request.json",
        {
            "schema_version": "strategy_revision_request.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T01:10:00Z",
            "request_status": "READY_FOR_HUMAN_REVIEW",
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_runtime_observations/boundary.json",
        {
            "schema_version": "strategy_runtime_observation_manifest.v1",
            "strategy_id": "ndx-breakout-001",
            "generated_at": "2026-06-19T01:20:00Z",
            "ingest_status": "BLOCKED_BOUNDARY_VIOLATION",
            "wallet_used": True,
        },
    )
    _write_json(
        data_dir / "strategy_micro_live_plans/plan.json",
        {
            "schema_version": "strategy_micro_live_plan.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T02:00:00Z",
            "plan_status": "READY_FOR_HUMAN_MICRO_LIVE_REVIEW",
            "micro_live_execution_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_live_observations/live.json",
        {
            "schema_version": "strategy_live_observation_manifest.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T03:00:00Z",
            "ingest_status": "LIVE_OBSERVATION_INGESTED",
            "scale_up_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_scale_decisions/scale.json",
        {
            "schema_version": "strategy_scale_decision.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T04:00:00Z",
            "decision_status": "READY_FOR_HUMAN_SCALE_REVIEW",
            "recommended_action": "PREPARE_NEXT_SCALE_PLAN",
            "next_scale_plan_allowed": False,
            "scale_up_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "strategy_next_scale_plans/next_scale.json",
        {
            "schema_version": "strategy_next_scale_plan.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T05:00:00Z",
            "plan_status": "READY_FOR_HUMAN_NEXT_SCALE_REVIEW",
            "next_scale_execution_allowed": False,
            "live_allowed": False,
        },
    )
    _write_json(
        data_dir / "crypto_perp/tournament_gate/tournament_gate.json",
        {
            "schema_version": "crypto_perp_tournament_gate.v1",
            "gate_id": "crypto-perp-gate-001",
            "report_id": "crypto-perp-tournament-001",
            "created_at": "2026-06-19T06:00:00Z",
            "gate_status": "NEEDS_ACTUAL_CASH",
            "recommended_action": "REBUILD_WITH_ACTUAL_CASH",
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )
    _write_json(
        data_dir / "crypto_perp/truth_cycle_status/truth_cycle_status.json",
        {
            "schema_version": "crypto_perp_truth_cycle_status.v1",
            "cycle_status": "NEEDS_ACTUAL_CASH",
            "recommended_next_command": "REBUILD_WITH_ACTUAL_CASH",
            "next_steps": [
                {
                    "step_id": "rebuild_actual_cash_basis",
                    "purpose": "before-cost proxyではなくactual cash evidenceでrows/report/gateを作り直す。",
                    "command": "REBUILD_WITH_ACTUAL_CASH",
                    "requires_explicit_approval": False,
                    "network_allowed": False,
                    "exchange_write_allowed": False,
                    "live_order_allowed": False,
                }
            ],
            "stop_reasons": [
                "GATE_STATUS_NEEDS_ACTUAL_CASH",
                "GATE_FAILED_CONDITION_no_proxy_known_gap",
            ],
            "summary": {
                "cycle_status": "NEEDS_ACTUAL_CASH",
                "present_stage_count": 2,
                "missing_artifact_path_count": 0,
                "known_gap_count": 1,
                "stop_reason_count": 2,
            },
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )
    (data_dir / "broken").mkdir(parents=True, exist_ok=True)
    (data_dir / "broken/not_json.json").write_text("{", encoding="utf-8")


def test_strategy_daily_brief_builds_schema_valid_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    _write_fixtures(data_dir)

    result = build_strategy_daily_brief(
        data_dir=data_dir,
        out_dir=tmp_path / "data/reports/strategy_daily_brief",
    )

    categories = {item.category.value for item in result.brief.items}
    assert "broken_artifact" in categories
    assert "pending_human_review" in categories
    assert "crypto_perp_gate_follow_up" in categories
    assert "crypto_perp_truth_cycle_follow_up" in categories
    assert "normal_paper_gap" in categories
    assert "drift_review_needed" in categories
    assert "learning_request_pending" in categories
    assert "boundary_violation" in categories
    assert result.brief.summary.scanned_json_count == 12
    assert result.brief.summary.broken_artifact_count >= 1
    assert result.brief.summary.crypto_perp_gate_follow_up_count == 1
    assert result.brief.summary.crypto_perp_truth_cycle_follow_up_count == 1
    assert result.brief.summary.boundary_violation_count == 1
    assert result.brief.paper_execution_allowed is False
    assert result.brief.live_allowed is False

    payload = json.loads(result.brief_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    report = result.report_path.read_text(encoding="utf-8")
    assert "Strategy Daily Brief" in report
    assert "crypto_perp_truth_cycle_follow_up_count: `1`" in report
    assert "crypto_perp_gate_follow_up" in report
    assert "crypto_perp_truth_cycle_follow_up" in report
    assert "rebuild_actual_cash_basis" in report
    assert "before-cost proxyではなくactual cash evidence" in report
    assert "REBUILD_WITH_ACTUAL_CASH" in report
    assert "normal_paper_gap" in report
