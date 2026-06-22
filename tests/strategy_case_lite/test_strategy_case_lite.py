from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_case_lite.service import build_strategy_case_lite


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_case_lite.v1.schema.json").read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _stage_decision(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_stage_decisions/ndx-breakout-001/stage.json",
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


def _drift_review(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/drift.json",
        {
            "schema_version": "paper_vs_backtest_drift_review.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T01:00:00Z",
            "review_status": "READY_FOR_HUMAN_DRIFT_REVIEW",
            "recommended_action": "REVISE_STRATEGY",
            "failed_conditions": [
                {
                    "condition_id": "runtime_return_drift_within_limit",
                    "passed": False,
                    "observed": "-0.24",
                    "required": "abs(return drift) <= 0.05",
                    "severity": "error",
                }
            ],
            "paper_execution_allowed": False,
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
            "created_at": "2026-06-19T02:00:00Z",
            "plan_status": "READY_FOR_HUMAN_MICRO_LIVE_REVIEW",
            "failed_conditions": [],
            "micro_live_execution_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _live_observation(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_live_observations/ndx-breakout-001/live.json",
        {
            "schema_version": "strategy_live_observation_manifest.v1",
            "strategy_id": "ndx-breakout-001",
            "observation_id": "ndx-breakout-001-live-observation",
            "created_at": "2026-06-19T03:00:00Z",
            "ingest_status": "LIVE_OBSERVATION_INGESTED",
            "failed_conditions": [],
            "scale_up_allowed": False,
            "live_allowed": False,
        },
    )


def _scale_decision(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_scale_decisions/ndx-breakout-001/scale.json",
        {
            "schema_version": "strategy_scale_decision.v1",
            "strategy_id": "ndx-breakout-001",
            "decision_id": "ndx-breakout-001-scale-decision",
            "created_at": "2026-06-19T04:00:00Z",
            "decision_status": "READY_FOR_HUMAN_SCALE_REVIEW",
            "recommended_action": "PREPARE_NEXT_SCALE_PLAN",
            "failed_conditions": [],
            "next_scale_plan_allowed": False,
            "scale_up_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _next_scale_plan(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_next_scale_plans/ndx-breakout-001/next_scale.json",
        {
            "schema_version": "strategy_next_scale_plan.v1",
            "strategy_id": "ndx-breakout-001",
            "plan_id": "ndx-breakout-001-next-scale-plan",
            "created_at": "2026-06-19T05:00:00Z",
            "plan_status": "READY_FOR_HUMAN_NEXT_SCALE_REVIEW",
            "scale_decision_status": "READY_FOR_HUMAN_SCALE_REVIEW",
            "scale_recommended_action": "PREPARE_NEXT_SCALE_PLAN",
            "failed_conditions": [],
            "next_scale_execution_allowed": False,
            "live_allowed": False,
        },
    )


def _backtest_result(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/research/strategy_backtest_metrics.json",
        {
            "schema_version": "strategy_authoring_backtest_result.v1",
            "strategy_id": "trend_pullback_user_v1",
            "created_at": "2026-06-18T00:00:00Z",
            "summary": {"backtest_passed": True},
            "paper_only": True,
            "live_order_submitted": False,
        },
    )


def _strategy_review_manifest(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_reviews/dogfood-current/review_manifest.json",
        {
            "schema_version": "strategy_review_manifest.v1",
            "review_id": "dogfood-current",
            "created_at": "2026-06-18T01:00:00Z",
            "review_status": "READY_FOR_HUMAN_REVIEW",
            "source_artifacts": [],
        },
    )


def _input_feedback_proposal(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_input_feedback/proposal.json",
        {
            "schema_version": "strategy_input_contract_update_proposal.v1",
            "proposal_id": "proposal-runtime",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-22T09:05:00Z",
            "producer": {"tool": "sis", "command": "strategy-input-feedback-proposal-build"},
            "status": "READY_FOR_HUMAN_REVIEW",
            "source_artifacts": [
                {
                    "artifact_kind": "runtime_observation",
                    "path": "data/strategy_runtime_observation/obs.json",
                    "sha256": "sha256:" + "a" * 64,
                    "schema_version": "strategy_runtime_observation_manifest.v1",
                }
            ],
            "proposed_changes": [
                {
                    "change_id": "runtime-001",
                    "target_section": "execution_reality",
                    "recommendation": "Review runtime observation evidence.",
                    "evidence_summary": "pnl_available=False; max_observed_quote_age_ms=1048982067",
                    "source_reason": "runtime_observation:INGESTED",
                    "requires_human_review": True,
                }
            ],
            "blocked_reasons": [],
            "requires_human_review": True,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
            "feedback_boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "permits_wallet": False,
                "permits_signing": False,
                "permits_exchange_write": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
                "auto_applied": False,
                "direct_contract_edit_allowed": False,
            },
        },
    )


def _input_feedback_review(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_input_feedback/proposal-review.json",
        {
            "schema_version": "strategy_input_contract_update_review.v1",
            "review_id": "proposal-runtime-review",
            "proposal_id": "proposal-runtime",
            "strategy_id": "ndx-breakout-001",
            "reviewed_at": "2026-06-22T09:10:00Z",
            "producer": {"tool": "sis", "command": "strategy-input-feedback-proposal-review"},
            "reviewer": "operator-a",
            "decision": "HOLD",
            "rationale": "Hold because PnL is unavailable and quote age is stale.",
            "approved_change_ids": [],
            "required_actions": [
                "Choose a human-approved manual contract update target before applying runtime-001."
            ],
            "source_proposal": {
                "proposal_path": "data/strategy_input_feedback/proposal.json",
                "proposal_sha256": "sha256:" + "b" * 64,
                "proposal_id": "proposal-runtime",
                "proposal_status": "READY_FOR_HUMAN_REVIEW",
                "proposed_change_ids": ["runtime-001"],
                "proposed_change_count": 1,
                "auto_applied": False,
                "direct_contract_edit_allowed": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
            },
            "manual_contract_update_input_allowed": False,
            "requires_human_contract_update": True,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
            "feedback_boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "permits_wallet": False,
                "permits_signing": False,
                "permits_exchange_write": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
                "auto_applied": False,
                "direct_contract_edit_allowed": False,
            },
        },
    )


def test_strategy_case_lite_builds_schema_valid_timeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    stage = _stage_decision(tmp_path)
    drift = _drift_review(tmp_path)
    plan = _micro_live_plan(tmp_path)
    live = _live_observation(tmp_path)
    scale = _scale_decision(tmp_path)
    next_scale = _next_scale_plan(tmp_path)

    result = build_strategy_case_lite(
        strategy_id="ndx-breakout-001",
        artifact_paths=[drift, stage, plan, live, scale, next_scale],
        out_dir=tmp_path / "data/strategy_cases",
    )

    assert result.case.strategy_id == "ndx-breakout-001"
    assert result.case.summary.artifact_count == 6
    assert result.case.summary.timeline_count == 6
    assert result.case.summary.latest_status == "READY_FOR_HUMAN_NEXT_SCALE_REVIEW"
    assert result.case.summary.open_actions == ["PREPARE_NEXT_SCALE_PLAN", "REVISE_STRATEGY"]
    assert result.case.summary.blocked_reasons == ["runtime_return_drift_within_limit"]
    assert result.case.paper_execution_allowed is False
    assert result.case.live_allowed is False

    payload = json.loads(result.case_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["summary"]["latest_source_hashes"]["paper_vs_backtest_drift_review"].startswith(
        "sha256:"
    )
    assert payload["summary"]["latest_source_hashes"]["strategy_micro_live_plan"].startswith(
        "sha256:"
    )
    assert payload["summary"]["latest_source_hashes"][
        "strategy_live_observation_manifest"
    ].startswith("sha256:")
    assert payload["summary"]["latest_source_hashes"]["strategy_scale_decision"].startswith(
        "sha256:"
    )
    assert payload["summary"]["latest_source_hashes"]["strategy_next_scale_plan"].startswith(
        "sha256:"
    )
    report = result.report_path.read_text(encoding="utf-8")
    assert "Strategy Case Lite" in report
    assert "REVISE_STRATEGY" in report


def test_strategy_case_lite_accepts_backtest_and_review_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    backtest = _backtest_result(tmp_path)
    review = _strategy_review_manifest(tmp_path)

    result = build_strategy_case_lite(
        strategy_id="trend_pullback_user_v1",
        artifact_paths=[backtest, review],
        out_dir=tmp_path / "data/strategy_cases",
    )

    assert result.case.strategy_id == "trend_pullback_user_v1"
    assert result.case.summary.artifact_count == 2
    assert result.case.summary.latest_status == "READY_FOR_HUMAN_REVIEW"
    assert result.case.timeline[0].artifact_type.value == "strategy_authoring_backtest_result"
    assert result.case.timeline[1].artifact_type.value == "strategy_review_manifest"

    payload = json.loads(result.case_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["summary"]["latest_source_hashes"][
        "strategy_authoring_backtest_result"
    ].startswith("sha256:")
    assert payload["summary"]["latest_source_hashes"]["strategy_review_manifest"].startswith(
        "sha256:"
    )


def test_strategy_case_lite_summarizes_input_feedback_hold_review(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    proposal = _input_feedback_proposal(tmp_path)
    review = _input_feedback_review(tmp_path)

    result = build_strategy_case_lite(
        strategy_id="ndx-breakout-001",
        artifact_paths=[proposal, review],
        out_dir=tmp_path / "data/strategy_cases",
    )

    assert result.case.summary.latest_status == "HOLD"
    assert result.case.summary.open_actions == [
        "Choose a human-approved manual contract update target before applying runtime-001.",
        "Review runtime observation evidence.",
    ]
    assert result.case.summary.blocked_reasons == ["strategy_input_feedback_review:HOLD"]
    assert result.case.timeline[0].artifact_type.value == (
        "strategy_input_contract_update_proposal"
    )
    assert result.case.timeline[1].artifact_type.value == ("strategy_input_contract_update_review")
    assert result.case.timeline[0].action == "Review runtime observation evidence."
    assert result.case.timeline[1].action == (
        "Choose a human-approved manual contract update target before applying runtime-001."
    )

    payload = json.loads(result.case_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
