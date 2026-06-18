from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

from sis.strategy_paper_smoke.service import build_paper_smoke_plan
from sis.strategy_stage.models import StageName
from sis.strategy_stage.service import build_stage_decision


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_paper_smoke_plan.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_yaml(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _valid_policy_payload() -> dict:
    return {
        "schema_version": "strategy_stage_policy.v1",
        "policy_id": "personal_default_v1",
        "description": "Personal default stage policy.",
        "fixed_safety": {
            "require_source_hashes": True,
            "require_schema_versions": True,
            "forbid_live_order_before_micro_live_gate": True,
            "forbid_wallet_before_micro_live_gate": True,
            "forbid_signing_before_micro_live_gate": True,
            "forbid_exchange_write_before_micro_live_gate": True,
            "require_manual_override_reason": True,
        },
        "stages": {
            "paper_smoke": {
                "min_fills": 3,
                "min_trading_days": 1,
                "max_order_notional_usd": 100,
                "max_position_notional_usd": 300,
                "max_orders_per_day": 10,
                "stop_after_consecutive_errors": 2,
            },
            "normal_paper_observation": {
                "min_fills": 20,
                "min_trading_days": 10,
                "max_no_fill_rate": 0.4,
                "max_slippage_bps": 20,
                "max_drawdown_vs_backtest_ratio": 2.0,
                "max_blocked_rate": 0.5,
                "max_consecutive_blocked": 3,
            },
            "drift_review": {"min_fills": 20, "min_trading_days": 10},
            "micro_live_plan": {
                "max_order_notional_usd": 50,
                "max_total_notional_usd": 100,
                "max_daily_loss_usd": 20,
                "max_total_loss_usd": 50,
                "max_runtime_days": 3,
                "require_manual_start": True,
                "require_kill_switch": True,
                "require_monitoring_plan": True,
            },
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def _write_policy(tmp_path: Path) -> Path:
    return _write_yaml(
        tmp_path / "configs/strategy_stage_policies/default.yaml", _valid_policy_payload()
    )


def _write_operator_review(tmp_path: Path) -> Path:
    return _write_yaml(
        tmp_path / "data/strategy_reviews/ndx-review-001/operator_review.yaml",
        {
            "schema_version": "operator_strategy_review.v1",
            "review_id": "ndx-review-001",
            "reviewed_at": "2026-06-18T12:45:00Z",
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
        },
    )


def _write_required_sources(tmp_path: Path) -> dict[str, Path]:
    return {
        "backtest_acceptance": _write_json(
            tmp_path / "data/research/strategy_lifecycle/backtest_acceptance_decision.json",
            {"schema_version": "strategy_backtest_acceptance_decision.v1"},
        ),
        "source_pack": _write_json(
            tmp_path / "data/research/paper_candidate_pack.json",
            {"schema_version": "paper_candidate_pack.v1"},
        ),
        "promotion_decision": _write_json(
            tmp_path / "data/research/promotion_decision.json",
            {"schema_version": "promotion_decision.v1"},
        ),
        "operator_promotion": _write_json(
            tmp_path / "data/research/ndx/operator_promotion_decision.json",
            {"schema_version": "ndx_operator_promotion_decision.v1"},
        ),
    }


def _stage_decision_path(tmp_path: Path, *, stage: StageName = StageName.PAPER_SMOKE) -> Path:
    policy_path = _write_policy(tmp_path)
    operator_review_path = _write_operator_review(tmp_path)
    result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=stage,
        policy_path=policy_path,
        out_dir=tmp_path / f"data/strategy_stage_decisions/{stage.value}",
        review_dir=operator_review_path.parent,
    )
    return result.decision_path


def test_paper_smoke_plan_ready_for_smoke_cycle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    operator_review_path = _write_operator_review(tmp_path)
    stage_result = build_stage_decision(
        strategy_id="ndx-breakout-001",
        stage=StageName.PAPER_SMOKE,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_stage_decisions/ndx-breakout-001-paper-smoke",
        review_dir=operator_review_path.parent,
    )
    sources = _write_required_sources(tmp_path)

    result = build_paper_smoke_plan(
        stage_decision_path=stage_result.decision_path,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_paper_smoke/ndx-breakout-001",
        data_dir=tmp_path / "data",
        artifact_dir=tmp_path / "data/research/ndx",
        reports_dir=tmp_path / "data/reports",
        session_id="smoke-001",
        backtest_acceptance_path=sources["backtest_acceptance"],
        source_pack_path=sources["source_pack"],
        promotion_decision_path=sources["promotion_decision"],
        operator_promotion_path=sources["operator_promotion"],
        paper_notional_usd=100,
    )

    assert result.plan.plan_status.value == "READY_TO_RUN_SMOKE_CYCLE"
    assert result.plan.paper_execution_allowed is False
    assert result.plan.live_allowed is False
    assert result.plan.thresholds.min_fills_for_pass == 3
    assert result.plan.thresholds.min_trading_days_for_pass == 1
    assert "--smoke" in result.plan.execution_preview.command
    assert "--min-fills-for-pass 3" in result.plan.execution_preview.command
    payload = json.loads(result.plan_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    report = result.report_path.read_text(encoding="utf-8")
    assert "A smoke pass is not a normal paper observation pass." in report


def test_paper_smoke_plan_records_missing_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    stage_decision_path = _stage_decision_path(tmp_path)

    result = build_paper_smoke_plan(
        stage_decision_path=stage_decision_path,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_paper_smoke/ndx-breakout-001",
        data_dir=tmp_path / "data",
        artifact_dir=tmp_path / "data/research/ndx",
        reports_dir=tmp_path / "data/reports",
        session_id="smoke-001",
        backtest_acceptance_path=tmp_path
        / "data/research/strategy_lifecycle/backtest_acceptance_decision.json",
        source_pack_path=tmp_path / "data/research/paper_candidate_pack.json",
        promotion_decision_path=tmp_path / "data/research/promotion_decision.json",
        operator_promotion_path=tmp_path / "data/research/ndx/operator_promotion_decision.json",
    )

    assert result.plan.plan_status.value == "NEEDS_SOURCE_ARTIFACTS"
    missing = {
        artifact.artifact_key for artifact in result.plan.source_artifacts if not artifact.exists
    }
    assert {
        "backtest_acceptance",
        "paper_candidate_pack",
        "promotion_decision",
        "operator_promotion",
    }.issubset(missing)


def test_paper_smoke_plan_rejects_non_smoke_stage_decision(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy_path = _write_policy(tmp_path)
    stage_decision_path = _stage_decision_path(tmp_path, stage=StageName.NORMAL_PAPER_OBSERVATION)
    sources = _write_required_sources(tmp_path)

    result = build_paper_smoke_plan(
        stage_decision_path=stage_decision_path,
        policy_path=policy_path,
        out_dir=tmp_path / "data/strategy_paper_smoke/ndx-breakout-001",
        data_dir=tmp_path / "data",
        artifact_dir=tmp_path / "data/research/ndx",
        reports_dir=tmp_path / "data/reports",
        session_id="smoke-001",
        backtest_acceptance_path=sources["backtest_acceptance"],
        source_pack_path=sources["source_pack"],
        promotion_decision_path=sources["promotion_decision"],
        operator_promotion_path=sources["operator_promotion"],
    )

    assert result.plan.plan_status.value == "NEEDS_STAGE_APPROVAL"
    failed = {condition.condition_id for condition in result.plan.failed_conditions}
    assert "stage_is_paper_smoke" in failed
    assert "stage_decision_ready" in failed
