from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_live_observation.service import ingest_strategy_live_observation


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_live_observation_manifest.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _audit_bundle(tmp_path: Path, status: str = "completed_canceled_open_order") -> Path:
    return _write_json(
        tmp_path / "data/ops/micro_live_audit_bundle.json",
        {
            "operation": "micro_live_canary",
            "status": status,
            "blocked_reasons": []
            if not status.startswith("blocked")
            else ["BLOCK_DAILY_LOSS_LIMIT"],
            "policy": {
                "venue": "trade_xyz",
                "enabled": True,
                "max_notional_usd": 50.0,
                "max_leverage": 1.0,
                "max_open_positions": 1,
            },
            "account": {
                "master_address": "0xmaster",
                "subaccount_address": "0xsub",
                "equity": 1000.0,
                "available_cash": 900.0,
            },
            "request": {
                "canonical_symbol": "SPY",
                "side": "long",
                "quantity": 1.0,
                "limit_price": 100.0,
                "cloid": "canary-1",
                "notional_usd": 10.0,
                "leverage": 1.0,
            },
            "gate_input": {
                "enable_live_flag": True,
                "kill_switch_clear": True,
                "schedule_cancel_success": True,
            },
            "actions": {
                "schedule_cancel_status": "scheduled",
                "order_submit_status": "submitted",
                "order_status": "open",
                "cancel_status": "canceled",
                "close_status": None,
            },
            "generated_at": "2026-06-19T01:00:00Z",
        },
    )


def _report(tmp_path: Path) -> Path:
    return _write_text(
        tmp_path / "data/reports/micro_live_safety_report.md",
        "# Micro Live Safety Report\n",
    )


def _micro_live_plan(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_micro_live_plans/ndx-breakout-001/strategy_micro_live_plan.json",
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


def test_live_observation_ingests_micro_live_canary_audit_bundle(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = ingest_strategy_live_observation(
        strategy_id="ndx-breakout-001",
        audit_bundle_path=_audit_bundle(tmp_path),
        report_path=_report(tmp_path),
        micro_live_plan_path=_micro_live_plan(tmp_path),
        out_dir=tmp_path / "data/strategy_live_observations",
    )

    assert result.manifest.ingest_status == "LIVE_OBSERVATION_INGESTED"
    assert result.manifest.summary.canary_status == "completed_canceled_open_order"
    assert result.manifest.summary.cancel_observed is True
    assert result.manifest.summary.account_snapshot_present is True
    assert result.manifest.live_execution_submitted_by_this_command is False
    assert result.manifest.scale_up_allowed is False
    assert result.manifest.live_allowed is False
    assert result.manifest.wallet_used is False
    assert result.manifest.signing_used is False
    assert result.manifest.exchange_write_used is False

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["summary"]["account_equity"] == 1000.0
    assert "master_address" not in json.dumps(payload)
    report = result.report_path.read_text(encoding="utf-8")
    assert "Strategy Live Observation" in report
    assert "does not submit live orders" in report


def test_live_observation_marks_blocked_canary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = ingest_strategy_live_observation(
        strategy_id="ndx-breakout-001",
        audit_bundle_path=_audit_bundle(tmp_path, status="blocked_policy"),
        out_dir=tmp_path / "data/strategy_live_observations",
    )

    assert result.manifest.ingest_status == "BLOCKED_CANARY"
    assert result.manifest.summary.max_loss_breach_observed is True
