from __future__ import annotations

from datetime import datetime, timezone

from sis.execution.base import AdapterPositionSnapshot
from sis.ops.daily_loss_limit import evaluate_daily_loss_limit, evaluate_max_exposure
from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.paper.portfolio import PaperPosition
from sis.state.reconciliation import reconcile_positions
from sis.state.store import StateStore


def test_state_store_roundtrips_json_and_reconciliation_payload(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite")
    store.set_json("paper:last_run", {"status": "ok"})
    store.record_reconciliation("run-1", "2026-05-24T00:00:00+00:00", {"matched": 1})

    assert store.get_json("paper:last_run") == {"status": "ok"}


def test_reconcile_positions_detects_missing_entries() -> None:
    internal = [
        PaperPosition(
            venue="gtrade",
            canonical_symbol="QQQ",
            side="long",
            quantity=1.0,
            avg_entry_price=100.0,
            opened_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        )
    ]
    adapter = [
        AdapterPositionSnapshot(
            venue="ostium",
            canonical_symbol="SPY",
            side="long",
            quantity=2.0,
        )
    ]
    result = reconcile_positions(internal, adapter)

    assert result.matched == 0
    assert result.missing_in_adapter
    assert result.missing_in_internal


def test_kill_switch_and_healthcheck_work(tmp_path) -> None:
    kill_switch = KillSwitch(tmp_path / "kill_switch.flag")
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
    phase_gate = tmp_path / "phase_gate.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    audit_dashboard.write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot"}',
        encoding="utf-8",
    )
    audit_bundle.write_text('{"bundle_history_snapshot_count":3}', encoding="utf-8")
    phase_gate.write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true}',
        encoding="utf-8",
    )
    execution_drift_overview.write_text(
        '{"execution_drift_overview_status":"degraded","execution_drift_overview_diagnostics_alignment_match":false,"execution_drift_overview_state_comparison_mismatching_count":1,"execution_drift_overview_snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    readiness.write_text(
        '{"readiness_next_phase_candidate":"Stay Phase 1","readiness_execution_ready":false}',
        encoding="utf-8",
    )
    assert kill_switch.is_enabled() is False
    kill_switch.enable("test")
    status = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=tmp_path / "decision_summary.json",
        audit_dashboard_summary_path=audit_dashboard,
        audit_bundle_summary_path=audit_bundle,
        phase_gate_summary_path=phase_gate,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        reconciliation_store_present=True,
    )

    assert kill_switch.is_enabled() is True
    assert status["kill_switch_enabled"] is True
    assert status["status"] == "degraded"
    assert status["audit_latest_operation"] == "audit_bundle_snapshot"
    assert status["audit_bundle_history_snapshot_count"] == 3
    assert status["audit_summary"]["audit_overall_status"] == "ok"
    assert status["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert status["phase2_entry_allowed"] is False
    assert status["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert status["phase_gate_strict_validation_passed"] is True
    assert status["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert status["execution_drift_overview_status"] == "degraded"
    assert status["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert status["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert status["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"


def test_daily_loss_limit_and_exposure_limit_block() -> None:
    loss = evaluate_daily_loss_limit(-150.0, 100.0)
    exposure = evaluate_max_exposure(3.0, 2.0)

    assert loss.allowed is False
    assert loss.reason == "BLOCK_DAILY_LOSS_LIMIT"
    assert exposure.allowed is False
    assert exposure.reason == "BLOCK_MAX_EXPOSURE"
