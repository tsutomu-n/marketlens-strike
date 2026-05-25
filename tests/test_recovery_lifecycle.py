from __future__ import annotations

import json
from datetime import datetime, timezone

from sis.ops.daemon import create_daemon_manifest, run_daemon_dry_run, write_daemon_manifest
from sis.ops.kill_switch import KillSwitch
from sis.ops.manifest_chain import latest_operation_manifest
from sis.reports.lifecycle import build_strategy_lifecycle_report
from sis.state.recovery import export_state_snapshot, restore_state_snapshot
from sis.state.store import StateStore
from sis.storage.jsonl_store import write_json


def test_state_snapshot_export_and_restore(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite")
    store.set_json("paper_positions", [{"venue": "gtrade"}])
    store.set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {"overall_status": "ok", "latest_operation": "audit_bundle_snapshot"},
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "timeline_latest_execution_overall_status": "ok",
            "timeline_latest_execution_venue_count": 2,
            "timeline_latest_execution_comparison_all_registries_present": True,
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_overall_status": "ok",
            "bundle_history_latest_execution_venue_count": 2,
            "bundle_history_latest_execution_comparison_all_registries_present": True,
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "cycle_history_latest_execution_overall_status": "ok",
            "cycle_history_latest_execution_venue_count": 2,
            "cycle_history_latest_execution_comparison_all_registries_present": True,
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
            },
            "readiness_summary": {
                "next_phase_candidate": "Stay Phase 1",
                "execution_ready": False,
            },
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
            "execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
                "execution_report_path": "data/reports/execution_snapshot.md",
            },
            "execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
                "execution_comparison_report_path": "data/reports/execution_venue_comparison.md",
            },
            "execution_diagnostics_summary": {
                "execution_diagnostics_status": "degraded",
                "execution_balance_gap_detected": True,
                "execution_fills_gap_detected": False,
                "execution_diagnostics_report_path": "data/reports/execution_venue_diagnostics.md",
            },
            "execution_gap_history_summary": {
                "execution_gap_history_entry_count": 4,
                "execution_gap_history_latest_status": "ok",
                "execution_gap_history_latest_diagnostics_status": "degraded",
                "execution_gap_history_report_path": "data/reports/execution_gap_history.md",
            },
            "execution_state_comparison_summary": {
                "execution_state_comparison_entry_count": 4,
                "execution_state_comparison_latest_status_match": False,
                "execution_state_comparison_mismatching_count": 1,
                "execution_state_comparison_report_path": "data/reports/execution_state_comparison_history.md",
            },
            "execution_snapshot_drift_summary": {
                "execution_snapshot_drift_entry_count": 3,
                "execution_snapshot_drift_latest_status_match": True,
                "execution_snapshot_drift_mismatching_snapshot_count": 1,
                "execution_snapshot_drift_report_path": "data/reports/execution_snapshot_drift_history.md",
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
            },
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    snapshot = export_state_snapshot(store, tmp_path / "snapshot.json")

    restored = StateStore(tmp_path / "restored.sqlite")
    restore_state_snapshot(restored, snapshot)

    assert snapshot.exists()
    assert restored.get_json("paper_positions") == [{"venue": "gtrade"}]
    assert restored.get_json("paper_last_run") == {
        "orders_count": 1,
        "audit": {"overall_status": "ok", "latest_operation": "audit_bundle_snapshot"},
        "timeline_latest_execution_summary": {
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        "timeline_latest_execution_comparison_summary": {
            "execution_comparison_all_registries_present": True,
        },
        "timeline_latest_execution_overall_status": "ok",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": True,
        "bundle_history_latest_execution_summary": {
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        "bundle_history_latest_execution_comparison_summary": {
            "execution_comparison_all_registries_present": True,
        },
        "bundle_history_latest_execution_overall_status": "ok",
        "bundle_history_latest_execution_venue_count": 2,
        "bundle_history_latest_execution_comparison_all_registries_present": True,
        "cycle_history_latest_execution_summary": {
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        "cycle_history_latest_execution_comparison_summary": {
            "execution_comparison_all_registries_present": True,
        },
        "cycle_history_latest_execution_overall_status": "ok",
        "cycle_history_latest_execution_venue_count": 2,
        "cycle_history_latest_execution_comparison_all_registries_present": True,
        "phase_gate": {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
        },
        "readiness_summary": {
            "next_phase_candidate": "Stay Phase 1",
            "execution_ready": False,
        },
        "readiness_next_phase_candidate": "Stay Phase 1",
        "readiness_execution_ready": False,
        "execution_summary": {
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
            "execution_report_path": "data/reports/execution_snapshot.md",
        },
        "execution_comparison_summary": {
            "execution_comparison_all_registries_present": True,
            "execution_comparison_report_path": "data/reports/execution_venue_comparison.md",
        },
        "execution_diagnostics_summary": {
            "execution_diagnostics_status": "degraded",
            "execution_balance_gap_detected": True,
            "execution_fills_gap_detected": False,
            "execution_diagnostics_report_path": "data/reports/execution_venue_diagnostics.md",
        },
        "execution_gap_history_summary": {
            "execution_gap_history_entry_count": 4,
            "execution_gap_history_latest_status": "ok",
            "execution_gap_history_latest_diagnostics_status": "degraded",
            "execution_gap_history_report_path": "data/reports/execution_gap_history.md",
        },
        "execution_state_comparison_summary": {
            "execution_state_comparison_entry_count": 4,
            "execution_state_comparison_latest_status_match": False,
            "execution_state_comparison_mismatching_count": 1,
            "execution_state_comparison_report_path": "data/reports/execution_state_comparison_history.md",
        },
        "execution_snapshot_drift_summary": {
            "execution_snapshot_drift_entry_count": 3,
            "execution_snapshot_drift_latest_status_match": True,
            "execution_snapshot_drift_mismatching_snapshot_count": 1,
            "execution_snapshot_drift_report_path": "data/reports/execution_snapshot_drift_history.md",
        },
        "execution_drift_overview_summary": {
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": False,
        "execution_drift_overview_state_comparison_mismatching_count": 1,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
    }
    assert '"overall_status": "ok"' in snapshot.read_text(encoding="utf-8")
    assert '"audit_overall_status": "ok"' in snapshot.read_text(encoding="utf-8")
    assert '"audit_latest_operation": "audit_bundle_snapshot"' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"execution_overall_status": "ok"' in snapshot.read_text(encoding="utf-8")
    assert '"timeline_latest_execution_summary"' in snapshot.read_text(encoding="utf-8")
    assert '"bundle_history_latest_execution_summary"' in snapshot.read_text(encoding="utf-8")
    assert '"cycle_history_latest_execution_summary"' in snapshot.read_text(encoding="utf-8")
    assert '"timeline_latest_execution_overall_status": "ok"' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"bundle_history_latest_execution_overall_status": "ok"' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"cycle_history_latest_execution_overall_status": "ok"' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"execution_comparison_all_registries_present": true' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"execution_diagnostics_status": "degraded"' in snapshot.read_text(encoding="utf-8")
    assert '"execution_gap_history_entry_count": 4' in snapshot.read_text(encoding="utf-8")
    assert '"execution_state_comparison_mismatching_count": 1' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"execution_snapshot_drift_mismatching_snapshot_count": 1' in snapshot.read_text(
        encoding="utf-8"
    )
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in snapshot.read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in snapshot.read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in snapshot.read_text(encoding="utf-8")


def test_daemon_manifest_and_lifecycle_report(tmp_path) -> None:
    manifest = create_daemon_manifest(
        mode="paper",
        command="uv run sis paper-step",
        state_store_path=tmp_path / "state.sqlite",
    )
    manifest_path = write_daemon_manifest(tmp_path / "daemon_manifest.json", manifest)
    write_json(
        tmp_path / "decision_summary.json",
        {"mode": "signal_driven", "signals_considered": 2, "executed_count": 1, "blocked_count": 1},
    )
    weekly_path = tmp_path / "weekly_review.md"
    weekly_path.write_text("# Weekly Strategy Review\n\n- sample\n", encoding="utf-8")
    paper_last_run_path = tmp_path / "paper_last_run.json"
    write_json(
        paper_last_run_path,
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "timeline_latest_execution_overall_status": "ok",
            "timeline_latest_execution_venue_count": 2,
            "timeline_latest_execution_comparison_all_registries_present": True,
            "bundle_history_latest_execution_overall_status": "ok",
            "bundle_history_latest_execution_venue_count": 2,
            "bundle_history_latest_execution_comparison_all_registries_present": True,
            "cycle_history_latest_execution_overall_status": "ok",
            "cycle_history_latest_execution_venue_count": 2,
            "cycle_history_latest_execution_comparison_all_registries_present": True,
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    )

    report = build_strategy_lifecycle_report(
        decision_summary_path=tmp_path / "decision_summary.json",
        weekly_review_path=weekly_path,
        paper_last_run_path=paper_last_run_path,
        out_path=tmp_path / "lifecycle.md",
    )

    assert manifest_path.exists()
    assert "Strategy Lifecycle Report" in report
    assert "## Quick Navigation" in report
    assert f"- strategy_lifecycle_report: {tmp_path / 'lifecycle.md'}" in report
    assert "## Related Reports" in report
    assert f"- weekly_review_report: {tmp_path / 'weekly_strategy_review.md'}" in report
    assert "signals_considered: 2" in report
    assert "Weekly Strategy Review" in report
    assert "Paper Last Run Audit" in report
    assert "Paper Last Run Phase Gate" in report
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "Paper Last Run Execution Drift Overview" in report
    assert "overall_status: degraded" in report
    assert "Paper Last Run Audit Timeline Latest Execution" in report
    assert "Paper Last Run Audit Bundle History Latest Execution" in report
    assert "Paper Last Run Cycle History Latest Execution" in report


def test_daemon_dry_run_writes_snapshot_and_operation_chain(tmp_path) -> None:
    data_dir = tmp_path / "data"
    write_json(
        data_dir / "ops/audit_dashboard_summary.json",
        {
            "overall_status": "ok",
            "timeline_latest_operation": "audit_bundle_snapshot",
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
        },
    )
    write_json(
        data_dir / "ops/audit_bundle_manifest.json",
        {
            "bundle_history_snapshot_count": 3,
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
        },
    )
    write_json(
        data_dir / "ops/operations_bundle_manifest.json",
        {
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "cycle_history_latest_execution_overall_status": "ok",
            "cycle_history_latest_execution_venue_count": 2,
            "cycle_history_latest_execution_comparison_all_registries_present": True,
        },
    )
    write_json(
        data_dir / "ops/phase_gate_review_summary.json",
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
        },
    )
    result = run_daemon_dry_run(
        data_dir=data_dir,
        mode="paper",
        command="uv run sis paper-step",
        state_store_path=data_dir / "state/marketlens.sqlite",
        every_minutes=30,
        kill_switch=KillSwitch(data_dir / "state/kill_switch.flag"),
        decision_summary_path=None,
        audit_dashboard_summary_path=data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=data_dir / "ops/phase_gate_review_summary.json",
        execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        execution_comparison_summary={
            "execution_comparison_all_registries_present": True,
        },
        execution_diagnostics_summary={
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
        },
        execution_gap_history_summary={
            "execution_gap_history_entry_count": 4,
            "execution_gap_history_latest_status": "ok",
            "execution_gap_history_latest_execution_diagnostics_status": "degraded",
        },
        execution_state_comparison_summary={
            "execution_state_comparison_entry_count": 4,
            "execution_state_comparison_latest_status_match": False,
            "execution_state_comparison_mismatching_count": 1,
        },
        execution_snapshot_drift_summary={
            "execution_snapshot_drift_entry_count": 3,
            "execution_snapshot_drift_latest_execution_state_comparison_status_match": True,
            "execution_snapshot_drift_mismatching_snapshot_count": 1,
        },
        execution_drift_overview_summary={
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        },
        readiness_summary={
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        },
        now=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )
    latest = latest_operation_manifest(result.operation_chain_path)
    snapshot = json.loads(result.dry_run_snapshot_path.read_text(encoding="utf-8"))

    assert result.daemon_manifest_path.exists()
    assert result.schedule_path.exists()
    assert result.dry_run_snapshot_path.exists()
    assert result.status == "planned"
    assert snapshot["audit"]["overall_status"] == "ok"
    assert snapshot["audit"]["latest_operation"] == "audit_bundle_snapshot"
    assert snapshot["audit"]["bundle_history_snapshot_count"] == 3
    assert snapshot["audit_summary"]["overall_status"] == "ok"
    assert snapshot["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        snapshot["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert (
        snapshot["bundle_history_latest_execution_summary"]["execution_overall_status"]
        == "ok"
    )
    assert (
        snapshot["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert snapshot["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        snapshot["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert snapshot["cycle_history_latest_execution_overall_status"] == "ok"
    assert snapshot["cycle_history_latest_execution_venue_count"] == 2
    assert snapshot["cycle_history_latest_execution_comparison_all_registries_present"] is True
    assert snapshot["phase_gate"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert snapshot["phase_gate"]["phase2_entry_allowed"] is False
    assert snapshot["phase_gate"]["phase2_entry_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["phase_gate"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["phase_gate"]["phase_gate_strict_validation_passed"] is True
    assert snapshot["phase_gate"]["phase_gate_strict_validation_issue_count"] == 2
    assert snapshot["phase_gate"]["phase_gate_checked_files"] == 7
    assert snapshot["phase_gate"]["strict_validation_issue_count"] == 2
    assert snapshot["phase_gate"]["checked_files"] == 7
    assert snapshot["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert snapshot["phase2_entry_allowed"] is False
    assert snapshot["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["phase_gate_strict_validation_passed"] is True
    assert snapshot["phase_gate_strict_validation_issue_count"] == 2
    assert snapshot["phase_gate_checked_files"] == 7
    assert snapshot["execution_diagnostics"]["overall_status"] == "degraded"
    assert snapshot["execution_diagnostics_summary"]["overall_status"] == "degraded"
    assert snapshot["execution"]["execution_overall_status"] == "ok"
    assert snapshot["execution_summary"]["execution_overall_status"] == "ok"
    assert snapshot["execution_comparison"]["execution_comparison_all_registries_present"] is True
    assert snapshot["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert snapshot["execution_gap_history"]["execution_gap_history_entry_count"] == 4
    assert snapshot["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert snapshot["execution_state_comparison"]["execution_state_comparison_mismatching_count"] == 1
    assert snapshot["execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == 1
    assert snapshot["execution_snapshot_drift"]["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert snapshot["execution_snapshot_drift_summary"]["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert snapshot["execution_drift_overview"]["overall_status"] == "degraded"
    assert snapshot["execution_drift_overview_summary"]["overall_status"] == "degraded"
    assert snapshot["execution_drift_overview_status"] == "degraded"
    assert snapshot["readiness"]["next_phase_candidate"] == "Stay Phase 1"
    assert snapshot["readiness_summary"]["next_phase_candidate"] == "Stay Phase 1"
    assert snapshot["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert snapshot["readiness_execution_ready"] is False
    assert snapshot["readiness"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert snapshot["readiness"]["readiness_execution_ready"] is False
    assert snapshot["execution_drift_overview"]["execution_drift_overview_status"] == "degraded"
    assert snapshot["execution_drift_overview"]["execution_drift_overview_diagnostics_alignment_match"] is False
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears"' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears"' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"phase_gate_strict_validation_passed": true' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_summary"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_overall_status": "ok"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_comparison_summary"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_diagnostics_status": "degraded"' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_gap_history_summary"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_state_comparison_summary"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_snapshot_drift_summary"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_balance_gap_detected": true' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_fills_gap_detected": false' in result.schedule_path.read_text(
        encoding="utf-8"
    )
    assert '"balance_gap_detected": true' in result.schedule_path.read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in result.schedule_path.read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in result.schedule_path.read_text(encoding="utf-8")
    assert '"next_phase_candidate": "Stay Phase 1"' in result.schedule_path.read_text(encoding="utf-8")
    assert snapshot["execution_diagnostics"]["execution_diagnostics_status"] == "degraded"
    assert snapshot["execution_diagnostics"]["execution_balance_gap_detected"] is True
    assert snapshot["execution_diagnostics"]["execution_fills_gap_detected"] is False
    assert latest is not None
    assert latest["parent_run_id"] == result.run_id
    assert latest["scheduled_for"] == "2026-05-24T12:30:00+00:00"
    assert "execution_diagnostics_status=degraded" in latest["notes"]
    assert "readiness_next_phase=Stay Phase 1" in latest["notes"]
