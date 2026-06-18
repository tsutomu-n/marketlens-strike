from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_micro_live_plan.models import MicroLiveMonitoringPlan, MicroLiveRiskLimits
from sis.strategy_micro_live_plan.service import build_strategy_micro_live_plan


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_micro_live_plan.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _stage_decision(tmp_path: Path, decision: str = "READY_FOR_MICRO_LIVE_PLAN") -> Path:
    return _write_json(
        tmp_path / "data/strategy_stage/ndx-breakout-001/strategy_stage_decision.json",
        {
            "schema_version": "strategy_stage_decision.v1",
            "strategy_id": "ndx-breakout-001",
            "selected_stage": "micro_live_plan",
            "decision": decision,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _drift_review(
    tmp_path: Path,
    status: str = "READY_FOR_HUMAN_DRIFT_REVIEW",
    action: str = "HUMAN_REVIEW_REQUIRED",
) -> Path:
    return _write_json(
        tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/drift.json",
        {
            "schema_version": "paper_vs_backtest_drift_review.v1",
            "strategy_id": "ndx-breakout-001",
            "review_status": status,
            "recommended_action": action,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _human_approval(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_micro_live_approvals/ndx-breakout-001/approval.json",
        {
            "schema_version": "operator_micro_live_review.v1",
            "strategy_id": "ndx-breakout-001",
            "decision": "APPROVE_FOR_MICRO_LIVE_PLAN",
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _policy(tmp_path: Path, max_notional: float = 25.0) -> Path:
    return _write_text(
        tmp_path / "configs/micro_live_policy.yaml",
        "\n".join(
            [
                "micro_live_policy:",
                "  enabled: false",
                "  venue: trade_xyz",
                f"  max_notional_usd: {max_notional}",
                "  max_daily_loss_usd: 10",
                "  max_open_positions: 1",
                "  max_leverage: 1",
                "  allowed_symbols: [SPY, QQQ]",
                "  prohibited_order_types: [market]",
                "  schedule_cancel:",
                "    deadline_seconds_after_now: 300",
                "  close:",
                "    require_reduce_only: true",
                "",
            ]
        ),
    )


def _risk_limits(max_order: float = 10.0) -> MicroLiveRiskLimits:
    return MicroLiveRiskLimits(
        max_order_notional_usd=max_order,
        max_position_notional_usd=20,
        max_daily_loss_usd=5,
        max_total_loss_usd=10,
        max_open_positions=1,
        allowed_symbols=["SPY"],
        session_window="XNYS regular session only",
    )


def _monitoring_plan() -> MicroLiveMonitoringPlan:
    return MicroLiveMonitoringPlan(
        owner="operator",
        cadence="watch every fill and every 5 minutes",
        schedule_cancel_procedure="schedule cancel before submitting any canary order",
        kill_switch_procedure="stop new orders and cancel open orders immediately",
    )


def test_micro_live_plan_builds_ready_schema_valid_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_micro_live_plan(
        strategy_id="ndx-breakout-001",
        stage_decision_path=_stage_decision(tmp_path),
        drift_review_path=_drift_review(tmp_path),
        human_approval_path=_human_approval(tmp_path),
        micro_live_policy_path=_policy(tmp_path),
        risk_limits=_risk_limits(),
        monitoring_plan=_monitoring_plan(),
        out_dir=tmp_path / "data/strategy_micro_live_plans",
    )

    assert result.plan.plan_status == "READY_FOR_HUMAN_MICRO_LIVE_REVIEW"
    assert result.plan.micro_live_execution_allowed is False
    assert result.plan.wallet_used is False
    assert result.plan.signing_used is False
    assert result.plan.exchange_write_used is False
    assert result.plan.micro_live_policy_snapshot is not None
    assert result.plan.micro_live_policy_snapshot.enabled is False

    payload = json.loads(result.plan_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["micro_live_execution_allowed"] is False
    report = result.report_path.read_text(encoding="utf-8")
    assert "Strategy Micro Live Plan Gate" in report
    assert "not live execution permission" in report


def test_micro_live_plan_requires_human_approval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_micro_live_plan(
        strategy_id="ndx-breakout-001",
        stage_decision_path=_stage_decision(tmp_path),
        drift_review_path=_drift_review(tmp_path),
        micro_live_policy_path=_policy(tmp_path),
        risk_limits=_risk_limits(),
        monitoring_plan=_monitoring_plan(),
        out_dir=tmp_path / "data/strategy_micro_live_plans",
    )

    assert result.plan.plan_status == "NEEDS_HUMAN_APPROVAL"
    assert [item.condition_id for item in result.plan.failed_conditions] == [
        "human_micro_live_approval_present"
    ]


def test_micro_live_plan_blocks_policy_risk_limit_mismatch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_micro_live_plan(
        strategy_id="ndx-breakout-001",
        stage_decision_path=_stage_decision(tmp_path),
        drift_review_path=_drift_review(tmp_path),
        human_approval_path=_human_approval(tmp_path),
        micro_live_policy_path=_policy(tmp_path, max_notional=5),
        risk_limits=_risk_limits(max_order=10),
        monitoring_plan=_monitoring_plan(),
        out_dir=tmp_path / "data/strategy_micro_live_plans",
    )

    assert result.plan.plan_status == "NEEDS_RISK_LIMITS"
    assert "max_order_notional_within_existing_policy" in {
        item.condition_id for item in result.plan.failed_conditions
    }


def test_micro_live_plan_rejects_non_micro_live_stage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = build_strategy_micro_live_plan(
        strategy_id="ndx-breakout-001",
        stage_decision_path=_stage_decision(tmp_path, decision="READY_FOR_DRIFT_REVIEW"),
        drift_review_path=_drift_review(tmp_path),
        human_approval_path=_human_approval(tmp_path),
        risk_limits=_risk_limits(),
        monitoring_plan=_monitoring_plan(),
        out_dir=tmp_path / "data/strategy_micro_live_plans",
    )

    assert result.plan.plan_status == "NEEDS_STAGE_DECISION"
