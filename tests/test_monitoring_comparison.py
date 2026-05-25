from __future__ import annotations

import polars as pl

from sis.execution.base import AdapterActionResult, AdapterFillSnapshot, AdapterOrderStatus
from sis.reports.audit_bundle_history import build_audit_bundle_history_report
from sis.reports.audit_bundle import build_audit_bundle_manifest
from sis.ops.monitoring import build_monitoring_snapshot, write_monitoring_snapshot
from sis.reports.audit_dashboard import build_audit_dashboard
from sis.reports.comparison import build_paper_live_comparison_report
from sis.reports.cost_matrix import build_cost_matrix_report
from sis.reports.current_state_index import build_current_state_index
from sis.reports.execution_adapter_status import (
    build_action_status_report,
    build_balance_status_report,
    build_execution_read_only_surfaces_report,
    build_fill_status_report,
    build_order_status_report,
    build_reconcile_positions_report,
)
from sis.reports.execution_drift_overview import build_execution_drift_overview_report
from sis.reports.execution_gap_history import build_execution_gap_history_report
from sis.reports.execution_snapshot_drift_history import build_execution_snapshot_drift_history_report
from sis.reports.execution_state_comparison_history import build_execution_state_comparison_history_report
from sis.reports.live_evidence_report import (
    LiveEvidenceArtifacts,
    LiveEvidenceReportData,
    render_live_evidence_report,
)
from sis.reports.weekly_review import build_weekly_review_report
from sis.reports.audit_timeline import build_audit_timeline_report
from sis.reports.operations_audit_pack import build_operations_audit_pack
from sis.reports.operations_bundle import build_operations_bundle_manifest
from sis.reports.ops_review import build_ops_review_report
from sis.reports.paper_cycle_history import build_paper_cycle_history_report
from sis.reports.operations_dashboard import build_operations_dashboard
from sis.reports.operations_timeline import build_operations_timeline_report
from sis.reports.paper_operations_runbook import build_paper_operations_runbook
from sis.reports.quote_diagnostics import build_quote_diagnostics_report
from sis.reports.readiness_snapshot import build_readiness_snapshot
from sis.reports.remediation_execution_plan import build_remediation_execution_plan
from sis.reports.remediation_planner import build_remediation_planner
from sis.reports.remediation_session import build_remediation_session
from sis.reports.remediation_session_checkpoint import build_remediation_session_checkpoint
from sis.reports.remediation_scoreboard import build_remediation_scoreboard
from sis.reports.remediation_evaluator import build_remediation_evaluator
from sis.reports.remediation_evidence import build_remediation_evidence
from sis.reports.remediation_command_results import build_remediation_command_results
from sis.reports.state_command_status import (
    build_daemon_manifest_report,
    build_state_export_report,
    build_state_restore_report,
)
from sis.state.reconciliation import ReconciliationResult
from sis.storage.jsonl_store import read_json, write_json
from sis.validation.artifacts import ValidationSummary


def test_build_monitoring_snapshot_and_write(tmp_path) -> None:
    decision_summary = tmp_path / "decision_summary.json"
    weekly_review = tmp_path / "weekly.md"
    daily_pnl = tmp_path / "daily_pnl.parquet"
    operation_chain = tmp_path / "operation_manifests.jsonl"
    execution_snapshot = tmp_path / "execution_snapshot.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
    operations_bundle = tmp_path / "operations_bundle.json"
    phase_gate = tmp_path / "phase_gate.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    write_json(decision_summary, {"mode": "signal_driven", "executed_count": 1})
    weekly_review.write_text("# Weekly Strategy Review\n", encoding="utf-8")
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 1.0}]).write_parquet(daily_pnl)
    operation_chain.write_text(
        '{"operation":"daemon_dry_run","status":"planned","artifacts":[],"notes":[]}\n',
        encoding="utf-8",
    )
    write_json(execution_snapshot, {"overall_status": "ok", "venue_count": 2})
    write_json(
        execution_comparison,
        {"all_registries_present": True, "report_path": "data/reports/execution_venue_comparison.md"},
    )
    write_json(
        execution_diagnostics,
        {
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
            "report_path": "data/reports/execution_venue_diagnostics.md",
        },
    )
    write_json(
        execution_gap_history,
        {
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "report_path": "data/reports/execution_gap_history.md",
        },
    )
    write_json(
        execution_state_comparison,
        {
            "entry_count": 4,
            "latest_status_match": False,
            "mismatching_count": 1,
            "report_path": "data/reports/execution_state_comparison_history.md",
        },
    )
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_snapshot_drift_history.md",
        },
    )
    write_json(
        audit_dashboard,
        {
            "overall_status": "ok",
            "timeline_latest_operation": "audit_bundle_snapshot",
            "audit_entry_count": 4,
            "audit_bundle_snapshot_count": 1,
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
        audit_bundle,
        {
            "bundle_history_snapshot_count": 3,
            "bundle_history_ok_count": 3,
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
        operations_bundle,
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
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )
    write_json(
        execution_drift_overview,
        {
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(
        readiness,
        {
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        },
    )

    snapshot = build_monitoring_snapshot(
        decision_summary_path=decision_summary,
        weekly_review_path=weekly_review,
        daily_pnl_path=daily_pnl,
        operation_chain_path=operation_chain,
        execution_snapshot_summary_path=execution_snapshot,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        audit_dashboard_summary_path=audit_dashboard,
        audit_bundle_summary_path=audit_bundle,
        operations_bundle_manifest_path=operations_bundle,
        phase_gate_summary_path=phase_gate,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        last_healthcheck={"status": "ok"},
    )
    out = write_monitoring_snapshot(tmp_path / "monitoring.json", snapshot)

    assert snapshot["status"] == "ok"
    assert snapshot["decision_summary_exists"] is True
    assert snapshot["operation_chain_exists"] is True
    assert snapshot["operation_chain_count"] == 1
    assert snapshot["execution_overall_status"] == "ok"
    assert snapshot["execution_venue_count"] == 2
    assert snapshot["execution_comparison_all_registries_present"] is True
    assert snapshot["execution_diagnostics_status"] == "degraded"
    assert snapshot["execution_balance_gap_detected"] is True
    assert snapshot["execution_fills_gap_detected"] is False
    assert snapshot["execution_gap_history_entry_count"] == 4
    assert snapshot["execution_gap_history_latest_status"] == "ok"
    assert snapshot["execution_state_comparison_mismatching_count"] == 1
    assert snapshot["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert snapshot["paper_total_realized_pnl"] == 1.0
    assert snapshot["audit_latest_operation"] == "audit_bundle_snapshot"
    assert snapshot["audit_bundle_history_snapshot_count"] == 3
    assert snapshot["audit_summary"]["audit_overall_status"] == "ok"
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
    assert snapshot["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert snapshot["phase2_entry_allowed"] is False
    assert snapshot["phase_gate"]["phase2_entry_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["phase_gate"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["phase_gate"]["phase_gate_strict_validation_passed"] is True
    assert snapshot["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert snapshot["execution_drift_overview_status"] == "degraded"
    assert snapshot["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert snapshot["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert snapshot["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert snapshot["execution_comparison"]["execution_comparison_all_registries_present"] is True
    assert snapshot["execution_diagnostics"]["execution_diagnostics_status"] == "degraded"
    assert snapshot["execution_gap_history"]["execution_gap_history_entry_count"] == 4
    assert (
        snapshot["execution_state_comparison"]["execution_state_comparison_mismatching_count"]
        == 1
    )
    assert (
        snapshot["execution_snapshot_drift"]["execution_snapshot_drift_mismatching_snapshot_count"]
        == 1
    )
    assert out.exists()


def test_build_paper_live_comparison_report(tmp_path) -> None:
    paper_pnl = tmp_path / "daily_pnl.parquet"
    backtest_metrics = tmp_path / "backtest_metrics.json"
    paper_last_run = tmp_path / "paper_last_run.json"
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 5.0}]).write_parquet(paper_pnl)
    pl.DataFrame(
        [{"canonical_symbol": "QQQ", "avg_trade_return": 0.05}, {"canonical_symbol": "SPY", "avg_trade_return": 0.01}]
    ).write_json(backtest_metrics)
    write_json(
        paper_last_run,
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
            "readiness_summary": {
                "next_phase_candidate": "Stay Phase 1",
                "execution_ready": False,
            },
            "execution_summary": {
                "overall_status": "ok",
                "venue_count": 2,
                "report_path": "data/reports/execution_snapshot.md",
            },
            "execution_comparison_summary": {
                "all_registries_present": True,
                "report_path": "data/reports/execution_venue_comparison.md",
            },
            "execution_diagnostics_summary": {
                "overall_status": "degraded",
                "balance_gap_detected": True,
                "fills_gap_detected": False,
                "report_path": "data/reports/execution_venue_diagnostics.md",
            },
            "execution_gap_history_summary": {
                "entry_count": 4,
                "latest_status": "ok",
                "latest_execution_diagnostics_status": "degraded",
                "report_path": "data/reports/execution_gap_history.md",
            },
            "execution_state_comparison_summary": {
                "entry_count": 4,
                "latest_status_match": False,
                "mismatching_count": 1,
                "report_path": "data/reports/execution_state_comparison_history.md",
            },
            "execution_snapshot_drift_summary": {
                "entry_count": 3,
                "latest_execution_state_comparison_status_match": True,
                "mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_snapshot_drift_history.md",
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
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
        },
    )

    report = build_paper_live_comparison_report(
        paper_pnl_path=paper_pnl,
        backtest_metrics_path=backtest_metrics,
        paper_last_run_path=paper_last_run,
        out_path=tmp_path / "comparison.md",
    )

    assert "Paper vs Backtest Comparison" in report
    assert "paper_total_realized_pnl: 5.0" in report
    assert "backtest_avg_trade_return_mean: 0.03" in report
    assert "## Quick Navigation" in report
    assert f"- paper_vs_backtest_comparison_report: {tmp_path / 'comparison.md'}" in report
    assert "## Related Reports" in report
    assert "- execution_snapshot_report: data/reports/execution_snapshot.md" in report
    assert "Paper Last Run Audit" in report
    assert "latest_operation: audit_bundle_snapshot" in report
    assert "Paper Last Run Phase Gate" in report
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "Paper Last Run Readiness" in report
    assert "next_phase_candidate: Stay Phase 1" in report
    assert "Paper Last Run Execution Snapshot" in report
    assert "venue_count: 2" in report
    assert "Paper Last Run Execution Venue Comparison" in report
    assert "all_registries_present: True" in report
    assert "Paper Last Run Execution Venue Diagnostics" in report
    assert "balance_gap_detected: True" in report
    assert "Paper Last Run Execution Gap History" in report
    assert "entry_count: 4" in report
    assert "Paper Last Run Execution State Comparison History" in report
    assert "mismatching_count: 1" in report
    assert "Paper Last Run Execution Snapshot Drift History" in report
    assert "mismatching_snapshot_count: 1" in report
    assert "Paper Last Run Execution Drift Overview" in report
    assert "overall_status: degraded" in report
    assert "Paper Last Run Audit Timeline Latest Execution" in report
    assert "Paper Last Run Audit Bundle History Latest Execution" in report
    assert "Paper Last Run Cycle History Latest Execution" in report


def test_build_weekly_review_report_includes_paper_last_run_audit(tmp_path) -> None:
    backtest_metrics = tmp_path / "backtest_metrics.json"
    daily_pnl = tmp_path / "daily_pnl.parquet"
    paper_last_run = tmp_path / "paper_last_run.json"
    pl.DataFrame([{"canonical_symbol": "QQQ"}]).write_json(backtest_metrics)
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 2.0}]).write_parquet(daily_pnl)
    write_json(
        paper_last_run,
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
            "readiness_summary": {
                "next_phase_candidate": "Stay Phase 1",
                "execution_ready": False,
            },
            "execution_summary": {
                "overall_status": "ok",
                "venue_count": 2,
                "report_path": "data/reports/execution_snapshot.md",
            },
            "execution_comparison_summary": {
                "all_registries_present": True,
                "report_path": "data/reports/execution_venue_comparison.md",
            },
            "execution_diagnostics_summary": {
                "overall_status": "degraded",
                "balance_gap_detected": True,
                "fills_gap_detected": False,
                "report_path": "data/reports/execution_venue_diagnostics.md",
            },
            "execution_gap_history_summary": {
                "entry_count": 4,
                "latest_status": "ok",
                "latest_execution_diagnostics_status": "degraded",
                "report_path": "data/reports/execution_gap_history.md",
            },
            "execution_state_comparison_summary": {
                "entry_count": 4,
                "latest_status_match": False,
                "mismatching_count": 1,
                "report_path": "data/reports/execution_state_comparison_history.md",
            },
            "execution_snapshot_drift_summary": {
                "entry_count": 3,
                "latest_execution_state_comparison_status_match": True,
                "mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_snapshot_drift_history.md",
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
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
        },
    )

    report = build_weekly_review_report(
        backtest_metrics_path=backtest_metrics,
        daily_pnl_path=daily_pnl,
        paper_last_run_path=paper_last_run,
        out_path=tmp_path / "weekly.md",
    )

    assert "Weekly Strategy Review" in report
    assert "## Quick Navigation" in report
    assert f"- weekly_review_report: {tmp_path / 'weekly.md'}" in report
    assert "## Related Reports" in report
    assert "- execution_snapshot_report: data/reports/execution_snapshot.md" in report
    assert "Paper Last Run Audit" in report
    assert "overall_status: ok" in report
    assert "Paper Last Run Phase Gate" in report
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "Paper Last Run Readiness" in report
    assert "next_phase_candidate: Stay Phase 1" in report
    assert "Paper Last Run Execution Snapshot" in report
    assert "venue_count: 2" in report
    assert "Paper Last Run Execution Venue Comparison" in report
    assert "all_registries_present: True" in report
    assert "Paper Last Run Execution Venue Diagnostics" in report
    assert "balance_gap_detected: True" in report
    assert "Paper Last Run Execution Gap History" in report
    assert "entry_count: 4" in report
    assert "Paper Last Run Execution State Comparison History" in report
    assert "mismatching_count: 1" in report
    assert "Paper Last Run Execution Snapshot Drift History" in report
    assert "mismatching_snapshot_count: 1" in report
    assert "Paper Last Run Execution Drift Overview" in report
    assert "overall_status: degraded" in report
    assert "Paper Last Run Audit Timeline Latest Execution" in report
    assert "Paper Last Run Audit Bundle History Latest Execution" in report
    assert "Paper Last Run Cycle History Latest Execution" in report


def test_build_ops_review_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    monitoring = tmp_path / "monitoring.json"
    daemon_dry_run = tmp_path / "daemon_dry_run.json"
    execution_snapshot = tmp_path / "execution_snapshot.json"
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
    operations_bundle = tmp_path / "operations_bundle.json"
    phase_gate = tmp_path / "phase_gate.json"
    operation_chain.write_text(
        "\n".join(
            [
                '{"operation":"daemon_dry_run","status":"planned","scheduled_for":"2026-05-24T12:30:00+00:00","command":"uv run sis paper-step","artifacts":["a.json"],"notes":["dry_run"]}',
                '{"operation":"daemon_dry_run","status":"blocked","scheduled_for":"2026-05-24T13:00:00+00:00","command":"uv run sis paper-step","artifacts":["b.json"],"notes":["kill_switch"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(monitoring, {"status": "degraded"})
    write_json(daemon_dry_run, {"status": "blocked"})
    write_json(execution_snapshot, {"overall_status": "ok", "venue_count": 2})
    write_json(
        audit_dashboard,
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
            "timeline_latest_execution_overall_status": "ok",
            "timeline_latest_execution_venue_count": 2,
            "timeline_latest_execution_comparison_all_registries_present": True,
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        audit_bundle,
        {
            "bundle_history_snapshot_count": 3,
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
        },
    )
    write_json(
        operations_bundle,
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
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )

    report = build_ops_review_report(
        operation_chain_path=operation_chain,
        monitoring_snapshot_path=monitoring,
        daemon_dry_run_path=daemon_dry_run,
        execution_snapshot_summary_path=execution_snapshot,
        audit_dashboard_summary_path=audit_dashboard,
        audit_bundle_summary_path=audit_bundle,
        operations_bundle_manifest_path=operations_bundle,
        phase_gate_summary_path=phase_gate,
        out_path=tmp_path / "ops_review.md",
        summary_path=tmp_path / "ops_review_summary.json",
    )

    assert "Ops Review Report" in report
    assert "operations_count: 2" in report
    assert "latest_status: blocked" in report
    assert "planned: 1" in report
    assert "blocked: 1" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "bundle_history_latest_execution_overall_status: ok" in report
    assert "bundle_history_latest_execution_venue_count: 2" in report
    assert "bundle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "cycle_history_latest_execution_overall_status: ok" in report
    assert "cycle_history_latest_execution_venue_count: 2" in report
    assert "cycle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "audit_latest_operation: audit_bundle_snapshot" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "## Quick Navigation" in report
    assert f"- ops_review_report: {tmp_path / 'ops_review.md'}" in report
    assert "## Related Reports" in report
    assert f"- operations_dashboard_report: {tmp_path / 'reports/operations_dashboard.md'}" in report
    summary = read_json(tmp_path / "ops_review_summary.json")
    assert isinstance(summary, dict)
    assert summary["quick_navigation"]["ops_review_report"] == str(tmp_path / "ops_review.md")
    assert (
        summary["related_reports"]["operations_dashboard_report"]
        == str(tmp_path / "reports/operations_dashboard.md")
    )
    assert summary["audit_summary"]["audit_overall_status"] == "ok"
    assert summary["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["bundle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert summary["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"


def test_build_operations_dashboard(tmp_path) -> None:
    monitoring = tmp_path / "monitoring.json"
    ops_summary = tmp_path / "ops_review_summary.json"
    operations_timeline = tmp_path / "operations_timeline.json"
    decision_summary = tmp_path / "decision_summary.json"
    execution_snapshot = tmp_path / "execution_snapshot.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_balance_status = tmp_path / "execution_balance_status.json"
    execution_fill_status = tmp_path / "execution_fill_status.json"
    execution_order_status = tmp_path / "execution_order_status.json"
    execution_cancel_order = tmp_path / "execution_cancel_order.json"
    execution_close_position = tmp_path / "execution_close_position.json"
    execution_reconcile_positions = tmp_path / "execution_reconcile_positions.json"
    execution_read_only_surfaces = tmp_path / "execution_read_only_surfaces.json"
    daemon_manifest = tmp_path / "daemon_manifest.json"
    state_export = tmp_path / "state_export.json"
    state_restore = tmp_path / "state_restore.json"
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
    operations_bundle = tmp_path / "operations_bundle.json"
    phase_gate = tmp_path / "phase_gate.json"
    comparison = tmp_path / "comparison.md"
    weekly = tmp_path / "weekly.md"
    lifecycle = tmp_path / "lifecycle.md"
    execution_comparison = tmp_path / "execution_comparison.json"
    write_json(
        monitoring,
        {
            "status": "degraded",
            "decision_summary_exists": True,
            "daily_pnl_exists": True,
            "operation_chain_exists": True,
        },
    )
    write_json(
        ops_summary,
        {
            "operations_count": 3,
            "latest_operation": "daemon_dry_run",
            "latest_status": "blocked",
            "latest_scheduled_for": "2026-05-24T12:30:00+00:00",
        },
    )
    write_json(
        operations_timeline,
        {
            "latest_remediation_planner_status": "stalled",
            "latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "latest_remediation_execution_plan_status": "stalled",
            "latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "latest_remediation_session_status": "ready_for_dry_run",
            "latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "latest_remediation_checkpoint_status": "retry_pending",
            "latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "latest_remediation_scoreboard_status": "retrying",
            "latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
        },
    )
    write_json(
        decision_summary,
        {
            "mode": "signal_driven",
            "executed_count": 2,
            "blocked_count": 1,
        },
    )
    write_json(execution_snapshot, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(
        execution_diagnostics,
        {"overall_status": "degraded", "balance_gap_detected": True, "fills_gap_detected": False},
    )
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"})
    write_json(
        execution_drift_overview,
        {
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
    )
    write_json(
        execution_balance_status,
        {
            "venue": "gtrade",
            "currency": "USD",
            "equity": 1500.0,
            "available_cash": 1200.0,
            "balance_snapshot_exists": True,
            "balance_status_report_path": "data/reports/execution_balance_status.md",
        },
    )
    write_json(
        execution_fill_status,
        {
            "venue": "gtrade",
            "fills_count": 1,
            "latest_fill_id": "fill-1",
            "latest_fill_status": "filled",
            "fill_status_report_path": "data/reports/execution_fill_status.md",
        },
    )
    write_json(
        execution_order_status,
        {
            "venue": "gtrade",
            "order_id": "ord-1",
            "status": "working",
            "symbol": "QQQ",
            "order_status_report_path": "data/reports/execution_order_status.md",
        },
    )
    write_json(
        execution_cancel_order,
        {
            "venue": "gtrade",
            "action": "cancel_order",
            "target": "ord-1",
            "success": False,
            "status": "blocked_read_only",
            "cancel_order_report_path": "data/reports/execution_cancel_order.md",
        },
    )
    write_json(
        execution_close_position,
        {
            "venue": "gtrade",
            "action": "close_position",
            "target": "QQQ:long",
            "success": False,
            "status": "blocked_read_only",
            "close_position_report_path": "data/reports/execution_close_position.md",
        },
    )
    write_json(
        execution_reconcile_positions,
        {
            "venue": "ostium",
            "run_id": "20260525_000000",
            "matched": 1,
            "missing_in_adapter_count": 0,
            "missing_in_internal_count": 0,
            "reconcile_positions_report_path": "data/reports/execution_reconcile_positions.md",
        },
    )
    write_json(
        execution_read_only_surfaces,
        {
            "venue_count": 2,
            "with_balance_snapshot_count": 1,
            "with_positions_snapshot_count": 2,
            "with_fills_snapshot_count": 1,
            "with_order_status_snapshot_count": 1,
            "reconciled_venue_count": 2,
            "execution_read_only_surfaces_report_path": "data/reports/execution_read_only_surfaces.md",
        },
    )
    write_json(
        daemon_manifest,
        {
            "mode": "paper",
            "command": "uv run sis paper-step",
            "state_store_path": "data/state/marketlens.sqlite",
            "daemon_manifest_report_path": "data/reports/daemon_manifest.md",
        },
    )
    write_json(
        state_export,
        {
            "snapshot_path": "data/state/state_snapshot.json",
            "audit_overall_status": "ok",
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "readiness_next_phase_candidate": "Stay Phase 1",
            "state_export_report_path": "data/reports/state_export.md",
        },
    )
    write_json(
        state_restore,
        {
            "restored": True,
            "snapshot_path": "data/state/state_snapshot.json",
            "audit_overall_status": "ok",
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "state_restore_report_path": "data/reports/state_restore.md",
        },
    )
    write_json(
        audit_dashboard,
        {
            "overall_status": "ok",
            "timeline_latest_operation": "audit_bundle_snapshot",
            "audit_entry_count": 4,
            "audit_bundle_snapshot_count": 1,
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
        },
    )
    write_json(
        audit_bundle,
        {
            "bundle_history_snapshot_count": 3,
            "bundle_history_ok_count": 3,
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
        },
    )
    write_json(
        operations_bundle,
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
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )
    comparison.write_text("# comparison\n", encoding="utf-8")
    weekly.write_text("# weekly\n", encoding="utf-8")
    lifecycle.write_text("# lifecycle\n", encoding="utf-8")

    report = build_operations_dashboard(
        monitoring_snapshot_path=monitoring,
        ops_review_summary_path=ops_summary,
        operations_timeline_summary_path=operations_timeline,
        decision_summary_path=decision_summary,
        execution_snapshot_summary_path=execution_snapshot,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_drift_overview_summary_path=execution_drift_overview,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_balance_status_summary_path=execution_balance_status,
        execution_fill_status_summary_path=execution_fill_status,
        execution_order_status_summary_path=execution_order_status,
        execution_cancel_order_summary_path=execution_cancel_order,
        execution_close_position_summary_path=execution_close_position,
        execution_reconcile_positions_summary_path=execution_reconcile_positions,
        execution_read_only_surfaces_summary_path=execution_read_only_surfaces,
        daemon_manifest_summary_path=daemon_manifest,
        state_export_summary_path=state_export,
        state_restore_summary_path=state_restore,
        audit_dashboard_summary_path=audit_dashboard,
        audit_bundle_summary_path=audit_bundle,
        operations_bundle_manifest_path=operations_bundle,
        phase_gate_summary_path=phase_gate,
        comparison_report_path=comparison,
        weekly_review_path=weekly,
        lifecycle_report_path=lifecycle,
        out_path=tmp_path / "dashboard.md",
        summary_path=tmp_path / "dashboard_summary.json",
    )

    assert "Operations Dashboard" in report
    assert "overall_status: blocked" in report
    assert "operations_count: 3" in report
    assert "decision_mode: signal_driven" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_all_registries_present: True" in report
    assert "execution_diagnostics_status: degraded" in report
    assert "execution_balance_gap_detected: True" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: degraded" in report
    assert "execution_drift_overview_status: degraded" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "## Execution Adapter Surfaces" in report
    assert "## State And Daemon Surfaces" in report
    assert "daemon_manifest_mode: paper" in report
    assert "state_export_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "state_restore_restored: True" in report
    assert "execution_balance_status_equity: 1500.0" in report
    assert "execution_fill_status_latest_fill_id: fill-1" in report
    assert "execution_order_status_status: working" in report
    assert "execution_cancel_order_status: blocked_read_only" in report
    assert "execution_reconcile_positions_matched: 1" in report
    assert "audit_latest_operation: audit_bundle_snapshot" in report
    assert "audit_bundle_history_snapshot_count: 3" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert (
        "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict"
        in report
    )
    assert "timeline_latest_remediation_execution_plan_status: stalled" in report
    assert (
        "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes"
        in report
    )
    assert "timeline_latest_remediation_session_status: ready_for_dry_run" in report
    assert (
        "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status"
        in report
    )
    assert "timeline_latest_remediation_checkpoint_status: retry_pending" in report
    assert (
        "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review"
        in report
    )
    assert "timeline_latest_remediation_scoreboard_status: retrying" in report
    assert (
        "timeline_latest_remediation_scoreboard_next_action_command: uv run sis phase-gate-review"
        in report
    )
    assert "bundle_history_latest_execution_overall_status: ok" in report
    assert "bundle_history_latest_execution_venue_count: 2" in report
    assert "bundle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "cycle_history_latest_execution_overall_status: ok" in report
    assert "cycle_history_latest_execution_venue_count: 2" in report
    assert "cycle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "## Quick Navigation" in report
    assert f"- operations_dashboard_report: {tmp_path / 'dashboard.md'}" in report
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in report
    assert "## Related Reports" in report
    assert f"- current_state_index_report: {tmp_path / 'reports/current_state_index.md'}" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    summary = read_json(tmp_path / "dashboard_summary.json")
    assert isinstance(summary, dict)
    assert summary["phase2_entry_allowed"] is False
    assert summary["quick_navigation"]["operations_dashboard_report"] == str(tmp_path / "dashboard.md")
    assert (
        summary["related_reports"]["current_state_index_report"]
        == str(tmp_path / "reports/current_state_index.md")
    )
    assert summary["audit_summary"]["audit_overall_status"] == "ok"
    assert summary["timeline_latest_execution_overall_status"] == "ok"
    assert summary["timeline_latest_execution_venue_count"] == 2
    assert summary["timeline_latest_execution_comparison_all_registries_present"] is True
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert (
        summary["timeline_latest_remediation_execution_plan_next_action_command"]
        == "uv run sis diagnose-quotes"
    )
    assert summary["timeline_latest_remediation_session_next_pending_command"] == "uv run sis monitoring-status"
    assert (
        summary["timeline_latest_remediation_scoreboard_next_action_command"]
        == "uv run sis phase-gate-review"
    )
    assert summary["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["bundle_history_latest_execution_overall_status"] == "ok"
    assert summary["bundle_history_latest_execution_venue_count"] == 2
    assert summary["bundle_history_latest_execution_comparison_all_registries_present"] is True
    assert summary["bundle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert summary["execution_balance_status_equity"] == 1500.0
    assert summary["execution_fill_status_latest_fill_id"] == "fill-1"
    assert summary["execution_order_status_status"] == "working"
    assert summary["execution_cancel_order_status"] == "blocked_read_only"
    assert summary["execution_reconcile_positions_matched"] == 1
    assert summary["daemon_manifest_mode"] == "paper"
    assert summary["state_export_phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert summary["state_restore_restored"] is True
    assert (
        summary["execution_snapshot_drift_summary"][
            "execution_snapshot_drift_mismatching_snapshot_count"
        ]
        == 1
    )
    assert summary["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"


def test_build_current_state_index(tmp_path) -> None:
    operations_dashboard = tmp_path / "operations_dashboard.json"
    operations_bundle = tmp_path / "operations_bundle.json"
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
    phase_gate = tmp_path / "phase_gate.json"
    execution_snapshot = tmp_path / "execution_snapshot.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    backtest_summary = tmp_path / "backtest_metrics_summary.json"
    live_evidence_summary = tmp_path / "live_evidence_summary.json"
    research_quality = tmp_path / "research_quality_report.md"

    write_json(
        operations_dashboard,
        {
            "overall_status": "ok",
            "execution_balance_status_venue": "gtrade",
            "execution_balance_status_currency": "USD",
            "execution_balance_status_equity": 1500.0,
            "execution_balance_status_available_cash": 1200.0,
            "execution_fill_status_fills_count": 1,
            "execution_fill_status_latest_fill_id": "fill-1",
            "execution_fill_status_latest_fill_status": "filled",
            "execution_order_status_order_id": "ord-1",
            "execution_order_status_status": "working",
            "execution_cancel_order_target": "ord-1",
            "execution_cancel_order_status": "blocked_read_only",
            "execution_close_position_target": "QQQ:long",
            "execution_close_position_status": "blocked_read_only",
            "execution_reconcile_positions_matched": 1,
            "execution_reconcile_positions_missing_in_adapter_count": 0,
            "execution_reconcile_positions_missing_in_internal_count": 0,
            "execution_read_only_surfaces_venue_count": 2,
            "execution_read_only_surfaces_with_balance_snapshot_count": 1,
            "execution_read_only_surfaces_with_positions_snapshot_count": 2,
            "execution_read_only_surfaces_with_fills_snapshot_count": 1,
            "execution_read_only_surfaces_with_order_status_snapshot_count": 1,
            "execution_read_only_surfaces_reconciled_venue_count": 2,
            "execution_read_only_surfaces_report_path": "data/reports/execution_read_only_surfaces.md",
            "daemon_manifest_mode": "paper",
            "daemon_manifest_command": "uv run sis paper-step",
            "daemon_manifest_state_store_path": "data/state/marketlens.sqlite",
            "state_export_snapshot_path": "data/state/state_snapshot.json",
            "state_export_audit_overall_status": "ok",
            "state_export_phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "state_export_readiness_next_phase_candidate": "Stay Phase 1",
            "state_restore_restored": True,
            "state_restore_snapshot_path": "data/state/state_snapshot.json",
            "state_restore_audit_overall_status": "ok",
            "state_restore_phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        operations_bundle,
        {
            "cycle_count": 2,
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
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        audit_dashboard,
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
            "timeline_latest_execution_overall_status": "ok",
            "timeline_latest_execution_venue_count": 2,
            "timeline_latest_execution_comparison_all_registries_present": True,
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        audit_bundle,
        {
            "bundle_history_snapshot_count": 3,
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
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(execution_snapshot, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(execution_diagnostics, {"overall_status": "ok"})
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "ok"})
    write_json(
        execution_state_comparison,
        {
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "ok",
            "latest_status_match": True,
            "mismatching_count": 0,
        },
    )
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "ok",
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 0,
        },
    )
    write_json(
        execution_drift_overview,
        {
            "overall_status": "ok",
            "diagnostics_alignment_match": True,
            "state_comparison_mismatching_count": 0,
            "snapshot_drift_mismatching_snapshot_count": 0,
        },
    )
    write_json(
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )
    write_json(
        backtest_summary,
        {
            "total_trade_count": 5,
            "symbols": ["QQQ", "SPY"],
        },
    )
    write_json(
        live_evidence_summary,
        {
            "run_id": "20260522_2308",
            "status": "completed",
            "decision": "GO",
        },
    )
    research_quality.write_text("# Research Quality\n", encoding="utf-8")

    report = build_current_state_index(
        operations_dashboard_summary_path=operations_dashboard,
        operations_bundle_manifest_path=operations_bundle,
        audit_dashboard_summary_path=audit_dashboard,
        audit_bundle_manifest_path=audit_bundle,
        phase_gate_summary_path=phase_gate,
        execution_snapshot_summary_path=execution_snapshot,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_drift_overview_summary_path=execution_drift_overview,
        backtest_metrics_summary_path=backtest_summary,
        live_evidence_summary_path=live_evidence_summary,
        research_quality_report_path=research_quality,
        out_path=tmp_path / "current_state_index.md",
        summary_path=tmp_path / "current_state_index.json",
    )

    assert "Current State Index" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_strict_validation_issue_count: 2" in report
    assert "phase_gate_checked_files: 7" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "bundle_history_latest_execution_overall_status: ok" in report
    assert "bundle_history_latest_execution_venue_count: 2" in report
    assert "bundle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "cycle_history_latest_execution_overall_status: ok" in report
    assert "cycle_history_latest_execution_venue_count: 2" in report
    assert "cycle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "## Execution Adapter Surfaces" in report
    assert "execution_balance_status_equity: 1500.0" in report
    assert "execution_fill_status_latest_fill_id: fill-1" in report
    assert "execution_order_status_status: working" in report
    assert "execution_cancel_order_status: blocked_read_only" in report
    assert "execution_reconcile_positions_matched: 1" in report
    assert "execution_read_only_surfaces_venue_count: 2" in report
    assert "execution_read_only_surfaces_with_positions_snapshot_count: 2" in report
    assert "## State And Daemon Surfaces" in report
    assert "daemon_manifest_mode: paper" in report
    assert "state_export_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "state_restore_restored: True" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_ready: True" in report
    assert "execution_diagnostics_status: ok" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: ok" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: True" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_drift_overview_status: ok" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 0" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 0" in report
    assert "backtest_total_trade_count: 5" in report
    assert "live_evidence_run_id: 20260522_2308" in report
    assert "live_evidence_report_path: docs/live_evidence_reports/live_evidence_report_20260522_2308.md" in report
    assert "research_quality_report_exists: True" in report
    assert "## Quick Navigation" in report
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in report
    assert "## Related Reports" in report
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in report
    assert "- live_evidence_report: docs/live_evidence_reports/live_evidence_report_20260522_2308.md" in report
    assert "## Restart Pointers" in report
    assert f"- current_state_index_report: {tmp_path / 'current_state_index.md'}" in report
    assert f"- readiness_snapshot_report: {tmp_path / 'reports/readiness_snapshot.md'}" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'reports/remediation_scoreboard.md'}" in report
    assert "## Recommended Read Order" in report
    summary = read_json(tmp_path / "current_state_index.json")
    assert isinstance(summary, dict)
    assert summary["recommended_read_order"][0] == "docs/ACCEPTANCE_AUDIT.md"
    assert summary["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["phase_gate_strict_validation_passed"] is True
    assert summary["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["phase_gate_strict_validation_issues"][0]["path"] == "data/research/backtest_metrics_summary.json"
    assert summary["timeline_latest_execution_overall_status"] == "ok"
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert summary["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"
    assert summary["live_evidence_report_path"] == "docs/live_evidence_reports/live_evidence_report_20260522_2308.md"
    assert summary["quick_navigation"]["phase_gate_review_report"] == "data/reports/phase_gate_review.md"
    assert summary["related_reports"]["phase_gate_review_report"] == "data/reports/phase_gate_review.md"
    assert summary["restart_pointers"]["current_state_index_report"] == str(
        tmp_path / "current_state_index.md"
    )
    assert summary["restart_pointers"]["remediation_scoreboard_report"] == str(
        tmp_path / "reports/remediation_scoreboard.md"
    )
    assert summary["bundle_history_latest_execution_overall_status"] == "ok"
    assert summary["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["bundle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["audit_summary"]["audit_overall_status"] == "ok"
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "ok"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert summary["execution_state_comparison_summary"]["execution_state_comparison_entry_count"] == 4
    assert summary["execution_snapshot_drift_summary"]["execution_snapshot_drift_entry_count"] == 3
    assert summary["execution_drift_overview_summary"]["execution_drift_overview_status"] == "ok"


def test_build_readiness_snapshot(tmp_path) -> None:
    current_state = tmp_path / "current_state_index.json"
    phase_gate = tmp_path / "phase_gate.json"
    execution = tmp_path / "execution_snapshot.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    backtest = tmp_path / "backtest_metrics_summary.json"
    live_evidence = tmp_path / "live_evidence_summary.json"
    operations = tmp_path / "operations_dashboard_summary.json"

    write_json(
        current_state,
        {
            "overall_status": "ok",
            "research_quality_report_exists": True,
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "warn",
                "execution_venue_count": 1,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": False,
            },
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        phase_gate,
        {
            "decision": "GO",
            "phase2_entry_allowed": True,
            "phase2_entry_reason": "decision_cleared_and_phase1_gate_complete",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 0,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [],
        },
    )
    write_json(execution, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(execution_diagnostics, {"overall_status": "ok"})
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "ok"})
    write_json(
        execution_state_comparison,
        {
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "ok",
            "latest_status_match": True,
            "mismatching_count": 0,
        },
    )
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "ok",
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 0,
        },
    )
    write_json(
        execution_drift_overview,
        {
            "overall_status": "ok",
            "diagnostics_alignment_match": True,
            "state_comparison_mismatching_count": 0,
            "snapshot_drift_mismatching_snapshot_count": 0,
        },
    )
    write_json(backtest, {"total_trade_count": 5})
    write_json(live_evidence, {"status": "completed", "decision": "GO"})
    write_json(operations, {"overall_status": "ok"})
    write_json(
        operations,
        {
            "overall_status": "ok",
            "execution_balance_status_venue": "gtrade",
            "execution_balance_status_currency": "USD",
            "execution_balance_status_equity": 1500.0,
            "execution_balance_status_available_cash": 1200.0,
            "execution_fill_status_fills_count": 1,
            "execution_fill_status_latest_fill_id": "fill-1",
            "execution_fill_status_latest_fill_status": "filled",
            "execution_order_status_order_id": "ord-1",
            "execution_order_status_status": "working",
            "execution_cancel_order_target": "ord-1",
            "execution_cancel_order_status": "blocked_read_only",
            "execution_close_position_target": "QQQ:long",
            "execution_close_position_status": "blocked_read_only",
            "execution_reconcile_positions_matched": 1,
            "execution_reconcile_positions_missing_in_adapter_count": 0,
            "execution_reconcile_positions_missing_in_internal_count": 0,
            "execution_read_only_surfaces_venue_count": 2,
            "execution_read_only_surfaces_with_balance_snapshot_count": 1,
            "execution_read_only_surfaces_with_positions_snapshot_count": 2,
            "execution_read_only_surfaces_with_fills_snapshot_count": 1,
            "execution_read_only_surfaces_with_order_status_snapshot_count": 1,
            "execution_read_only_surfaces_reconciled_venue_count": 2,
            "execution_read_only_surfaces_report_path": "data/reports/execution_read_only_surfaces.md",
            "daemon_manifest_mode": "paper",
            "daemon_manifest_command": "uv run sis paper-step",
            "daemon_manifest_state_store_path": "data/state/marketlens.sqlite",
            "state_export_snapshot_path": "data/state/state_snapshot.json",
            "state_export_audit_overall_status": "ok",
            "state_export_phase_gate_decision": "GO",
            "state_export_readiness_next_phase_candidate": "Phase 2",
            "state_restore_restored": True,
            "state_restore_snapshot_path": "data/state/state_snapshot.json",
            "state_restore_audit_overall_status": "ok",
            "state_restore_phase_gate_decision": "GO",
        },
    )

    report = build_readiness_snapshot(
        current_state_index_path=current_state,
        phase_gate_summary_path=phase_gate,
        execution_snapshot_summary_path=execution,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_drift_overview_summary_path=execution_drift_overview,
        backtest_metrics_summary_path=backtest,
        live_evidence_summary_path=live_evidence,
        operations_dashboard_summary_path=operations,
        out_path=tmp_path / "readiness_snapshot.md",
        summary_path=tmp_path / "readiness_snapshot.json",
    )

    assert "Readiness Snapshot" in report
    assert "next_phase_candidate: Phase 2" in report
    assert "phase_gate_reason: decision_cleared_and_phase1_gate_complete" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "issues: none" in report
    assert "execution_ready: True" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: ok" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: True" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_drift_overview_status: ok" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 0" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 0" in report
    assert "backtest_ready: True" in report
    assert "live_evidence_ready: True" in report
    assert "operations_ready: True" in report
    assert "## Execution Adapter Surfaces" in report
    assert "execution_balance_status_equity: 1500.0" in report
    assert "execution_fill_status_latest_fill_id: fill-1" in report
    assert "execution_order_status_status: working" in report
    assert "execution_cancel_order_status: blocked_read_only" in report
    assert "execution_reconcile_positions_matched: 1" in report
    assert "## State And Daemon Surfaces" in report
    assert "daemon_manifest_mode: paper" in report
    assert "state_export_phase_gate_decision: GO" in report
    assert "state_restore_restored: True" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "bundle_history_latest_execution_overall_status: warn" in report
    assert "bundle_history_latest_execution_venue_count: 1" in report
    assert "bundle_history_latest_execution_comparison_all_registries_present: False" in report
    assert "cycle_history_latest_execution_overall_status: ok" in report
    assert "cycle_history_latest_execution_venue_count: 2" in report
    assert "cycle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "## Quick Navigation" in report
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in report
    assert "## Related Reports" in report
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in report
    assert "## Restart Pointers" in report
    assert f"- readiness_snapshot_report: {tmp_path / 'readiness_snapshot.md'}" in report
    assert f"- current_state_index_report: {tmp_path / 'reports/current_state_index.md'}" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'reports/remediation_scoreboard.md'}" in report
    assert "live_evidence_report_path: None" in report
    summary = read_json(tmp_path / "readiness_snapshot.json")
    assert isinstance(summary, dict)
    assert summary["phase2_entry_allowed"] is True
    assert summary["execution_ready"] is True
    assert summary["readiness_next_phase_candidate"] == "Phase 2"
    assert summary["readiness_execution_ready"] is True
    assert summary["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert summary["phase_gate_strict_validation_passed"] is True
    assert summary["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert summary["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["bundle_history_latest_execution_summary"]["execution_overall_status"] == "warn"
    assert (
        summary["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is False
    )
    assert summary["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "ok"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert summary["execution_state_comparison_summary"]["execution_state_comparison_entry_count"] == 4
    assert summary["execution_snapshot_drift_summary"]["execution_snapshot_drift_entry_count"] == 3
    assert summary["execution_drift_overview_summary"]["execution_drift_overview_status"] == "ok"
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert summary["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"
    assert summary["execution_balance_status_equity"] == 1500.0
    assert summary["execution_fill_status_latest_fill_id"] == "fill-1"
    assert summary["execution_order_status_status"] == "working"
    assert summary["execution_cancel_order_status"] == "blocked_read_only"
    assert summary["execution_reconcile_positions_matched"] == 1
    assert summary["execution_read_only_surfaces_venue_count"] == 2
    assert summary["execution_read_only_surfaces_with_positions_snapshot_count"] == 2
    assert summary["daemon_manifest_mode"] == "paper"
    assert summary["state_export_phase_gate_decision"] == "GO"
    assert summary["state_restore_restored"] is True
    assert summary["live_evidence_report_path"] is None
    assert summary["quick_navigation"]["phase_gate_review_report"] == "data/reports/phase_gate_review.md"
    assert summary["related_reports"]["phase_gate_review_report"] == "data/reports/phase_gate_review.md"
    assert summary["restart_pointers"]["remediation_scoreboard_report"] == str(
        tmp_path / "reports/remediation_scoreboard.md"
    )


def test_build_execution_gap_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_execution_gap_history_report(
        operation_chain_path=operation_chain,
        out_path=tmp_path / "execution_gap_history.md",
        summary_path=tmp_path / "execution_gap_history.json",
    )

    assert "Execution Gap History Report" in report
    assert "## Quick Navigation" in report
    assert f"- execution_gap_history_report: {tmp_path / 'execution_gap_history.md'}" in report
    assert "## Related Reports" in report
    assert f"- execution_state_comparison_report: {tmp_path / 'execution_state_comparison_history.md'}" in report
    assert "entry_count: 3" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_diagnostics_status: degraded" in report
    assert "latest_readiness_next_phase: Phase 1" in report
    assert "latest_readiness_execution_ready: False" in report
    assert "degraded: 2" in report
    assert "ok: 1" in report
    summary = read_json(tmp_path / "execution_gap_history.json")
    assert summary["execution_gap_history_entry_count"] == 3
    assert summary["execution_gap_history_latest_status"] == "ok"
    assert summary["execution_gap_history_latest_diagnostics_status"] == "degraded"
    assert summary["execution_gap_history_report_path"] == str(tmp_path / "execution_gap_history.md")
    assert summary["quick_navigation"]["execution_gap_history_report"] == str(
        tmp_path / "execution_gap_history.md"
    )
    assert summary["related_reports"]["execution_state_comparison_report"] == str(
        tmp_path / "execution_state_comparison_history.md"
    )
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_readiness_summary"]["readiness_execution_ready"] == "False"


def test_build_execution_state_comparison_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=ok","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_execution_state_comparison_history_report(
        operation_chain_path=operation_chain,
        out_path=tmp_path / "execution_state_comparison_history.md",
        summary_path=tmp_path / "execution_state_comparison_history.json",
    )

    assert "Execution State Comparison History" in report
    assert "## Quick Navigation" in report
    assert (
        f"- execution_state_comparison_report: {tmp_path / 'execution_state_comparison_history.md'}"
        in report
    )
    assert "## Related Reports" in report
    assert f"- execution_snapshot_drift_report: {tmp_path / 'execution_snapshot_drift_history.md'}" in report
    assert "entry_count: 3" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_diagnostics_status: degraded" in report
    assert "latest_execution_gap_history_diagnostics_status: ok" in report
    assert "latest_status_match: False" in report
    assert "matching_count: 2" in report
    assert "mismatching_count: 1" in report
    summary = read_json(tmp_path / "execution_state_comparison_history.json")
    assert summary["execution_state_comparison_entry_count"] == 3
    assert summary["execution_state_comparison_latest_status"] == "ok"
    assert summary["execution_state_comparison_latest_diagnostics_status"] == "degraded"
    assert summary["execution_state_comparison_latest_status_match"] is False
    assert summary["execution_state_comparison_mismatching_count"] == 1
    assert summary["execution_state_comparison_report_path"] == str(
        tmp_path / "execution_state_comparison_history.md"
    )
    assert summary["quick_navigation"]["execution_state_comparison_report"] == str(
        tmp_path / "execution_state_comparison_history.md"
    )
    assert summary["related_reports"]["execution_snapshot_drift_report"] == str(
        tmp_path / "execution_snapshot_drift_history.md"
    )
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert (
        summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_diagnostics_status"]
        == "ok"
    )


def test_build_execution_snapshot_drift_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_execution_snapshot_drift_history_report(
        operation_chain_path=operation_chain,
        out_path=tmp_path / "execution_snapshot_drift_history.md",
        summary_path=tmp_path / "execution_snapshot_drift_history.json",
    )

    assert "Execution Snapshot Drift History" in report
    assert "## Quick Navigation" in report
    assert (
        f"- execution_snapshot_drift_report: {tmp_path / 'execution_snapshot_drift_history.md'}"
        in report
    )
    assert "## Related Reports" in report
    assert f"- execution_drift_overview_report: {tmp_path / 'execution_drift_overview.md'}" in report
    assert "entry_count: 3" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_diagnostics_status: degraded" in report
    assert "latest_execution_gap_history_diagnostics_status: ok" in report
    assert "latest_execution_state_comparison_status_match: False" in report
    assert "latest_execution_state_comparison_mismatching_count: 1" in report
    assert "matching_snapshot_count: 2" in report
    assert "mismatching_snapshot_count: 1" in report
    summary = read_json(tmp_path / "execution_snapshot_drift_history.json")
    assert summary["execution_snapshot_drift_entry_count"] == 3
    assert summary["execution_snapshot_drift_latest_status"] == "ok"
    assert summary["execution_snapshot_drift_latest_diagnostics_status"] == "degraded"
    assert summary["execution_snapshot_drift_latest_status_match"] == "False"
    assert summary["execution_snapshot_drift_latest_mismatching_count"] == "1"
    assert summary["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert summary["execution_snapshot_drift_report_path"] == str(
        tmp_path / "execution_snapshot_drift_history.md"
    )
    assert summary["quick_navigation"]["execution_snapshot_drift_report"] == str(
        tmp_path / "execution_snapshot_drift_history.md"
    )
    assert summary["related_reports"]["execution_drift_overview_report"] == str(
        tmp_path / "execution_drift_overview.md"
    )
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert (
        summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_diagnostics_status"]
        == "ok"
    )
    assert (
        summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"]
        == "1"
    )
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"


def test_build_execution_drift_overview_report(tmp_path) -> None:
    gap_history = tmp_path / "execution_gap_history.json"
    state_comparison = tmp_path / "execution_state_comparison.json"
    snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    write_json(
        gap_history,
        {
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
        },
    )
    write_json(
        state_comparison,
        {
            "latest_execution_diagnostics_status": "degraded",
            "latest_execution_gap_history_diagnostics_status": "degraded",
            "latest_status_match": True,
            "mismatching_count": 0,
        },
    )
    write_json(
        snapshot_drift,
        {
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 0,
        },
    )

    report = build_execution_drift_overview_report(
        execution_gap_history_summary_path=gap_history,
        execution_state_comparison_history_summary_path=state_comparison,
        execution_snapshot_drift_history_summary_path=snapshot_drift,
        out_path=tmp_path / "execution_drift_overview.md",
        summary_path=tmp_path / "execution_drift_overview.json",
    )

    assert "Execution Drift Overview" in report
    assert "## Quick Navigation" in report
    assert f"- execution_drift_overview_report: {tmp_path / 'execution_drift_overview.md'}" in report
    assert "## Related Reports" in report
    assert f"- execution_snapshot_report: {tmp_path / 'execution_snapshot.md'}" in report
    assert "overall_status: ok" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "diagnostics_alignment_match: True" in report
    summary = read_json(tmp_path / "execution_drift_overview.json")
    assert summary["execution_drift_overview_status"] == "ok"
    assert summary["execution_drift_overview_diagnostics_alignment_match"] is True
    assert summary["execution_drift_overview_state_comparison_mismatching_count"] == 0
    assert summary["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] == 0
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["execution_drift_overview_report_path"] == str(
        tmp_path / "execution_drift_overview.md"
    )
    assert summary["quick_navigation"]["execution_drift_overview_report"] == str(
        tmp_path / "execution_drift_overview.md"
    )
    assert summary["related_reports"]["execution_snapshot_report"] == str(
        tmp_path / "execution_snapshot.md"
    )
    assert summary["execution_gap_history_summary"]["execution_gap_history_latest_diagnostics_status"] == "degraded"
    assert (
        summary["execution_state_comparison_summary"]["execution_state_comparison_latest_status_match"]
        is True
    )
    assert (
        summary["execution_snapshot_drift_summary"]["execution_snapshot_drift_mismatching_snapshot_count"]
        == 0
    )


def test_build_execution_balance_status_report(tmp_path) -> None:
    out_path = tmp_path / "execution_balance_status.md"
    summary_path = tmp_path / "execution_balance_status_summary.json"

    text = build_balance_status_report(
        venue="gtrade",
        balance={
            "venue": "gtrade",
            "currency": "USD",
            "equity": 1500.0,
            "available_cash": 1200.0,
            "balance_snapshot_exists": True,
            "mode": "read_only",
        },
        out_path=out_path,
        summary_path=summary_path,
    )

    assert "Execution Balance Status" in text
    assert "## Quick Navigation" in text
    summary = read_json(summary_path)
    assert summary["venue"] == "gtrade"
    assert summary["equity"] == 1500.0
    assert summary["quick_navigation"]["execution_adapter_report"] == str(out_path)


def test_build_execution_fill_status_report(tmp_path) -> None:
    out_path = tmp_path / "execution_fill_status.md"
    summary_path = tmp_path / "execution_fill_status_summary.json"

    text = build_fill_status_report(
        venue="gtrade",
        fills=[
            AdapterFillSnapshot(
                venue="gtrade",
                fill_id="fill-1",
                order_id="ord-1",
                canonical_symbol="QQQ",
                side="long",
                quantity=1.0,
                price=100.5,
                status="filled",
                ts_fill="2026-05-24T00:00:00+00:00",
                notes=["read_only_adapter", "snapshot_fill"],
            )
        ],
        limit=10,
        out_path=out_path,
        summary_path=summary_path,
    )

    assert "fill_1_id: fill-1" in text
    summary = read_json(summary_path)
    assert summary["fills_count"] == 1
    assert summary["latest_fill_id"] == "fill-1"


def test_build_execution_order_and_action_reports(tmp_path) -> None:
    order_out = tmp_path / "execution_order_status.md"
    order_summary = tmp_path / "execution_order_status_summary.json"
    cancel_out = tmp_path / "execution_cancel_order.md"
    cancel_summary = tmp_path / "execution_cancel_order_summary.json"

    order_text = build_order_status_report(
        status=AdapterOrderStatus(
            venue="gtrade",
            order_id="ord-1",
            canonical_symbol="QQQ",
            side="long",
            quantity=1.0,
            status="working",
            notes=["read_only_adapter", "snapshot_status"],
        ),
        out_path=order_out,
        summary_path=order_summary,
    )
    cancel_text = build_action_status_report(
        title="Execution Cancel Order",
        report_key="cancel_order_report_path",
        result=AdapterActionResult(
            venue="gtrade",
            action="cancel_order",
            target="ord-1",
            success=False,
            status="blocked_read_only",
            notes=["read_only_adapter", "cancel_not_available"],
        ),
        out_path=cancel_out,
        summary_path=cancel_summary,
    )

    assert "status: working" in order_text
    assert "status: blocked_read_only" in cancel_text
    assert read_json(order_summary)["order_id"] == "ord-1"
    assert read_json(cancel_summary)["action"] == "cancel_order"


def test_build_execution_reconcile_positions_report(tmp_path) -> None:
    out_path = tmp_path / "execution_reconcile_positions.md"
    summary_path = tmp_path / "execution_reconcile_positions_summary.json"

    text = build_reconcile_positions_report(
        venue="ostium",
        result=ReconciliationResult(
            matched=1,
            missing_in_adapter=[{"venue": "ostium", "canonical_symbol": "SPY", "side": "long"}],
            missing_in_internal=[],
        ),
        run_id="20260525_000000",
        state_store_path=str(tmp_path / "marketlens.sqlite"),
        out_path=out_path,
        summary_path=summary_path,
    )

    assert "Execution Position Reconciliation" in text
    summary = read_json(summary_path)
    assert summary["matched"] == 1
    assert summary["missing_in_adapter_count"] == 1
    assert summary["run_id"] == "20260525_000000"


def test_build_execution_read_only_surfaces_report(tmp_path) -> None:
    out_path = tmp_path / "execution_read_only_surfaces.md"
    summary_path = tmp_path / "execution_read_only_surfaces_summary.json"

    text = build_execution_read_only_surfaces_report(
        venue_surfaces=[
            {
                "venue": "gtrade",
                "balance_snapshot_exists": True,
                "positions_snapshot_exists": True,
                "fills_snapshot_exists": True,
                "order_status_snapshot_exists": True,
                "equity": 1500.0,
                "fills_count": 1,
                "latest_fill_id": "fill-1",
                "order_status_count": 1,
                "latest_order_id": "ord-1",
                "latest_order_status": "working",
                "positions_count": 1,
                "reconcile_matched": 1,
                "reconcile_missing_in_adapter_count": 0,
                "reconcile_missing_in_internal_count": 0,
            },
            {
                "venue": "ostium",
                "balance_snapshot_exists": False,
                "positions_snapshot_exists": True,
                "fills_snapshot_exists": False,
                "order_status_snapshot_exists": False,
                "equity": None,
                "fills_count": 0,
                "latest_fill_id": None,
                "order_status_count": 0,
                "latest_order_id": None,
                "latest_order_status": None,
                "positions_count": 1,
                "reconcile_matched": 1,
                "reconcile_missing_in_adapter_count": 0,
                "reconcile_missing_in_internal_count": 0,
            },
        ],
        out_path=out_path,
        summary_path=summary_path,
    )

    assert "Execution Read Only Surfaces" in text
    assert "venue_count: 2" in text
    assert "venue_gtrade_latest_fill_id: fill-1" in text
    summary = read_json(summary_path)
    assert summary["venue_count"] == 2
    assert summary["with_positions_snapshot_count"] == 2
    assert summary["reconciled_venue_count"] == 2


def test_build_daemon_manifest_report(tmp_path) -> None:
    report = build_daemon_manifest_report(
        manifest={
            "run_id": "20260525_120000",
            "created_at": "2026-05-25T12:00:00+00:00",
            "mode": "paper",
            "command": "uv run sis paper-step",
            "state_store_path": "data/state/marketlens.sqlite",
            "notes": ["foundation_only", "non_daemon_runtime"],
        },
        manifest_path="data/ops/daemon_manifest.json",
        out_path=tmp_path / "daemon_manifest.md",
        summary_path=tmp_path / "daemon_manifest_summary.json",
    )

    assert "Daemon Manifest" in report
    assert "## Quick Navigation" in report
    assert f"- state_command_report: {tmp_path / 'daemon_manifest.md'}" in report
    assert "## Related Reports" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'remediation_scoreboard.md'}" in report
    summary = read_json(tmp_path / "daemon_manifest_summary.json")
    assert summary["mode"] == "paper"
    assert summary["daemon_manifest_path"] == "data/ops/daemon_manifest.json"
    assert summary["quick_navigation"]["state_command_report"] == str(tmp_path / "daemon_manifest.md")


def test_build_state_export_and_restore_report(tmp_path) -> None:
    snapshot = {
        "paper_positions": [{"symbol": "BTCUSD"}],
        "paper_last_run": {"orders_count": 1},
        "latest_reconciliation": {"run_id": "r-1"},
        "audit_overall_status": "ok",
        "audit_latest_operation": "audit_bundle_snapshot",
        "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "phase_gate_strict_validation_passed": True,
        "readiness_next_phase_candidate": "Stay Phase 1",
        "readiness_execution_ready": False,
        "execution_drift_overview_status": "degraded",
    }

    export_report = build_state_export_report(
        snapshot=snapshot,
        snapshot_path="data/state/state_snapshot.json",
        state_store_path="data/state/marketlens.sqlite",
        out_path=tmp_path / "state_export.md",
        summary_path=tmp_path / "state_export_summary.json",
    )
    restore_report = build_state_restore_report(
        snapshot=snapshot,
        snapshot_path="data/state/state_snapshot.json",
        state_store_path="data/state/marketlens.sqlite",
        restored=True,
        out_path=tmp_path / "state_restore.md",
        summary_path=tmp_path / "state_restore_summary.json",
    )

    assert "State Export Snapshot" in export_report
    assert "paper_positions_present: True" in export_report
    assert "State Restore Snapshot" in restore_report
    assert "restored: True" in restore_report
    export_summary = read_json(tmp_path / "state_export_summary.json")
    restore_summary = read_json(tmp_path / "state_restore_summary.json")
    assert export_summary["audit_overall_status"] == "ok"
    assert export_summary["paper_positions_present"] is True
    assert restore_summary["restored"] is True
    assert restore_summary["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"


def test_build_paper_operations_runbook(tmp_path) -> None:
    schedule = tmp_path / "scheduled_run.json"
    daemon = tmp_path / "daemon_manifest.json"
    monitoring = tmp_path / "monitoring.json"
    execution = tmp_path / "execution_snapshot.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    phase_gate = tmp_path / "phase_gate.json"
    dashboard = tmp_path / "dashboard_summary.json"
    write_json(
        schedule,
        {
            "run_type": "paper",
            "scheduled_for": "2026-05-24T12:30:00+00:00",
            "command": "uv run sis paper-step",
        },
    )
    write_json(
        daemon,
        {
            "mode": "paper",
            "command": "uv run sis paper-step",
            "state_store_path": "data/state/marketlens.sqlite",
        },
    )
    write_json(monitoring, {"status": "ok"})
    write_json(execution, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(
        execution_diagnostics,
        {"overall_status": "degraded", "balance_gap_detected": True, "fills_gap_detected": False},
    )
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"})
    write_json(execution_state_comparison, {"entry_count": 4, "latest_status_match": False, "mismatching_count": 1})
    write_json(
        execution_drift_overview,
        {
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
    )
    write_json(readiness, {"next_phase_candidate": "Stay Phase 1", "execution_ready": False})
    write_json(
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )
    write_json(
        dashboard,
        {
            "overall_status": "ok",
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )

    summary_path = tmp_path / "runbook_summary.json"
    planner_summary_path = tmp_path / "remediation_planner.json"
    evaluator_summary_path = tmp_path / "remediation_evaluator.json"
    write_json(
        summary_path,
        {
            "remediation_signal_snapshots_before": {
                "execution_drift_unresolved": {
                    "execution_drift_overview_status": "blocked",
                    "execution_state_comparison_mismatching_count": 3,
                    "execution_snapshot_drift_mismatching_snapshot_count": 2,
                }
            },
            "remediation_recommendations": {
                "execution_drift_unresolved": {
                    "status": "stalled",
                    "commands": ["uv run sis monitoring-status"],
                    "why": "signals did not move toward target",
                    "source_confidence": "medium",
                    "source_policy": "structured_summary_priority",
                }
            },
        },
    )
    write_json(
        planner_summary_path,
        {
            "entries": [
                {
                    "source": "paper_operations_runbook",
                    "reason": "execution_drift_unresolved",
                    "source_confidence": "high",
                    "source_policy": "direct_observation_priority",
                }
            ]
        },
    )
    write_json(
        evaluator_summary_path,
        {
            "actions": [
                {
                    "source": "paper_operations_runbook",
                    "reason": "execution_drift_unresolved",
                    "signal_evaluations": [
                        {
                            "signal": "execution_drift_overview_summary.json is regenerated",
                            "observed_source": "markdown_reports",
                        }
                    ],
                }
            ]
        },
    )
    report = build_paper_operations_runbook(
        scheduled_run_path=schedule,
        daemon_manifest_path=daemon,
        monitoring_snapshot_path=monitoring,
        execution_snapshot_summary_path=execution,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        phase_gate_summary_path=phase_gate,
        ops_dashboard_summary_path=dashboard,
        remediation_planner_summary_path=planner_summary_path,
        remediation_evaluator_summary_path=evaluator_summary_path,
        out_path=tmp_path / "runbook.md",
        summary_path=summary_path,
    )

    assert "Scheduled Paper Operations Runbook" in report
    assert "run_type: paper" in report
    assert "monitoring_status: ok" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_all_registries_present: True" in report
    assert "execution_diagnostics_status: degraded" in report
    assert "execution_balance_gap_detected: True" in report
    assert "execution_fills_gap_detected: False" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: degraded" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: False" in report
    assert "execution_state_comparison_mismatching_count: 1" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "execution_drift_overview_status: degraded" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "readiness_next_phase_candidate: Stay Phase 1" in report
    assert "readiness_execution_ready: False" in report
    assert "## Quick Navigation" in report
    assert f"- paper_operations_runbook_report: {tmp_path / 'runbook.md'}" in report
    assert "## Related Reports" in report
    assert f"- operations_dashboard_report: {tmp_path / 'reports/operations_dashboard.md'}" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_strict_validation_issue_count: 2" in report
    assert "phase_gate_checked_files: 7" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "## Required Artifacts" in report
    assert "missing_required_artifact_paths: none" in report
    assert "## Recovery Commands" in report
    assert "recovery_commands: none" in report
    assert "## Remediation Order" in report
    assert "priority_2: strict_validation_failed" in report
    assert "priority_3: execution_diagnostics_degraded" in report
    assert "priority_4: execution_drift_unresolved" in report
    assert "priority_5: readiness_not_cleared" in report
    assert "## Remediation Success Criteria" in report
    assert "execution_diagnostics_status == ok" in report
    assert "readiness_execution_ready == True" in report
    assert "## Remediation Command Flow" in report
    assert "`uv run sis validate-artifacts --strict`" in report
    assert "`uv run sis monitoring-status`" in report
    assert "`uv run sis paper-operations-runbook`" in report
    assert "## Remediation Verification Signals" in report
    assert "preflight_expected_output:" in report
    assert "execute_expected_output:" in report
    assert "postcheck_pass_signal:" in report
    assert "## Remediation Signal Snapshots" in report
    assert "before:" in report
    assert "target:" in report
    assert "## Remediation Signal Diffs" in report
    assert "trend=changed" in report
    assert "## Remediation Recommendations" in report
    assert "status: improving" in report
    assert "scheduled_run_path:" in report
    assert "execution_snapshot_summary_path:" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "Latest Execution Lineage" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "bundle_history_latest_execution_overall_status: ok" in report
    assert "cycle_history_latest_execution_overall_status: ok" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "## Quick Navigation" in report
    assert "- paper_operations_runbook_report:" in report
    assert "## Related Reports" in report
    assert "- paper_operations_runbook_report:" in report
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in report
    assert "Review `data/reports/remediation_scoreboard.md`" in report
    assert "dashboard_status: ok" in report
    summary = read_json(tmp_path / "runbook_summary.json")
    assert isinstance(summary, dict)
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert summary["execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == 1
    assert summary["required_artifact_paths"]["execution_snapshot_summary_path"] == str(execution)
    assert summary["missing_required_artifact_paths"] == []
    assert summary["artifact_recovery_commands"] == {}
    assert [item["priority"] for item in summary["remediation_order"]] == [2, 3, 4, 5]
    assert summary["remediation_success_criteria"]["strict_validation_failed"] == [
        "phase_gate_strict_validation_issue_count == 0"
    ]
    assert summary["remediation_success_criteria"]["readiness_not_cleared"] == [
        "readiness_execution_ready == True",
        "phase2_entry_allowed == True",
    ]
    assert summary["remediation_preflight_commands"]["strict_validation_failed"] == [
        "uv run sis validate-artifacts --strict"
    ]
    assert summary["remediation_postcheck_commands"]["readiness_not_cleared"] == [
        "uv run sis phase-gate-review",
        "uv run sis paper-operations-runbook",
    ]
    assert summary["remediation_preflight_expected_outputs"]["execution_diagnostics_degraded"] == [
        "monitoring-status prints execution_diagnostics_status",
        "monitoring output shows current balance/fills gap flags",
    ]
    assert summary["remediation_execute_expected_outputs"]["execution_drift_unresolved"] == [
        "execution_drift_overview_summary.json is regenerated",
        "drift mismatch counts are recalculated from fresh artifacts",
    ]
    assert summary["remediation_postcheck_pass_signals"]["readiness_not_cleared"] == [
        "readiness_execution_ready == True",
        "phase2_entry_allowed == True",
    ]
    assert summary["remediation_signal_snapshots_before"]["execution_drift_unresolved"] == {
        "execution_drift_overview_status": "degraded",
        "execution_state_comparison_mismatching_count": 1,
        "execution_snapshot_drift_mismatching_snapshot_count": 1,
    }
    assert summary["remediation_signal_snapshots_target"]["readiness_not_cleared"] == {
        "readiness_execution_ready": True,
        "phase2_entry_allowed": True,
    }
    assert summary["remediation_signal_snapshots_previous"]["execution_drift_unresolved"] == {
        "execution_drift_overview_status": "blocked",
        "execution_state_comparison_mismatching_count": 3,
        "execution_snapshot_drift_mismatching_snapshot_count": 2,
    }
    assert summary["remediation_signal_snapshot_diffs"]["execution_drift_unresolved"][
        "execution_state_comparison_mismatching_count"
    ] == {
        "previous": 3,
        "current": 1,
        "target": 0,
        "trend": "changed",
        "target_matched": False,
    }
    assert summary["remediation_recommendations"]["execution_drift_unresolved"] == {
        "status": "improving",
        "commands": ["uv run sis monitoring-status"],
        "why": "signals changed but low-confidence verification sources require revalidation before execute",
        "source_confidence": "high",
        "source_policy": "direct_observation_priority",
        "execute_signal_confidence": "low",
    }
    assert summary["remediation_planner_summary_path"] == str(planner_summary_path)
    assert summary["remediation_evaluator_summary_path"] == str(evaluator_summary_path)
    assert summary["execution_snapshot_drift_summary"]["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert summary["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert summary["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert summary["phase_gate_strict_validation_issue_count"] == 2
    assert summary["phase_gate_checked_files"] == 7
    assert summary["phase2_entry_allowed"] is False
    assert summary["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["related_reports"]["phase_gate_review_report"] == "data/reports/phase_gate_review.md"
    assert summary["phase_gate_strict_validation_issues"][0]["message"] == "missing field"
    assert summary["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert summary["bundle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert summary["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert summary["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"


def test_build_remediation_planner(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    evaluator = tmp_path / "remediation_evaluator.json"
    command_results = tmp_path / "remediation_command_results.json"
    operation_chain = tmp_path / "operation_manifests.jsonl"
    write_json(
        tmp_path / "remediation_planner.json",
        {
            "planner_status": "regressed",
            "planned_step_count": 3,
            "next_best_command": "uv run sis refresh-operations-artifacts",
            "recommended_command_chain": [
                "uv run sis refresh-operations-artifacts",
                "uv run sis phase-gate-review",
            ],
            "entries": [
                {
                    "source": "paper_operations_runbook",
                    "priority": 2,
                    "reason": "strict_validation_failed",
                    "status": "regressed",
                    "why": "signals regressed away from target",
                    "commands": ["uv run sis validate-artifacts --strict"],
                }
            ],
        },
    )
    operation_chain.write_text(
        '{"run_id":"20260524_010203","created_at":"2026-05-24T01:02:03+00:00","operation":"remediation_planner_dry_run","mode":"ops","command":"uv run sis remediation-planner","status":"regressed","scheduled_for":null,"parent_run_id":null,"artifacts":["/tmp/old.json"],"notes":["planner_status=regressed","rerun_trend=regressed","planned_step_count=3","next_best_command=uv run sis refresh-operations-artifacts"]}\n',
        encoding="utf-8",
    )
    write_json(
        phase_gate,
        {
            "remediation_order": [
                {"priority": 4, "reason": "execution_drift_unresolved", "commands": ["uv run sis refresh-operations-artifacts"]}
            ],
            "remediation_recommendations": {
                "execution_drift_unresolved": {
                    "status": "improving",
                    "why": "signals changed but target is not fully matched yet",
                    "commands": ["uv run sis refresh-operations-artifacts"],
                }
            },
        },
    )
    write_json(
        runbook,
        {
            "remediation_order": [
                {"priority": 2, "reason": "strict_validation_failed", "commands": ["uv run sis validate-artifacts --strict"]}
            ],
            "remediation_recommendations": {
                "strict_validation_failed": {
                    "status": "stalled",
                    "why": "signals did not move toward target",
                    "commands": ["uv run sis validate-artifacts --strict"],
                }
            },
        },
    )
    write_json(
        evaluator,
        {
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "source": "paper_operations_runbook",
                    "reason": "strict_validation_failed",
                    "signal_evaluations": [
                        {
                            "signal": "validate-artifacts --strict reports the current issue count",
                            "observed_source": "stdout_stderr",
                        }
                    ],
                    "evaluation_result": "fail",
                }
            ]
        },
    )
    write_json(
        command_results,
        {
            "entries": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "observation_status": "observed",
                }
            ]
        },
    )
    report = build_remediation_planner(
        phase_gate_summary_path=phase_gate,
        runbook_summary_path=runbook,
        remediation_evaluator_summary_path=evaluator,
        remediation_command_results_summary_path=command_results,
        operation_chain_path=operation_chain,
        out_path=tmp_path / "remediation_planner.md",
        summary_path=tmp_path / "remediation_planner.json",
    )

    assert "Remediation Planner Dry Run" in report
    assert "## Quick Navigation" in report
    assert f"- remediation_planner_report: {tmp_path / 'remediation_planner.md'}" in report
    assert "## Related Reports" in report
    assert f"- remediation_execution_plan_report: {tmp_path / 'remediation_execution_plan.md'}" in report
    assert "planner_status: stalled" in report
    assert "## Planner Rerun Diff" in report
    assert "- trend: improved" in report
    assert "strict_validation_failed: improved" in report
    assert "observed_sources: ['stdout_stderr']" in report
    assert "source_confidence: high" in report
    assert "feedback_priority_reason: evaluation_failed" in report
    assert "`uv run sis validate-artifacts --strict`" in report
    assert "`uv run sis refresh-operations-artifacts`" in report
    summary = read_json(tmp_path / "remediation_planner.json")
    assert isinstance(summary, dict)
    assert summary["planner_status"] == "stalled"
    assert summary["planned_step_count"] == 2
    assert summary["next_best_command"] == "uv run sis validate-artifacts --strict"
    assert summary["recommended_command_chain"] == [
        "uv run sis validate-artifacts --strict",
        "uv run sis refresh-operations-artifacts",
    ]
    assert summary["quick_navigation"]["remediation_planner_report"] == str(
        tmp_path / "remediation_planner.md"
    )
    assert summary["related_reports"]["remediation_execution_plan_report"] == str(
        tmp_path / "remediation_execution_plan.md"
    )
    assert summary["remediation_evaluator_summary_path"] == str(evaluator)
    assert summary["planner_rerun_diff"]["trend"] == "improved"
    assert summary["planner_rerun_diff"]["previous_manifest_status"] == "regressed"
    assert summary["planner_entry_diffs"]["paper_operations_runbook:strict_validation_failed"]["trend"] == "improved"
    assert summary["entries"][0]["observed_sources"] == ["stdout_stderr"]
    assert summary["entries"][0]["source_confidence"] == "high"
    assert summary["entries"][0]["feedback_priority_reason"] == "evaluation_failed"
    assert summary["entries"][0]["supporting_action_keys"] == [
        "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1"
    ]


def test_render_live_evidence_report_includes_remediation_queue(tmp_path) -> None:
    report = render_live_evidence_report(
        LiveEvidenceReportData(
            status="completed",
            log_path=tmp_path / "live.log",
            manifest_path=tmp_path / "manifest.json",
            output_path=tmp_path / "live_evidence_report.md",
            started_at_utc="2026-05-24T00:00:00+00:00",
            finished_at_utc="2026-05-24T02:00:00+00:00",
            decision="CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            venue_decisions=[],
            blockers=["stale_rate remains above threshold"],
            next_actions=["collect more live quotes"],
            audit_summary={},
            phase_gate_summary={
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
                "strict_validation_issue_count": 1,
                "checked_files": 7,
                "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            },
            readiness_summary={
                "next_phase_candidate": "Stay Phase 1",
                "execution_ready": False,
                "timeline_latest_remediation_planner_status": "stalled",
                "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
                "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
                "timeline_latest_remediation_execution_plan_status": "stalled",
                "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
                "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
                "timeline_latest_remediation_session_status": "ready_for_dry_run",
                "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
                "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
                "timeline_latest_remediation_checkpoint_status": "retry_pending",
                "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
                "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
                "timeline_latest_remediation_scoreboard_status": "retrying",
                "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
                "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
                "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
                "current_state_index_report": "data/reports/current_state_index.md",
                "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
                "remediation_session_checkpoint_report": "data/reports/remediation_session_checkpoint.md",
                "remediation_session_report": "data/reports/remediation_session.md",
                "remediation_execution_plan_report": "data/reports/remediation_execution_plan.md",
                "remediation_planner_report": "data/reports/remediation_planner.md",
                "live_evidence_report": "docs/live_evidence_reports/live_evidence_report_run123.md",
            },
            timeline_latest_execution_summary={},
            timeline_latest_execution_comparison_summary={},
            bundle_history_latest_execution_summary={},
            bundle_history_latest_execution_comparison_summary={},
            cycle_history_latest_execution_summary={},
            cycle_history_latest_execution_comparison_summary={},
            execution_summary={},
            execution_comparison_summary={},
            execution_diagnostics_summary={},
            execution_gap_history_summary={},
            execution_state_comparison_summary={},
            execution_snapshot_drift_summary={},
            execution_drift_overview_summary={},
            quote_diagnostics=[],
            cost_rows=[],
            backtest_metrics=[],
            validation=ValidationSummary(checked_files=0, issues=[]),
            artifacts=LiveEvidenceArtifacts(
                sidecar_metadata=tmp_path / "sidecar_metadata.jsonl",
                sidecar_pricing=tmp_path / "sidecar_pricing.jsonl",
                raw_quotes=tmp_path / "raw_quotes.jsonl",
                normalized_quotes=tmp_path / "quotes.parquet",
                cost_matrix=tmp_path / "venue_cost_matrix.csv",
                backtest_metrics=tmp_path / "backtest_metrics.json",
                go_no_go_report=tmp_path / "go_no_go_report.md",
                evidence_card=None,
            ),
            log_tail=[],
            row_counts={"sidecar_metadata": 0, "sidecar_pricing": 0, "raw_quotes": 0},
        )
    )

    assert "## Current Remediation Queue" in report
    assert "- planner_status: `stalled`" in report
    assert "- session_next_pending_command: `uv run sis monitoring-status`" in report
    assert "- scoreboard_feedback_priority_reason: `evaluation_failed`" in report
    assert "## Restart Pointers" in report
    assert "- remediation_scoreboard_report: `data/reports/remediation_scoreboard.md`" in report
    assert "## Quick Navigation" in report
    assert "- phase_gate_review_report: `data/reports/phase_gate_review.md`" in report
    assert "## Related Reports" in report
    assert "- phase_gate_review_report: `data/reports/phase_gate_review.md`" in report


def test_build_remediation_execution_plan(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    write_json(
        phase_gate,
        {
            "remediation_preflight_commands": {
                "execution_drift_unresolved": ["uv run sis diagnose-quotes"],
            },
            "remediation_postcheck_commands": {
                "execution_drift_unresolved": ["uv run sis phase-gate-review"],
            },
            "remediation_preflight_expected_outputs": {
                "execution_drift_unresolved": ["diagnose-quotes prints per-symbol diagnostics rows"],
            },
            "remediation_execute_expected_outputs": {
                "execution_drift_unresolved": [
                    "execution_drift_overview_status == ok",
                    "execution_drift_overview_summary.json is regenerated",
                ],
            },
            "remediation_postcheck_pass_signals": {
                "execution_drift_unresolved": ["execution_drift_overview_status == ok"],
            },
        },
    )
    write_json(
        runbook,
        {
            "remediation_preflight_commands": {
                "strict_validation_failed": ["uv run sis validate-artifacts --strict"],
            },
            "remediation_postcheck_commands": {
                "strict_validation_failed": ["uv run sis paper-operations-runbook"],
            },
            "remediation_preflight_expected_outputs": {
                "strict_validation_failed": ["validate-artifacts --strict reports the current issue count"],
            },
            "remediation_execute_expected_outputs": {
                "strict_validation_failed": ["strict validation output reports issues=0"],
            },
            "remediation_postcheck_pass_signals": {
                "strict_validation_failed": ["phase_gate_strict_validation_issue_count == 0"],
            },
        },
    )
    write_json(
        planner,
        {
            "planner_status": "stalled",
            "planner_rerun_diff": {"trend": "improved"},
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
            "entries": [
                {
                    "source": "paper_operations_runbook",
                    "priority": 2,
                    "effective_priority": 1,
                    "reason": "strict_validation_failed",
                    "status": "stalled",
                    "why": "signals did not move toward target",
                    "commands": ["uv run sis validate-artifacts --strict"],
                    "observed_sources": ["stdout_stderr"],
                    "source_confidence": "high",
                    "source_policy": "direct_observation_priority",
                    "feedback_priority_reason": "verification_passed",
                    "signal_observed_sources": {
                        "validate-artifacts --strict reports the current issue count": "stdout_stderr"
                    },
                },
                {
                    "source": "phase_gate_review",
                    "priority": 4,
                    "effective_priority": 5,
                    "reason": "execution_drift_unresolved",
                    "status": "improving",
                    "why": "signals changed but target is not fully matched yet",
                    "commands": ["uv run sis refresh-operations-artifacts"],
                    "observed_sources": ["markdown_reports"],
                    "source_confidence": "low",
                    "source_policy": "verify_before_execute",
                    "feedback_priority_reason": "evaluation_failed",
                    "signal_observed_sources": {
                        "execution_drift_overview_status == ok": "markdown_reports",
                        "execution_drift_overview_summary.json is regenerated": "stdout_stderr",
                    },
                },
            ],
            "planner_entry_diffs": {
                "paper_operations_runbook:strict_validation_failed": {"trend": "regressed"},
                "phase_gate_review:execution_drift_unresolved": {"trend": "improved"},
            },
        },
    )

    report = build_remediation_execution_plan(
        remediation_planner_summary_path=planner,
        out_path=tmp_path / "remediation_execution_plan.md",
        summary_path=tmp_path / "remediation_execution_plan.json",
    )

    assert "Remediation Execution Plan Dry Run" in report
    assert "## Quick Navigation" in report
    assert (
        f"- remediation_execution_plan_report: {tmp_path / 'remediation_execution_plan.md'}"
        in report
    )
    assert "## Related Reports" in report
    assert f"- remediation_session_report: {tmp_path / 'remediation_session.md'}" in report
    assert "execution_plan_status: stalled" in report
    assert "`uv run sis validate-artifacts --strict`" in report
    assert "`uv run sis refresh-operations-artifacts`" in report
    assert "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1" in report
    assert "source_confidence: low" in report
    assert "observed_sources: ['stdout_stderr']" in report
    assert "execute_signal_confidence: low" in report
    assert "feedback_priority_reason: evaluation_failed" in report
    summary = read_json(tmp_path / "remediation_execution_plan.json")
    assert isinstance(summary, dict)
    assert summary["execution_plan_status"] == "stalled"
    assert summary["planned_reason_count"] == 2
    assert summary["planned_action_count"] >= 4
    assert summary["next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["quick_navigation"]["remediation_execution_plan_report"] == str(
        tmp_path / "remediation_execution_plan.md"
    )
    assert summary["related_reports"]["remediation_session_report"] == str(
        tmp_path / "remediation_session.md"
    )
    assert summary["entries"][0]["stage_order"] == ["preflight", "execute", "post_check"]
    assert summary["entries"][1]["stage_order"] == ["preflight", "execute", "post_check"]
    assert summary["entries"][0]["observed_sources"] == ["stdout_stderr"]
    assert summary["entries"][1]["feedback_priority_reason"] == "evaluation_failed"
    assert summary["actions"][0]["observed_sources"] == ["markdown_reports"]
    assert summary["entries"][1]["execute_signal_confidence"] == "low"
    phase_gate_execute = next(
        item
        for item in summary["actions"]
        if item["source"] == "phase_gate_review" and item["stage"] == "execute"
    )
    assert phase_gate_execute["verification"][0] == "execution_drift_overview_status == ok"


def test_build_remediation_session(tmp_path) -> None:
    execution_plan = tmp_path / "remediation_execution_plan.json"
    command_results = tmp_path / "remediation_command_results.json"
    evaluator = tmp_path / "remediation_evaluator.json"
    write_json(
        execution_plan,
        {
            "execution_plan_status": "stalled",
            "planner_status": "stalled",
            "planner_rerun_trend": "improved",
            "planned_reason_count": 2,
            "planned_action_count": 3,
            "next_action_command": "uv run sis validate-artifacts --strict",
            "entries": [
                {
                    "source": "paper_operations_runbook",
                    "priority": 2,
                    "reason": "strict_validation_failed",
                    "recommendation_status": "stalled",
                    "entry_trend": "regressed",
                    "observed_sources": ["stdout_stderr"],
                    "signal_observed_sources": {
                        "validate-artifacts --strict reports the current issue count": "stdout_stderr"
                    },
                }
            ],
            "actions": [
                {
                    "source": "paper_operations_runbook",
                    "priority": 2,
                    "effective_priority": 2,
                    "reason": "strict_validation_failed",
                    "stage": "preflight",
                    "sequence": 1,
                    "command": "uv run sis validate-artifacts --strict",
                    "recommendation_status": "stalled",
                    "entry_trend": "regressed",
                    "observed_sources": ["stdout_stderr"],
                    "source_confidence": "high",
                    "source_policy": "direct_observation_priority",
                    "signal_observed_sources": {
                        "validate-artifacts --strict reports the current issue count": "stdout_stderr"
                    },
                    "stage_signal_confidence": "high",
                    "verification": ["validate-artifacts --strict reports the current issue count"],
                },
                {
                    "source": "phase_gate_review",
                    "priority": 2,
                    "effective_priority": 2,
                    "reason": "execution_drift_unresolved",
                    "stage": "preflight",
                    "sequence": 1,
                    "command": "uv run sis monitoring-status",
                    "recommendation_status": "improving",
                    "entry_trend": "improved",
                    "observed_sources": ["markdown_reports"],
                    "source_confidence": "low",
                    "source_policy": "verify_before_execute",
                    "signal_observed_sources": {
                        "monitoring-status prints execution_drift_overview_status": "markdown_reports"
                    },
                    "stage_signal_confidence": "low",
                    "verification": ["monitoring-status prints execution_drift_overview_status"],
                },
            ],
        },
    )
    write_json(
        command_results,
        {
            "entries": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "observation_status": "observed",
                },
                {
                    "action_key": "priority_2_phase_gate_review_execution_drift_unresolved_preflight_1",
                    "observation_status": "observed",
                },
            ]
        },
    )
    write_json(
        evaluator,
        {
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "evaluation_result": "pass",
                },
                {
                    "action_key": "priority_2_phase_gate_review_execution_drift_unresolved_preflight_1",
                    "evaluation_result": "fail",
                },
            ]
        },
    )

    report = build_remediation_session(
        remediation_execution_plan_summary_path=execution_plan,
        remediation_command_results_summary_path=command_results,
        remediation_evaluator_summary_path=evaluator,
        out_path=tmp_path / "remediation_session.md",
        summary_path=tmp_path / "remediation_session.json",
    )

    assert "Remediation Session Dry Run" in report
    assert "## Quick Navigation" in report
    assert f"- remediation_session_report: {tmp_path / 'remediation_session.md'}" in report
    assert "## Related Reports" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'remediation_scoreboard.md'}" in report
    assert "session_status: ready_for_dry_run" in report
    assert "`uv run sis monitoring-status`" in report
    assert "stage_signal_confidence: low" in report
    assert "next_pending_feedback_priority_reason: evaluation_failed" in report
    summary = read_json(tmp_path / "remediation_session.json")
    assert isinstance(summary, dict)
    assert summary["session_status"] == "ready_for_dry_run"
    assert summary["planned_action_count"] == 2
    assert summary["pending_action_count"] == 2
    assert summary["next_pending_command"] == "uv run sis monitoring-status"
    assert summary["quick_navigation"]["remediation_session_report"] == str(
        tmp_path / "remediation_session.md"
    )
    assert summary["related_reports"]["remediation_scoreboard_report"] == str(
        tmp_path / "remediation_scoreboard.md"
    )
    assert summary["next_pending_stage_signal_confidence"] == "low"
    assert summary["next_pending_feedback_priority_reason"] == "evaluation_failed"
    assert summary["actions"][0]["session_status"] == "pending"
    assert summary["actions"][0]["evidence_status"] == "evidence_missing"
    assert summary["actions"][0]["observed_sources"] == ["markdown_reports"]
    assert summary["actions"][0]["stage_signal_confidence"] == "low"
    assert summary["actions"][0]["feedback_evaluation_result"] == "fail"
    assert summary["actions"][0]["feedback_priority_reason"] == "evaluation_failed"


def test_build_remediation_session_checkpoint(tmp_path) -> None:
    session = tmp_path / "remediation_session.json"
    write_json(
        session,
        {
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "source": "paper_operations_runbook",
                    "priority": 2,
                    "effective_priority": 2,
                    "reason": "strict_validation_failed",
                    "stage": "preflight",
                    "sequence": 1,
                    "command": "uv run sis validate-artifacts --strict",
                    "suggested_result": "needs_attention",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["stdout_stderr"],
                    "signal_observed_sources": {
                        "validate-artifacts --strict reports the current issue count": "stdout_stderr"
                    },
                    "stage_signal_confidence": "low",
                    "verification": ["validate-artifacts --strict reports the current issue count"],
                    "operator_notes": [],
                },
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_post_check_1",
                    "source": "paper_operations_runbook",
                    "priority": 2,
                    "effective_priority": 2,
                    "reason": "strict_validation_failed",
                    "stage": "post_check",
                    "sequence": 1,
                    "command": "uv run sis paper-operations-runbook",
                    "suggested_result": "pass",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["phase_gate_review"],
                    "signal_observed_sources": {
                        "phase_gate_strict_validation_issue_count == 0": "phase_gate_review"
                    },
                    "stage_signal_confidence": "high",
                    "verification": ["phase_gate_strict_validation_issue_count == 0"],
                    "operator_notes": [],
                },
            ]
        },
    )

    report = build_remediation_session_checkpoint(
        remediation_session_summary_path=session,
        checkpoint_summary_path=tmp_path / "remediation_session_checkpoint.json",
        out_path=tmp_path / "remediation_session_checkpoint.md",
        summary_path=tmp_path / "remediation_session_checkpoint.json",
        action_key="priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
        result="retry",
        note="strict validation still failing on first retry",
        evidence_path="data/ops/validate_artifacts_strict.log",
        observed_signal="validate-artifacts --strict reports the current issue count",
        stdout_summary="issues=2 checked_files=7",
        stderr_summary="",
        exit_code=1,
    )

    assert "Remediation Session Checkpoint" in report
    assert "## Quick Navigation" in report
    assert (
        f"- remediation_session_checkpoint_report: {tmp_path / 'remediation_session_checkpoint.md'}"
        in report
    )
    assert "## Related Reports" in report
    assert f"- remediation_evaluator_report: {tmp_path / 'remediation_evaluator.md'}" in report
    assert "checkpoint_status: retry_pending" in report
    assert "`uv run sis validate-artifacts --strict`" in report
    assert "next_action_observed_sources: ['stdout_stderr']" in report
    assert "next_action_stage_signal_confidence: low" in report
    summary = read_json(tmp_path / "remediation_session_checkpoint.json")
    assert isinstance(summary, dict)
    assert summary["checkpoint_status"] == "retry_pending"
    assert summary["pending_action_count"] == 1
    assert summary["retry_action_count"] == 1
    assert summary["next_action_command"] == "uv run sis validate-artifacts --strict"
    assert summary["quick_navigation"]["remediation_session_checkpoint_report"] == str(
        tmp_path / "remediation_session_checkpoint.md"
    )
    assert summary["related_reports"]["remediation_evaluator_report"] == str(
        tmp_path / "remediation_evaluator.md"
    )
    assert summary["next_action_observed_sources"] == ["stdout_stderr"]
    assert summary["next_action_stage_signal_confidence"] == "low"
    assert summary["observed_source_counts"] == {"phase_gate_review": 1, "stdout_stderr": 1}
    assert summary["actions"][0]["checkpoint_status"] == "retry"
    assert summary["actions"][0]["operator_notes"] == ["strict validation still failing on first retry"]
    assert summary["actions"][0]["evidence_paths"] == ["data/ops/validate_artifacts_strict.log"]
    assert summary["actions"][0]["observed_signals"] == ["validate-artifacts --strict reports the current issue count"]
    assert summary["actions"][0]["latest_exit_code"] == 1
    assert summary["actions"][0]["latest_stdout_summary"] == "issues=2 checked_files=7"
    assert summary["actions"][0]["stage_signal_confidence"] == "low"


def test_build_remediation_scoreboard(tmp_path) -> None:
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(
        checkpoint,
        {
            "checkpoint_status": "retry_pending",
            "pass_action_count": 1,
            "fail_action_count": 0,
            "retry_action_count": 1,
            "pending_action_count": 1,
            "next_action_command": "uv run sis validate-artifacts --strict",
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "priority": 2,
                    "effective_priority": 2,
                    "stage": "preflight",
                    "sequence": 1,
                    "command": "uv run sis validate-artifacts --strict",
                    "checkpoint_status": "retry",
                    "evidence_status": "needs_review",
                    "observed_sources": ["stdout_stderr"],
                    "stage_signal_confidence": "low",
                    "operator_notes": ["strict validation still failing on first retry"],
                },
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_post_check_1",
                    "priority": 2,
                    "effective_priority": 2,
                    "stage": "post_check",
                    "sequence": 1,
                    "command": "uv run sis paper-operations-runbook",
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "observed_sources": ["phase_gate_review"],
                    "stage_signal_confidence": "high",
                    "operator_notes": [],
                },
            ],
        },
    )

    report = build_remediation_scoreboard(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_scoreboard.md",
        summary_path=tmp_path / "remediation_scoreboard.json",
    )

    assert "Remediation Scoreboard" in report
    assert "## Quick Navigation" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'remediation_scoreboard.md'}" in report
    assert "## Related Reports" in report
    assert f"- remediation_evidence_report: {tmp_path / 'remediation_evidence.md'}" in report
    assert "scoreboard_status: retrying" in report
    assert "completion_rate: 0.5" in report
    assert "next_action_observed_sources: ['stdout_stderr']" in report
    assert "next_action_stage_signal_confidence: low" in report
    summary = read_json(tmp_path / "remediation_scoreboard.json")
    assert isinstance(summary, dict)
    assert summary["scoreboard_status"] == "retrying"
    assert summary["completion_rate"] == 0.5
    assert summary["quick_navigation"]["remediation_scoreboard_report"] == str(
        tmp_path / "remediation_scoreboard.md"
    )
    assert summary["related_reports"]["remediation_evidence_report"] == str(
        tmp_path / "remediation_evidence.md"
    )
    assert summary["blocking_action_keys"] == [
        "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1"
    ]
    assert summary["next_action_observed_sources"] == ["stdout_stderr"]
    assert summary["next_action_stage_signal_confidence"] == "low"
    assert summary["blocking_action_observed_sources"] == {
        "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1": ["stdout_stderr"]
    }
    assert summary["blocking_action_stage_signal_confidence"] == {
        "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1": "low"
    }


def test_build_remediation_session_checkpoint_uses_feedback_loop(tmp_path) -> None:
    session = tmp_path / "remediation_session.json"
    command_results = tmp_path / "remediation_command_results.json"
    evaluator = tmp_path / "remediation_evaluator.json"
    write_json(
        session,
        {
            "actions": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "source": "phase_gate_review",
                    "priority": 1,
                    "effective_priority": 1,
                    "reason": "missing_required_artifacts",
                    "stage": "preflight",
                    "sequence": 1,
                    "command": "uv run sis implementation-status",
                    "suggested_result": "pass",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["stdout_stderr"],
                    "signal_observed_sources": {"implementation-status exits 0": "stdout_stderr"},
                    "stage_signal_confidence": "high",
                    "verification": ["implementation-status exits 0"],
                    "operator_notes": [],
                },
                {
                    "action_key": "priority_3_phase_gate_review_execution_drift_unresolved_post_check_1",
                    "source": "phase_gate_review",
                    "priority": 3,
                    "effective_priority": 3,
                    "reason": "execution_drift_unresolved",
                    "stage": "post_check",
                    "sequence": 1,
                    "command": "uv run sis phase-gate-review",
                    "suggested_result": "pass",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["markdown_reports"],
                    "signal_observed_sources": {"execution_drift_overview_status == ok": "markdown_reports"},
                    "stage_signal_confidence": "low",
                    "verification": ["execution_drift_overview_status == ok"],
                    "operator_notes": [],
                },
            ]
        },
    )
    write_json(
        command_results,
        {
            "entries": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "observation_status": "observed",
                },
                {
                    "action_key": "priority_3_phase_gate_review_execution_drift_unresolved_post_check_1",
                    "observation_status": "observed",
                },
            ]
        },
    )
    write_json(
        evaluator,
        {
            "actions": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "evaluation_result": "pass",
                },
                {
                    "action_key": "priority_3_phase_gate_review_execution_drift_unresolved_post_check_1",
                    "evaluation_result": "fail",
                },
            ]
        },
    )

    report = build_remediation_session_checkpoint(
        remediation_session_summary_path=session,
        checkpoint_summary_path=tmp_path / "remediation_session_checkpoint.json",
        remediation_command_results_summary_path=command_results,
        remediation_evaluator_summary_path=evaluator,
        out_path=tmp_path / "remediation_session_checkpoint.md",
        summary_path=tmp_path / "remediation_session_checkpoint.json",
    )

    assert "next_action_command: uv run sis phase-gate-review" in report
    assert "feedback_priority_reason: evaluation_failed" in report
    summary = read_json(tmp_path / "remediation_session_checkpoint.json")
    assert isinstance(summary, dict)
    assert summary["next_action_command"] == "uv run sis phase-gate-review"
    assert summary["actions"][1]["feedback_evaluation_result"] == "fail"
    assert summary["actions"][1]["feedback_priority_reason"] == "evaluation_failed"


def test_build_remediation_scoreboard_uses_feedback_loop(tmp_path) -> None:
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    command_results = tmp_path / "remediation_command_results.json"
    evaluator = tmp_path / "remediation_evaluator.json"
    write_json(
        checkpoint,
        {
            "checkpoint_status": "in_progress",
            "pass_action_count": 0,
            "fail_action_count": 0,
            "retry_action_count": 0,
            "pending_action_count": 2,
            "next_action_command": "uv run sis implementation-status",
            "actions": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "priority": 1,
                    "effective_priority": 1,
                    "stage": "preflight",
                    "sequence": 1,
                    "command": "uv run sis implementation-status",
                    "checkpoint_status": "pending",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["stdout_stderr"],
                    "stage_signal_confidence": "high",
                    "operator_notes": [],
                },
                {
                    "action_key": "priority_3_phase_gate_review_execution_drift_unresolved_post_check_1",
                    "priority": 3,
                    "effective_priority": 3,
                    "stage": "post_check",
                    "sequence": 1,
                    "command": "uv run sis phase-gate-review",
                    "checkpoint_status": "pending",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["markdown_reports"],
                    "stage_signal_confidence": "low",
                    "operator_notes": [],
                },
            ],
        },
    )
    write_json(
        command_results,
        {
            "entries": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "observation_status": "observed",
                },
                {
                    "action_key": "priority_3_phase_gate_review_execution_drift_unresolved_post_check_1",
                    "observation_status": "observed",
                },
            ]
        },
    )
    write_json(
        evaluator,
        {
            "actions": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "evaluation_result": "pass",
                },
                {
                    "action_key": "priority_3_phase_gate_review_execution_drift_unresolved_post_check_1",
                    "evaluation_result": "fail",
                },
            ]
        },
    )

    report = build_remediation_scoreboard(
        remediation_session_checkpoint_summary_path=checkpoint,
        remediation_command_results_summary_path=command_results,
        remediation_evaluator_summary_path=evaluator,
        out_path=tmp_path / "remediation_scoreboard.md",
        summary_path=tmp_path / "remediation_scoreboard.json",
    )

    assert "next_action_command: uv run sis phase-gate-review" in report
    assert "feedback_priority_reason: evaluation_failed" in report
    summary = read_json(tmp_path / "remediation_scoreboard.json")
    assert isinstance(summary, dict)
    assert summary["next_action_command"] == "uv run sis phase-gate-review"
    assert summary["actions"][1]["feedback_evaluation_result"] == "fail"
    assert summary["actions"][1]["feedback_priority_reason"] == "evaluation_failed"


def test_build_remediation_evaluator(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {"strict_validation_issue_count": 0})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(
        execution_plan,
        {
            "remediation_planner_summary_path": str(planner),
        },
    )
    write_json(
        session,
        {
            "remediation_execution_plan_summary_path": str(execution_plan),
        },
    )
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_2_phase_gate_review_strict_validation_failed_post_check_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis phase-gate-review",
                    "verification": ["strict_validation_issue_count == 0"],
                    "checkpoint_status": "pending",
                    "evidence_status": "evidence_missing",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                }
            ],
        },
    )

    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator.md",
        summary_path=tmp_path / "remediation_evaluator.json",
    )

    assert "Remediation Evaluator" in report
    assert "## Quick Navigation" in report
    assert f"- remediation_evaluator_report: {tmp_path / 'remediation_evaluator.md'}" in report
    assert "## Related Reports" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'remediation_scoreboard.md'}" in report
    assert "evaluator_status: auto_passed" in report
    summary = read_json(tmp_path / "remediation_evaluator.json")
    assert isinstance(summary, dict)
    assert summary["evaluator_status"] == "auto_passed"
    assert summary["auto_pass_count"] == 1
    assert summary["auto_fail_count"] == 0
    assert summary["quick_navigation"]["remediation_evaluator_report"] == str(
        tmp_path / "remediation_evaluator.md"
    )
    assert summary["related_reports"]["remediation_scoreboard_report"] == str(
        tmp_path / "remediation_scoreboard.md"
    )
    assert summary["actions"][0]["evaluation_result"] == "pass"


def test_build_remediation_evaluator_uses_observed_signals(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {"strict_validation_issue_count": 2})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(
        execution_plan,
        {
            "remediation_planner_summary_path": str(planner),
        },
    )
    write_json(
        session,
        {
            "remediation_execution_plan_summary_path": str(execution_plan),
        },
    )
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_2_phase_gate_review_strict_validation_failed_preflight_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": ["validate-artifacts --strict reports issues=0"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": ["validate-artifacts --strict reports issues=0"],
                    "evidence_paths": ["data/ops/validate_artifacts_strict.log"],
                    "latest_exit_code": 0,
                }
            ],
        },
    )

    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_observed.md",
        summary_path=tmp_path / "remediation_evaluator_observed.json",
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(tmp_path / "remediation_evaluator_observed.json")
    assert isinstance(summary, dict)
    assert summary["actions"][0]["evaluation_result"] == "pass"
    assert summary["actions"][0]["signal_evaluations"][0]["expected"] == "manually_observed"


def test_build_remediation_evaluator_uses_exit_code_signal(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis implementation-status",
                    "verification": ["implementation-status exits 0"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": ["docs/IMPLEMENTATION_STATUS.md"],
                    "latest_exit_code": 0,
                }
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_exit_code.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_exit_code.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["actions"][0]["signal_evaluations"][0]["field"] == "exit_code"
    assert summary["actions"][0]["signal_evaluations"][0]["observed"] == 0


def test_build_remediation_evaluator_uses_stdout_summary_signals(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": [
                        "validate-artifacts --strict reports the current issue count",
                        "strict validation output includes checked_files",
                        "strict validation output reports checked_files >= 1",
                        "strict validation output reports issues=0",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": ["data/ops/validate_artifacts_strict.log"],
                    "latest_exit_code": 0,
                    "latest_stdout_summary": "issues=0 checked_files=7",
                    "latest_stderr_summary": "",
                }
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_stdout.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_stdout.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    evaluations = summary["actions"][0]["signal_evaluations"]
    assert evaluations[0]["field"] == "issues"
    assert evaluations[0]["observed"] == 0
    assert evaluations[1]["field"] == "checked_files"
    assert evaluations[1]["observed"] == 7
    assert evaluations[2]["status"] == "pass"
    assert evaluations[3]["status"] == "pass"


def test_build_remediation_evaluator_uses_monitoring_and_phase_gate_stdout_signals(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring-status prints execution_diagnostics_status",
                        "monitoring output shows current balance/fills gap flags",
                        "monitoring-status prints execution_drift_overview_status",
                        "monitoring output shows current mismatch counts",
                        "phase-gate-review prints phase2_entry_allowed",
                        "phase gate output shows current readiness blockers",
                        "current gate decision is visible before regeneration",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": ["data/ops/monitoring_status.log"],
                    "latest_exit_code": 0,
                    "latest_stdout_summary": (
                        "execution_diagnostics_status=degraded "
                        "execution_balance_gap_detected=True "
                        "execution_fills_gap_detected=False "
                        "execution_drift_overview_status=degraded "
                        "execution_drift_overview_state_comparison_mismatching_count=1 "
                        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=2 "
                        "phase2_entry_allowed=False "
                        "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears "
                        "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
                    ),
                    "latest_stderr_summary": "",
                }
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_monitoring.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_monitoring.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    evaluations = summary["actions"][0]["signal_evaluations"]
    assert evaluations[0]["field"] == "execution_diagnostics_status"
    assert evaluations[1]["status"] == "pass"
    assert evaluations[2]["field"] == "execution_drift_overview_status"
    assert evaluations[3]["status"] == "pass"
    assert evaluations[4]["field"] == "phase2_entry_allowed"
    assert evaluations[5]["status"] == "pass"
    assert evaluations[6]["observed"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"


def test_build_remediation_evaluator_uses_quote_diagnostics_and_go_no_go_stdout_signals(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_3_phase_gate_review_diagnostics_unavailable_preflight_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis diagnose-quotes",
                    "verification": [
                        "diagnose-quotes prints per-symbol diagnostics rows",
                        "required symbols show quote diagnostics coverage",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": ["data/ops/quote_diagnostics.log"],
                    "latest_exit_code": 0,
                    "latest_stdout_summary": "venue=gtrade symbol=QQQ rows=120 tradable_rate=0.9000 stale_rate=0.0100",
                    "latest_stderr_summary": "",
                },
                {
                    "action_key": "priority_5_phase_gate_review_phase_gate_not_cleared_preflight_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis check-go-no-go",
                    "verification": [
                        "check-go-no-go prints the current decision and blockers",
                        "current gate decision is visible before regeneration",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": ["data/ops/check_go_no_go.log"],
                    "latest_exit_code": 0,
                    "latest_stdout_summary": (
                        "decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW "
                        "phase2_entry_reason=remain_in_phase1_until_live_evidence_gate_clears "
                        "blocker_count=2"
                    ),
                    "latest_stderr_summary": "",
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_quote_go_no_go.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_quote_go_no_go.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    quote_evaluations = summary["actions"][0]["signal_evaluations"]
    gate_evaluations = summary["actions"][1]["signal_evaluations"]
    assert quote_evaluations[0]["status"] == "pass"
    assert quote_evaluations[1]["status"] == "pass"
    assert gate_evaluations[0]["status"] == "pass"
    assert gate_evaluations[0]["observed"]["blockers"] == 2
    assert gate_evaluations[1]["observed"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"


def test_build_remediation_evaluator_uses_operation_manifest_notes(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    operation_chain = tmp_path / "operation_manifests.jsonl"
    write_json(phase_gate, {})
    write_json(runbook, {})
    operation_chain.write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-25T00:00:00+00:00","operation":"monitoring_snapshot","mode":"manual","command":"uv run sis monitoring-status","status":"degraded","scheduled_for":null,"parent_run_id":null,"artifacts":[],"notes":["execution_diagnostics_status=degraded","execution_balance_gap_detected=True","execution_fills_gap_detected=False","execution_drift_overview_status=degraded","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=2"]}',
                '{"run_id":"r2","created_at":"2026-05-25T00:05:00+00:00","operation":"phase_gate_review","mode":"manual","command":"uv run sis phase-gate-review","status":"blocked","scheduled_for":null,"parent_run_id":null,"artifacts":[],"notes":["phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase_gate_checked_files=7","phase_gate_strict_validation_issue_count=2"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
            "operation_chain_path": str(operation_chain),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring-status prints execution_diagnostics_status",
                        "monitoring output shows current balance/fills gap flags",
                        "monitoring-status prints execution_drift_overview_status",
                        "monitoring output shows current mismatch counts",
                        "phase-gate-review prints phase2_entry_allowed",
                        "phase gate output shows current readiness blockers",
                        "strict validation output includes checked_files",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                }
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_manifest_notes.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_manifest_notes.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["operation_chain_path"] == str(operation_chain)
    evaluations = summary["actions"][0]["signal_evaluations"]
    assert evaluations[0]["field"] == "execution_diagnostics_status"
    assert evaluations[0]["observed"] == "degraded"
    assert evaluations[1]["status"] == "pass"
    assert evaluations[4]["field"] == "phase2_entry_allowed"
    assert evaluations[4]["observed"] is False
    assert evaluations[5]["status"] == "pass"
    assert evaluations[6]["observed"] == 7


def test_build_remediation_evaluator_uses_timeline_summary_fallback(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    operations_timeline = tmp_path / "operations_timeline_summary.json"
    audit_timeline = tmp_path / "audit_timeline_summary.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        operations_timeline,
        {
            "latest_execution_diagnostics_status": "degraded",
            "latest_execution_drift_overview_status": "degraded",
            "latest_execution_drift_overview_state_comparison_mismatching_count": 1,
            "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 2,
            "latest_phase2_entry_allowed": False,
            "latest_phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "latest_phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "latest_phase_gate_checked_files": 7,
        },
    )
    write_json(audit_timeline, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring-status prints execution_diagnostics_status",
                        "monitoring-status prints execution_drift_overview_status",
                        "monitoring output shows current mismatch counts",
                        "phase-gate-review prints phase2_entry_allowed",
                        "phase gate output shows current readiness blockers",
                        "strict validation output includes checked_files",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                }
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_timeline_fallback.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_timeline_fallback.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["operations_timeline_summary_path"] == str(operations_timeline)
    evaluations = summary["actions"][0]["signal_evaluations"]
    assert evaluations[0]["observed"] == "degraded"
    assert evaluations[2]["status"] == "pass"
    assert evaluations[3]["observed"] is False
    assert evaluations[4]["observed"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert evaluations[5]["observed"] == 7


def test_build_remediation_evaluator_uses_dashboard_bundle_summary_fallback(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    operations_dashboard = tmp_path / "operations_dashboard_summary.json"
    operations_bundle = tmp_path / "operations_bundle_manifest.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        operations_dashboard,
        {
            "execution_diagnostics_status": "degraded",
            "execution_balance_gap_detected": True,
            "execution_fills_gap_detected": False,
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 2,
        },
    )
    write_json(
        operations_bundle,
        {
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase_gate_checked_files": 7,
        },
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring-status prints execution_diagnostics_status",
                        "monitoring output shows current balance/fills gap flags",
                        "monitoring-status prints execution_drift_overview_status",
                        "monitoring output shows current mismatch counts",
                        "phase-gate-review prints phase2_entry_allowed",
                        "phase gate output shows current readiness blockers",
                        "strict validation output includes checked_files",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                }
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_dashboard_bundle_fallback.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_dashboard_bundle_fallback.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["operations_dashboard_summary_path"] == str(operations_dashboard)
    assert summary["operations_bundle_manifest_path"] == str(operations_bundle)
    evaluations = summary["actions"][0]["signal_evaluations"]
    assert evaluations[0]["observed"] == "degraded"
    assert evaluations[1]["status"] == "pass"
    assert evaluations[4]["observed"] is False
    assert evaluations[5]["observed"]["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert evaluations[6]["observed"] == 7


def test_build_remediation_evaluator_uses_issue_previews_and_blocker_lists(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(
        phase_gate,
        {
            "phase_gate_strict_validation_issues": [
                {
                    "path": "data/research/backtest_metrics_summary.json",
                    "message": "missing field",
                }
            ],
            "blockers": ["stale_rate at or below threshold"],
            "next_actions": ["collect more live quotes"],
        },
    )
    write_json(
        runbook,
        {
            "phase_gate_strict_validation_issues": [
                {
                    "path": "data/research/backtest_metrics_summary.json",
                    "message": "missing field",
                }
            ]
        },
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": ["strict validation preview lists current issues"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
                {
                    "action_key": "priority_5_phase_gate_review_phase_gate_not_cleared_preflight_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis check-go-no-go",
                    "verification": [
                        "phase gate summary lists blockers",
                        "phase gate summary lists next actions",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_issue_preview_lists.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_issue_preview_lists.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    issue_eval = summary["actions"][0]["signal_evaluations"][0]
    blocker_eval = summary["actions"][1]["signal_evaluations"][0]
    next_action_eval = summary["actions"][1]["signal_evaluations"][1]
    assert issue_eval["status"] == "pass"
    assert issue_eval["observed"] == ["data/research/backtest_metrics_summary.json: missing field"]
    assert blocker_eval["observed"] == ["stale_rate at or below threshold"]
    assert next_action_eval["observed"] == ["collect more live quotes"]


def test_build_remediation_evaluator_uses_markdown_report_fallback(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    phase_gate_report = tmp_path / "phase_gate_review.md"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {"phase_gate_review_report_path": str(phase_gate_report)})
    write_json(runbook, {})
    phase_gate_report.write_text(
        "\n".join(
            [
                "# Phase Gate Review",
                "",
                "## Executive Summary",
                "",
                "- phase2_entry_reason: stale_rate remains above threshold",
                "",
                "## Strict Validation",
                "",
                "- checked_files: 7",
                "",
                "| path | message |",
                "| --- | --- |",
                "| data/research/backtest_metrics_summary.json | missing field |",
                "",
                "## Next Actions",
                "",
                "- collect more live quotes",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "source": "paper_operations_runbook",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": ["strict validation preview lists current issues"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
                {
                    "action_key": "priority_5_phase_gate_review_phase_gate_not_cleared_preflight_1",
                    "source": "phase_gate_review",
                    "command": "uv run sis check-go-no-go",
                    "verification": [
                        "phase gate summary lists blockers",
                        "phase gate summary lists next actions",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_markdown_report.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_markdown_report.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["phase_gate_review_report_path"] == str(phase_gate_report)
    issue_eval = summary["actions"][0]["signal_evaluations"][0]
    blocker_eval = summary["actions"][1]["signal_evaluations"][0]
    next_action_eval = summary["actions"][1]["signal_evaluations"][1]
    assert issue_eval["observed"] == ["data/research/backtest_metrics_summary.json: missing field"]
    assert blocker_eval["observed"] == ["stale_rate remains above threshold"]
    assert next_action_eval["observed"] == ["collect more live quotes"]


def test_build_remediation_evaluator_uses_ops_review_fallback(tmp_path) -> None:
    ops_dir = tmp_path / "ops"
    reports_dir = tmp_path / "reports"
    ops_dir.mkdir()
    reports_dir.mkdir()
    phase_gate = ops_dir / "phase_gate_review_summary.json"
    runbook = ops_dir / "paper_operations_runbook_summary.json"
    ops_review_summary = ops_dir / "ops_review_summary.json"
    ops_review_report = reports_dir / "ops_review_report.md"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        ops_review_summary,
        {
            "execution_balance_gap_detected": False,
            "execution_fills_gap_detected": True,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 2,
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "phase_gate_checked_files": 7,
        },
    )
    ops_review_report.write_text(
        "\n".join(
            [
                "# Ops Review Report",
                "",
                "## Strict Validation Preview",
                "",
                "- data/research/backtest_metrics_summary.json: missing field",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "a1",
                    "source": "phase_gate_review",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": ["strict validation preview lists current issues"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
                {
                    "action_key": "a2",
                    "source": "phase_gate_review",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring output shows current balance/fills gap flags",
                        "monitoring output shows current mismatch counts",
                        "phase gate output shows current readiness blockers",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_ops_review_fallback.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_ops_review_fallback.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["ops_review_summary_path"] == str(ops_review_summary)
    assert summary["ops_review_report_path"] == str(ops_review_report)
    issue_eval = summary["actions"][0]["signal_evaluations"][0]
    monitoring_eval = summary["actions"][1]["signal_evaluations"][0]
    mismatch_eval = summary["actions"][1]["signal_evaluations"][1]
    readiness_eval = summary["actions"][1]["signal_evaluations"][2]
    assert issue_eval["observed"] == ["data/research/backtest_metrics_summary.json: missing field"]
    assert monitoring_eval["status"] == "pass"
    assert mismatch_eval["observed"]["execution_drift_overview_state_comparison_mismatching_count"] == 1
    assert readiness_eval["observed"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"


def test_build_remediation_evaluator_uses_current_state_index_fallback(tmp_path) -> None:
    ops_dir = tmp_path / "ops"
    reports_dir = tmp_path / "reports"
    ops_dir.mkdir()
    reports_dir.mkdir()
    phase_gate = ops_dir / "phase_gate_review_summary.json"
    runbook = ops_dir / "paper_operations_runbook_summary.json"
    current_state_index = ops_dir / "current_state_index.json"
    current_state_report = reports_dir / "current_state_index.md"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        current_state_index,
        {
            "execution_balance_gap_detected": False,
            "execution_fills_gap_detected": True,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 2,
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "phase_gate_checked_files": 7,
            "live_evidence_status": "completed",
            "live_evidence_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        },
    )
    current_state_report.write_text(
        "\n".join(
            [
                "# Current State Index",
                "",
                "## Strict Validation Preview",
                "",
                "- data/research/backtest_metrics_summary.json: missing field",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "a1",
                    "source": "phase_gate_review",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": ["strict validation preview lists current issues"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
                {
                    "action_key": "a2",
                    "source": "phase_gate_review",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring output shows current balance/fills gap flags",
                        "monitoring output shows current mismatch counts",
                        "phase gate output shows current readiness blockers",
                        "phase-gate-review prints phase2_entry_allowed",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_current_state_index_fallback.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_current_state_index_fallback.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["current_state_index_summary_path"] == str(current_state_index)
    assert summary["current_state_index_report_path"] == str(current_state_report)
    issue_eval = summary["actions"][0]["signal_evaluations"][0]
    phase_gate_eval = summary["actions"][1]["signal_evaluations"][3]
    assert issue_eval["observed"] == ["data/research/backtest_metrics_summary.json: missing field"]
    assert phase_gate_eval["observed"] is False


def test_build_remediation_evaluator_uses_live_evidence_fallback(tmp_path) -> None:
    ops_dir = tmp_path / "ops"
    reports_dir = tmp_path / "reports"
    logs_summary_dir = tmp_path / "logs/live_evidence/summaries"
    live_reports_dir = tmp_path / "docs/live_evidence_reports"
    ops_dir.mkdir()
    reports_dir.mkdir()
    logs_summary_dir.mkdir(parents=True)
    live_reports_dir.mkdir(parents=True)
    phase_gate = ops_dir / "phase_gate_review_summary.json"
    runbook = ops_dir / "paper_operations_runbook_summary.json"
    current_state_index = ops_dir / "current_state_index.json"
    live_evidence_summary = logs_summary_dir / "live_evidence_summary_run123.json"
    live_evidence_report = live_reports_dir / "live_evidence_report_run123.md"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        current_state_index,
        {
            "artifacts": {
                "live_evidence_summary": str(live_evidence_summary),
            }
        },
    )
    write_json(
        live_evidence_summary,
        {
            "status": "completed",
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "run_id": "run123",
            "blockers": ["stale_rate remains above threshold"],
            "next_actions": ["collect more live quotes"],
            "phase_gate_summary": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "checked_files": 7,
            },
            "execution_diagnostics_summary": {
                "overall_status": "degraded",
                "balance_gap_detected": False,
                "fills_gap_detected": True,
            },
        },
    )
    live_evidence_report.write_text(
        "\n".join(
            [
                "# Live Evidence Detailed Report",
                "",
                "## Phase Gate Summary",
                "",
                "- phase2_entry_allowed: `False`",
                "- phase_gate_reason: `remain_in_phase1_until_live_evidence_gate_clears`",
                "",
                "## Execution Venue Diagnostics",
                "",
                "- overall_status: `degraded`",
                "- balance_gap_detected: `False`",
                "- fills_gap_detected: `True`",
                "",
                "## Blockers",
                "",
                "- stale_rate remains above threshold",
                "",
                "## Next Actions",
                "",
                "- collect more live quotes",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "a1",
                    "source": "phase_gate_review",
                    "command": "uv run sis monitoring-status",
                    "verification": [
                        "monitoring output shows current balance/fills gap flags",
                        "phase gate summary lists blockers",
                        "phase gate summary lists next actions",
                        "phase-gate-review prints phase2_entry_allowed",
                    ],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_live_evidence_fallback.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_live_evidence_fallback.md",
        summary_path=summary_path,
    )

    assert "evaluator_status: auto_passed" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["live_evidence_summary_path"] == str(live_evidence_summary)
    assert summary["live_evidence_report_path"] == str(live_evidence_report)
    evaluations = summary["actions"][0]["signal_evaluations"]
    assert evaluations[0]["status"] == "pass"
    assert evaluations[1]["observed"] == ["stale_rate remains above threshold"]
    assert evaluations[2]["observed"] == ["collect more live quotes"]
    assert evaluations[3]["observed"] is False


def test_build_remediation_evaluator_records_observed_sources(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(phase_gate, {})
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(execution_plan, {"remediation_planner_summary_path": str(planner)})
    write_json(session, {"remediation_execution_plan_summary_path": str(execution_plan)})
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "a1",
                    "source": "phase_gate_review",
                    "command": "uv run sis validate-artifacts --strict",
                    "verification": ["validate-artifacts --strict reports issues=0"],
                    "checkpoint_status": "pass",
                    "evidence_status": "evidence_recorded",
                    "operator_notes": [],
                    "observed_signals": [],
                    "evidence_paths": [],
                    "latest_stdout_summary": "issues=0 checked_files=7",
                },
            ],
        },
    )

    summary_path = tmp_path / "remediation_evaluator_observed_sources.json"
    report = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_evaluator_observed_sources.md",
        summary_path=summary_path,
    )

    assert "## Fallback Field Sources" in report
    assert "observed_source=stdout_stderr" in report
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    evaluation = summary["actions"][0]["signal_evaluations"][0]
    assert evaluation["observed_source"] == "stdout_stderr"
    assert summary["fallback_count_sources"] == {}


def test_build_remediation_command_results(tmp_path) -> None:
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    write_json(
        checkpoint,
        {
            "actions": [
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
                    "source": "paper_operations_runbook",
                    "reason": "strict_validation_failed",
                    "stage": "preflight",
                    "command": "uv run sis validate-artifacts --strict",
                    "checkpoint_status": "retry",
                    "observed_sources": ["stdout_stderr"],
                    "signal_observed_sources": {
                        "validate-artifacts --strict reports the current issue count": "stdout_stderr"
                    },
                    "evidence_paths": ["data/ops/validate_artifacts_strict.log"],
                    "observed_signals": ["validate-artifacts --strict reports the current issue count"],
                    "latest_exit_code": 1,
                    "latest_stdout_summary": "issues=2 checked_files=7",
                    "latest_stderr_summary": "",
                },
                {
                    "action_key": "priority_2_paper_operations_runbook_strict_validation_failed_post_check_1",
                    "source": "paper_operations_runbook",
                    "reason": "strict_validation_failed",
                    "stage": "post_check",
                    "command": "uv run sis paper-operations-runbook",
                    "checkpoint_status": "pending",
                    "evidence_paths": [],
                    "observed_signals": [],
                },
            ]
        },
    )

    report = build_remediation_command_results(
        remediation_session_checkpoint_summary_path=checkpoint,
        out_path=tmp_path / "remediation_command_results.md",
        summary_path=tmp_path / "remediation_command_results.json",
    )

    assert "Remediation Command Results" in report
    assert "## Quick Navigation" in report
    assert (
        f"- remediation_command_results_report: {tmp_path / 'remediation_command_results.md'}"
        in report
    )
    assert "## Related Reports" in report
    assert f"- remediation_scoreboard_report: {tmp_path / 'remediation_scoreboard.md'}" in report
    assert "command_results_status: partially_observed" in report
    assert "observed_sources: ['stdout_stderr']" in report
    summary = read_json(tmp_path / "remediation_command_results.json")
    assert isinstance(summary, dict)
    assert summary["observed_action_count"] == 1
    assert summary["missing_observation_count"] == 1
    assert summary["quick_navigation"]["remediation_command_results_report"] == str(
        tmp_path / "remediation_command_results.md"
    )
    assert summary["related_reports"]["remediation_scoreboard_report"] == str(
        tmp_path / "remediation_scoreboard.md"
    )
    assert summary["observed_source_counts"] == {"stdout_stderr": 1}
    assert summary["entries"][0]["observation_status"] == "observed"
    assert summary["entries"][0]["latest_exit_code"] == 1
    assert summary["entries"][0]["observed_sources"] == ["stdout_stderr"]


def test_build_remediation_evidence(tmp_path) -> None:
    phase_gate = tmp_path / "phase_gate.json"
    runbook = tmp_path / "runbook.json"
    planner = tmp_path / "remediation_planner.json"
    execution_plan = tmp_path / "remediation_execution_plan.json"
    session = tmp_path / "remediation_session.json"
    checkpoint = tmp_path / "remediation_session_checkpoint.json"
    evaluator = tmp_path / "remediation_evaluator.json"
    write_json(
        phase_gate,
        {
            "phase_gate_review_report_path": str(tmp_path / "phase_gate_review.md"),
            "required_artifact_paths": {
                "latest_manifest_path": str(tmp_path / "decision_summary.json"),
                "latest_evidence_card_path": str(tmp_path / "evidence_card.json"),
            },
            "missing_required_artifact_paths": [],
        },
    )
    write_json(runbook, {})
    write_json(
        planner,
        {
            "phase_gate_summary_path": str(phase_gate),
            "runbook_summary_path": str(runbook),
        },
    )
    write_json(
        execution_plan,
        {
            "remediation_planner_summary_path": str(planner),
        },
    )
    write_json(
        session,
        {
            "remediation_execution_plan_summary_path": str(execution_plan),
        },
    )
    write_json(
        checkpoint,
        {
            "remediation_session_summary_path": str(session),
            "actions": [
                {
                    "action_key": "priority_5_phase_gate_review_phase_gate_not_cleared_post_check_1",
                    "source": "phase_gate_review",
                    "reason": "phase_gate_not_cleared",
                    "stage": "post_check",
                    "command": "uv run sis phase-gate-review",
                    "checkpoint_status": "pending",
                    "evidence_status": "evidence_missing",
                    "observed_sources": ["current_state_index"],
                    "operator_notes": [],
                    "evidence_paths": [],
                    "observed_signals": [],
                }
            ],
        },
    )
    write_json(
        evaluator,
        {
            "actions": [
                {
                    "action_key": "priority_5_phase_gate_review_phase_gate_not_cleared_post_check_1",
                    "source": "phase_gate_review",
                    "reason": "phase_gate_not_cleared",
                    "stage": "post_check",
                    "command": "uv run sis phase-gate-review",
                    "evaluation_result": "manual_review",
                    "checkpoint_status": "pending",
                    "evidence_status": "evidence_missing",
                    "suggested_result": "pass",
                    "operator_notes": [],
                    "verification": ["validate-artifacts --strict reports issues=0"],
                    "signal_evaluations": [
                        {
                            "signal": "validate-artifacts --strict reports issues=0",
                            "status": "unsupported",
                            "expected": None,
                            "observed": None,
                            "observed_source": "stdout_stderr",
                        }
                    ],
                }
            ],
        },
    )

    report = build_remediation_evidence(
        remediation_session_checkpoint_summary_path=checkpoint,
        remediation_evaluator_summary_path=evaluator,
        out_path=tmp_path / "remediation_evidence.md",
        summary_path=tmp_path / "remediation_evidence.json",
    )

    assert "Remediation Evidence" in report
    assert "## Quick Navigation" in report
    assert f"- remediation_evidence_report: {tmp_path / 'remediation_evidence.md'}" in report
    assert "## Related Reports" in report
    assert f"- remediation_evaluator_report: {tmp_path / 'remediation_evaluator.md'}" in report
    assert "evidence_status: manual_review_required" in report
    assert "observed_sources: ['current_state_index', 'stdout_stderr']" in report
    summary = read_json(tmp_path / "remediation_evidence.json")
    assert isinstance(summary, dict)
    assert summary["manual_review_action_count"] == 1
    assert summary["unsupported_signal_count"] == 1
    assert summary["quick_navigation"]["remediation_evidence_report"] == str(
        tmp_path / "remediation_evidence.md"
    )
    assert summary["related_reports"]["remediation_evaluator_report"] == str(
        tmp_path / "remediation_evaluator.md"
    )
    assert summary["observed_source_counts"] == {"current_state_index": 1, "stdout_stderr": 1}
    assert summary["entries"][0]["source_summary_path"] == str(phase_gate)
    assert str(tmp_path / "decision_summary.json") in summary["entries"][0]["candidate_artifact_paths"]
    assert summary["entries"][0]["observed_sources"] == ["current_state_index", "stdout_stderr"]


def test_build_paper_cycle_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-24T00:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"run_id":"r2","created_at":"2026-05-24T01:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":[]}',
                '{"run_id":"r3","created_at":"2026-05-24T02:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=2","fills=2","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_paper_cycle_history_report(
        operation_chain_path=operation_chain,
        out_path=tmp_path / "paper_cycle_history.md",
        summary_path=tmp_path / "paper_cycle_history_summary.json",
    )

    assert "Paper Cycle History Report" in report
    assert "## Quick Navigation" in report
    assert f"- paper_cycle_history_report: {tmp_path / 'paper_cycle_history.md'}" in report
    assert "## Related Reports" in report
    assert f"- execution_drift_overview_report: {tmp_path / 'execution_drift_overview.md'}" in report
    assert "cycle_count: 2" in report
    assert "completed_count: 2" in report
    assert "total_orders: 3" in report
    assert "total_fills: 3" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_diagnostics_status: degraded" in report
    assert "latest_execution_drift_overview_status: degraded" in report
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in report
    assert "latest_execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "latest_readiness_next_phase: Phase 1" in report
    assert "latest_readiness_execution_ready: False" in report
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "latest_phase2_entry_allowed: False" in report
    assert "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "latest_phase_gate_strict_validation_passed: False" in report
    assert "latest_phase_gate_strict_validation_issue_count: 2" in report
    assert "latest_phase_gate_checked_files: 7" in report
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "degraded: 1" in report
    assert "ok: 1" in report
    assert "False: 1" in report
    assert "True: 1" in report
    assert "1: 1" in report
    assert "0: 1" in report
    assert "Phase 1: 1" in report
    assert "Phase 2: 1" in report
    assert "CONDITIONAL_GO_NEEDS_LIVE_WINDOW: 1" in report
    assert "GO: 1" in report
    summary = read_json(tmp_path / "paper_cycle_history_summary.json")
    assert isinstance(summary, dict)
    assert summary["quick_navigation"]["paper_cycle_history_report"] == str(
        tmp_path / "paper_cycle_history.md"
    )
    assert summary["related_reports"]["execution_drift_overview_report"] == str(
        tmp_path / "execution_drift_overview.md"
    )
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["latest_execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"


def test_build_operations_bundle_manifest(tmp_path) -> None:
    monitoring = tmp_path / "monitoring.json"
    ops_review = tmp_path / "ops_review.json"
    dashboard = tmp_path / "dashboard.json"
    execution = tmp_path / "execution.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    runbook = tmp_path / "runbook.json"
    cycle_history = tmp_path / "cycle_history.json"
    phase_gate = tmp_path / "phase_gate.json"
    write_json(monitoring, {"status": "ok"})
    write_json(ops_review, {"latest_status": "completed"})
    write_json(
        dashboard,
        {
            "overall_status": "ok",
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_execution_plan_status": "stalled",
            "timeline_latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "timeline_latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_session_status": "ready_for_dry_run",
            "timeline_latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "timeline_latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_checkpoint_status": "retry_pending",
            "timeline_latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "timeline_latest_remediation_scoreboard_status": "retrying",
            "timeline_latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "timeline_latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(execution, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(
        execution_diagnostics,
        {"overall_status": "degraded", "balance_gap_detected": True, "fills_gap_detected": False},
    )
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"})
    write_json(execution_state_comparison, {"entry_count": 4, "latest_status_match": False, "mismatching_count": 1})
    write_json(
        execution_drift_overview,
        {
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
    )
    write_json(readiness, {"next_phase_candidate": "Stay Phase 1", "execution_ready": False})
    write_json(runbook, {"monitoring_status": "ok"})
    write_json(
        cycle_history,
        {
            "cycle_count": 2,
            "completed_count": 2,
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "latest_execution_overall_status": "ok",
            "latest_execution_venue_count": 2,
            "latest_execution_comparison_all_registries_present": True,
        },
    )
    write_json(
        phase_gate,
        {
            "decision": "GO",
            "phase2_entry_allowed": True,
            "phase2_entry_reason": "decision_cleared_and_phase1_gate_complete",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 0,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [],
        },
    )

    report = build_operations_bundle_manifest(
        monitoring_summary_path=monitoring,
        ops_review_summary_path=ops_review,
        dashboard_summary_path=dashboard,
        execution_snapshot_summary_path=execution,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        runbook_summary_path=runbook,
        paper_cycle_history_summary_path=cycle_history,
        phase_gate_summary_path=phase_gate,
        out_path=tmp_path / "bundle.md",
        manifest_path=tmp_path / "bundle.json",
    )

    assert "Operations Bundle Manifest" in report
    assert "overall_status: ok" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_all_registries_present: True" in report
    assert "execution_diagnostics_status: degraded" in report
    assert "execution_balance_gap_detected: True" in report
    assert "execution_fills_gap_detected: False" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: degraded" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: False" in report
    assert "execution_state_comparison_mismatching_count: 1" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "execution_drift_overview_status: degraded" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "readiness_next_phase_candidate: Stay Phase 1" in report
    assert "readiness_execution_ready: False" in report
    assert "cycle_count: 2" in report
    assert "cycle_history_latest_execution_overall_status: ok" in report
    assert "cycle_history_latest_execution_venue_count: 2" in report
    assert "cycle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "phase_gate_decision: GO" in report
    assert "phase2_entry_allowed: True" in report
    assert "phase_gate_reason: decision_cleared_and_phase1_gate_complete" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "issues: none" in report
    assert "## Quick Navigation" in report
    assert f"- operations_bundle_report: {tmp_path / 'bundle.md'}" in report
    assert f"- phase_gate_review_report: {tmp_path / 'reports/phase_gate_review.md'}" in report
    assert "## Related Reports" in report
    assert "## Recommended Read Order" in report
    manifest = read_json(tmp_path / "bundle.json")
    assert isinstance(manifest, dict)
    assert manifest["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert manifest["readiness_execution_ready"] is False
    assert manifest["timeline_latest_remediation_planner_status"] == "stalled"
    assert (
        manifest["timeline_latest_remediation_execution_plan_next_action_command"]
        == "uv run sis diagnose-quotes"
    )
    assert manifest["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"
    assert manifest["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert manifest["phase_gate_strict_validation_passed"] is True
    assert manifest["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert manifest["quick_navigation"]["operations_bundle_report"] == str(tmp_path / "bundle.md")
    assert (
        manifest["related_reports"]["phase_gate_review_report"]
        == str(tmp_path / "reports/phase_gate_review.md")
    )
    assert manifest["recommended_read_order"][0] == "docs/ACCEPTANCE_AUDIT.md"
    assert manifest["phase_gate_summary"]["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert manifest["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert manifest["cycle_history_latest_execution_overall_status"] == "ok"
    assert manifest["cycle_history_latest_execution_venue_count"] == 2
    assert manifest["cycle_history_latest_execution_comparison_all_registries_present"] is True
    assert manifest["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        manifest["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert manifest["execution_summary"]["execution_overall_status"] == "ok"
    assert manifest["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert manifest["execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert manifest["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert manifest["execution_state_comparison_summary"]["execution_state_comparison_entry_count"] == 4
    assert manifest["execution_snapshot_drift_summary"]["execution_snapshot_drift_entry_count"] == 3
    assert manifest["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"


def test_build_operations_timeline_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","mode":"paper","notes":["dry_run","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=planned","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","mode":"paper","notes":["orders=1","fills=1","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=completed","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","mode":"ops","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
                '{"created_at":"2026-05-24T03:00:00+00:00","operation":"remediation_planner_dry_run","status":"stalled","mode":"ops","notes":["planner_status=stalled","next_best_command=uv run sis validate-artifacts --strict","next_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T04:00:00+00:00","operation":"remediation_execution_plan_dry_run","status":"stalled","mode":"ops","notes":["execution_plan_status=stalled","next_action_command=uv run sis diagnose-quotes","next_action_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T05:00:00+00:00","operation":"remediation_session_dry_run","status":"ready_for_dry_run","mode":"ops","notes":["session_status=ready_for_dry_run","next_pending_command=uv run sis monitoring-status","next_pending_stage_signal_confidence=low","next_pending_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T06:00:00+00:00","operation":"remediation_session_checkpoint","status":"retry_pending","mode":"ops","notes":["checkpoint_status=retry_pending","next_action_command=uv run sis phase-gate-review","next_action_stage_signal_confidence=low","next_action_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T07:00:00+00:00","operation":"remediation_scoreboard","status":"retrying","mode":"ops","notes":["scoreboard_status=retrying","next_action_command=uv run sis phase-gate-review","next_action_stage_signal_confidence=low","next_action_feedback_priority_reason=evaluation_failed"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_operations_timeline_report(
        operation_chain_path=operation_chain,
        out_path=tmp_path / "timeline.md",
        summary_path=tmp_path / "timeline_summary.json",
    )

    assert "Operations Timeline Report" in report
    assert "operation_count: 8" in report
    assert "latest_operation: remediation_scoreboard" in report
    assert "daemon_dry_run: 1" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_diagnostics_status: degraded" in report
    assert "latest_execution_drift_overview_status: degraded" in report
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in report
    assert "latest_execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "latest_execution_gap_history_status: ok" in report
    assert "latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "latest_execution_state_comparison_status_match: False" in report
    assert "latest_execution_state_comparison_mismatching_count: 1" in report
    assert "latest_readiness_next_phase: Phase 1" in report
    assert "latest_readiness_execution_ready: False" in report
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "latest_phase2_entry_allowed: False" in report
    assert "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "latest_phase_gate_strict_validation_passed: False" in report
    assert "latest_phase_gate_strict_validation_issue_count: 2" in report
    assert "latest_phase_gate_checked_files: 7" in report
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "latest_remediation_planner_status: stalled" in report
    assert "latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_execution_plan_status: stalled" in report
    assert "latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "latest_remediation_execution_plan_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_session_status: ready_for_dry_run" in report
    assert "latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "latest_remediation_session_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_checkpoint_status: retry_pending" in report
    assert "latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "latest_remediation_checkpoint_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_scoreboard_status: retrying" in report
    assert "latest_remediation_scoreboard_next_action_command: uv run sis phase-gate-review" in report
    assert "latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "latest_phase2_entry_allowed: False" in report
    assert "degraded: 2" in report
    assert "ok: 1" in report
    assert "completed: 1" in report
    assert "planned: 1" in report
    assert "False: 1" in report
    assert "True: 2" in report
    assert "1: 2" in report
    assert "0: 1" in report
    assert "1: 1" in report
    assert "0: 2" in report
    assert "## Quick Navigation" in report
    assert f"- operations_timeline_report: {tmp_path / 'timeline.md'}" in report
    assert "## Related Reports" in report
    assert f"- operations_dashboard_report: {tmp_path / 'reports/operations_dashboard.md'}" in report
    summary = read_json(tmp_path / "timeline_summary.json")
    assert isinstance(summary, dict)
    assert summary["quick_navigation"]["operations_timeline_report"] == str(tmp_path / "timeline.md")
    assert (
        summary["related_reports"]["operations_dashboard_report"]
        == str(tmp_path / "reports/operations_dashboard.md")
    )
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == "1"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["latest_remediation_planner_status"] == "stalled"
    assert summary["latest_remediation_session_next_pending_command"] == "uv run sis monitoring-status"
    assert summary["latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"


def test_build_operations_audit_pack(tmp_path) -> None:
    bundle = tmp_path / "bundle.json"
    timeline = tmp_path / "timeline.json"
    cycle_history = tmp_path / "cycle_history.json"
    runbook = tmp_path / "runbook.json"
    execution = tmp_path / "execution.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    phase_gate = tmp_path / "phase_gate.json"
    write_json(bundle, {"overall_status": "ok"})
    write_json(
        timeline,
        {
            "latest_operation": "operations_snapshot",
            "latest_status": "ok",
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "latest_execution_overall_status": "ok",
            "latest_execution_venue_count": 2,
            "latest_execution_comparison_all_registries_present": True,
            "latest_execution_gap_history_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "degraded",
            "latest_readiness_execution_ready": False,
            "latest_remediation_planner_status": "stalled",
            "latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_execution_plan_status": "stalled",
            "latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_session_status": "ready_for_dry_run",
            "latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_checkpoint_status": "retry_pending",
            "latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_scoreboard_status": "retrying",
            "latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(cycle_history, {"cycle_count": 2, "completed_count": 2})
    write_json(runbook, {"monitoring_status": "ok"})
    write_json(execution, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(
        execution_diagnostics,
        {"overall_status": "degraded", "balance_gap_detected": True, "fills_gap_detected": False},
    )
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"})
    write_json(execution_state_comparison, {"entry_count": 4, "latest_status_match": False, "mismatching_count": 1})
    write_json(
        execution_drift_overview,
        {
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(
        readiness,
        {
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        },
    )
    write_json(
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )

    report = build_operations_audit_pack(
        bundle_manifest_path=bundle,
        timeline_summary_path=timeline,
        cycle_history_summary_path=cycle_history,
        runbook_summary_path=runbook,
        execution_snapshot_summary_path=execution,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        phase_gate_summary_path=phase_gate,
        out_path=tmp_path / "audit.md",
        manifest_path=tmp_path / "audit.json",
    )

    assert "Operations Audit Pack" in report
    assert "overall_status: ok" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_all_registries_present: True" in report
    assert "execution_diagnostics_status: degraded" in report
    assert "execution_balance_gap_detected: True" in report
    assert "execution_fills_gap_detected: False" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: degraded" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: False" in report
    assert "execution_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_status: degraded" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "readiness_next_phase_candidate: Stay Phase 1" in report
    assert "readiness_execution_ready: False" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "timeline_latest_operation: operations_snapshot" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_execution_gap_history_status: ok" in report
    assert "timeline_latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "timeline_latest_readiness_execution_ready: False" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "## Quick Navigation" in report
    assert f"- operations_audit_pack_report: {tmp_path / 'audit.md'}" in report
    assert f"- phase_gate_review_report: {tmp_path / 'reports/phase_gate_review.md'}" in report
    assert "## Related Reports" in report
    manifest = read_json(tmp_path / "audit.json")
    assert isinstance(manifest, dict)
    assert manifest["timeline_latest_remediation_planner_status"] == "stalled"
    assert manifest["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert manifest["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"
    assert manifest["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert manifest["quick_navigation"]["operations_audit_pack_report"] == str(tmp_path / "audit.md")
    assert (
        manifest["related_reports"]["phase_gate_review_report"]
        == str(tmp_path / "reports/phase_gate_review.md")
    )
    assert (
        manifest["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )


def test_build_audit_timeline_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["dry_run"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T03:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
                '{"created_at":"2026-05-24T04:00:00+00:00","operation":"remediation_planner_dry_run","status":"stalled","notes":["planner_status=stalled","next_best_command=uv run sis validate-artifacts --strict","next_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T05:00:00+00:00","operation":"remediation_execution_plan_dry_run","status":"stalled","notes":["execution_plan_status=stalled","next_action_command=uv run sis diagnose-quotes","next_action_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T06:00:00+00:00","operation":"remediation_session_dry_run","status":"ready_for_dry_run","notes":["session_status=ready_for_dry_run","next_pending_command=uv run sis monitoring-status","next_pending_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T07:00:00+00:00","operation":"remediation_session_checkpoint","status":"retry_pending","notes":["checkpoint_status=retry_pending","next_action_command=uv run sis phase-gate-review","next_action_stage_signal_confidence=low","next_action_feedback_priority_reason=evaluation_failed"]}',
                '{"created_at":"2026-05-24T08:00:00+00:00","operation":"remediation_scoreboard","status":"retrying","notes":["scoreboard_status=retrying","next_action_command=uv run sis phase-gate-review","next_action_stage_signal_confidence=low","next_action_feedback_priority_reason=evaluation_failed"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_audit_timeline_report(
        operation_chain_path=operation_chain,
        out_path=tmp_path / "audit_timeline.md",
        summary_path=tmp_path / "audit_timeline_summary.json",
    )

    assert "Audit Timeline Report" in report
    assert "audit_entry_count: 3" in report
    assert "latest_operation: audit_bundle_snapshot" in report
    assert "operations_snapshot: 1" in report
    assert "audit_bundle_snapshot: 1" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_diagnostics_status: degraded" in report
    assert "latest_execution_drift_overview_status: degraded" in report
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in report
    assert "latest_execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "latest_execution_gap_history_status: ok" in report
    assert "latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "latest_execution_state_comparison_status_match: False" in report
    assert "latest_execution_state_comparison_mismatching_count: 1" in report
    assert "latest_readiness_next_phase: Phase 1" in report
    assert "latest_readiness_execution_ready: False" in report
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field" in report
    assert "latest_remediation_planner_status: stalled" in report
    assert "latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "latest_remediation_execution_plan_status: stalled" in report
    assert "latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "latest_remediation_session_status: ready_for_dry_run" in report
    assert "latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "latest_remediation_checkpoint_status: retry_pending" in report
    assert "latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "latest_remediation_scoreboard_status: retrying" in report
    assert "latest_remediation_scoreboard_next_action_command: uv run sis phase-gate-review" in report
    assert "degraded: 2" in report
    assert "ok: 1" in report
    assert "True: 1" in report
    assert "False: 2" in report
    assert "False: 2" in report
    assert "True: 1" in report
    assert "1: 2" in report
    assert "0: 1" in report
    assert "## Quick Navigation" in report
    assert f"- audit_timeline_report: {tmp_path / 'audit_timeline.md'}" in report
    assert "## Related Reports" in report
    assert f"- audit_dashboard_report: {tmp_path / 'reports/audit_dashboard.md'}" in report
    summary = read_json(tmp_path / "audit_timeline_summary.json")
    assert isinstance(summary, dict)
    assert summary["quick_navigation"]["audit_timeline_report"] == str(tmp_path / "audit_timeline.md")
    assert (
        summary["related_reports"]["audit_dashboard_report"]
        == str(tmp_path / "reports/audit_dashboard.md")
    )
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == "1"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["latest_remediation_planner_status"] == "stalled"
    assert summary["latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["latest_remediation_scoreboard_next_action_command"] == "uv run sis phase-gate-review"


def test_build_audit_dashboard(tmp_path) -> None:
    bundle = tmp_path / "bundle.json"
    audit_pack = tmp_path / "audit_pack.json"
    audit_timeline = tmp_path / "audit_timeline.json"
    audit_bundle_history = tmp_path / "audit_bundle_history.json"
    execution = tmp_path / "execution.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    phase_gate = tmp_path / "phase_gate.json"
    write_json(bundle, {"overall_status": "ok", "cycle_count": 2, "completed_cycle_count": 2})
    write_json(
        audit_pack,
        {
            "overall_status": "ok",
            "timeline_latest_operation": "operations_audit_snapshot",
            "timeline_latest_status": "ok",
            "cycle_count": 2,
            "completed_cycle_count": 2,
        },
    )
    write_json(
        audit_timeline,
        {
            "audit_entry_count": 4,
            "latest_operation": "operations_audit_snapshot",
            "latest_status": "ok",
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "latest_execution_overall_status": "ok",
            "latest_execution_venue_count": 2,
            "latest_execution_comparison_all_registries_present": True,
            "latest_remediation_planner_status": "stalled",
            "latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "latest_remediation_execution_plan_status": "stalled",
            "latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "latest_remediation_session_status": "ready_for_dry_run",
            "latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "latest_remediation_checkpoint_status": "retry_pending",
            "latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "latest_remediation_scoreboard_status": "retrying",
            "latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "operation_counts": {"operations_snapshot": 2, "operations_audit_snapshot": 2},
        },
    )
    write_json(
        audit_bundle_history,
        {
            "snapshot_count": 3,
            "ok_count": 3,
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "latest_execution_overall_status": "ok",
            "latest_execution_venue_count": 2,
            "latest_execution_comparison_all_registries_present": True,
        },
    )
    write_json(execution, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(
        execution_diagnostics,
        {"overall_status": "degraded", "balance_gap_detected": True, "fills_gap_detected": False},
    )
    write_json(execution_gap_history, {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"})
    write_json(execution_state_comparison, {"entry_count": 4, "latest_status_match": False, "mismatching_count": 1})
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
    )
    write_json(
        execution_drift_overview,
        {
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(readiness, {"next_phase_candidate": "Stay Phase 1", "execution_ready": False})
    write_json(
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
            ],
        },
    )

    report = build_audit_dashboard(
        bundle_manifest_path=bundle,
        audit_pack_path=audit_pack,
        audit_timeline_summary_path=audit_timeline,
        audit_bundle_history_summary_path=audit_bundle_history,
        execution_snapshot_summary_path=execution,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        phase_gate_summary_path=phase_gate,
        out_path=tmp_path / "audit_dashboard.md",
        summary_path=tmp_path / "audit_dashboard_summary.json",
    )

    assert "Audit Dashboard" in report
    assert "overall_status: ok" in report
    assert "audit_entry_count: 4" in report
    assert "operations_audit_snapshot_count: 2" in report
    assert "bundle_history_snapshot_count: 3" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert (
        "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict"
        in report
    )
    assert "timeline_latest_remediation_execution_plan_status: stalled" in report
    assert (
        "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes"
        in report
    )
    assert "timeline_latest_remediation_session_status: ready_for_dry_run" in report
    assert (
        "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status"
        in report
    )
    assert "timeline_latest_remediation_checkpoint_status: retry_pending" in report
    assert (
        "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review"
        in report
    )
    assert "timeline_latest_remediation_scoreboard_status: retrying" in report
    assert (
        "timeline_latest_remediation_scoreboard_next_action_command: uv run sis phase-gate-review"
        in report
    )
    assert "bundle_history_latest_execution_overall_status: ok" in report
    assert "bundle_history_latest_execution_venue_count: 2" in report
    assert "bundle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_all_registries_present: True" in report
    assert "execution_diagnostics_status: degraded" in report
    assert "execution_balance_gap_detected: True" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: degraded" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: False" in report
    assert "execution_state_comparison_mismatching_count: 1" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "execution_drift_overview_status: degraded" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "readiness_next_phase_candidate: Stay Phase 1" in report
    assert "readiness_execution_ready: False" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    summary = read_json(tmp_path / "audit_dashboard_summary.json")
    assert isinstance(summary, dict)
    assert summary["audit_summary"]["audit_overall_status"] == "ok"
    assert summary["timeline_latest_execution_overall_status"] == "ok"
    assert summary["timeline_latest_execution_venue_count"] == 2
    assert summary["timeline_latest_execution_comparison_all_registries_present"] is True
    assert summary["timeline_latest_remediation_planner_status"] == "stalled"
    assert summary["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert summary["timeline_latest_remediation_session_next_pending_command"] == "uv run sis monitoring-status"
    assert summary["timeline_latest_remediation_scoreboard_next_action_command"] == "uv run sis phase-gate-review"
    assert summary["quick_navigation"]["audit_dashboard_report"] == str(tmp_path / "audit_dashboard.md")
    assert (
        summary["related_reports"]["operations_dashboard_report"]
        == str(tmp_path / "reports/operations_dashboard.md")
    )
    assert summary["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["bundle_history_latest_execution_overall_status"] == "ok"
    assert summary["bundle_history_latest_execution_venue_count"] == 2
    assert summary["bundle_history_latest_execution_comparison_all_registries_present"] is True
    assert summary["bundle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert summary["execution_state_comparison_summary"]["execution_state_comparison_entry_count"] == 4
    assert summary["execution_snapshot_drift_summary"]["execution_snapshot_drift_entry_count"] == 3
    assert summary["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"


def test_build_audit_bundle_manifest(tmp_path) -> None:
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_timeline = tmp_path / "audit_timeline.json"
    audit_pack = tmp_path / "audit_pack.json"
    audit_bundle_history = tmp_path / "audit_bundle_history.json"
    execution = tmp_path / "execution.json"
    execution_comparison = tmp_path / "execution_comparison.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_state_comparison = tmp_path / "execution_state_comparison.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    readiness = tmp_path / "readiness.json"
    phase_gate = tmp_path / "phase_gate.json"
    write_json(audit_dashboard, {"overall_status": "ok", "cycle_count": 2, "completed_cycle_count": 2})
    write_json(
        audit_timeline,
        {
            "audit_entry_count": 5,
            "latest_operation": "audit_bundle_snapshot",
            "latest_status": "ok",
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "latest_execution_overall_status": "ok",
            "latest_execution_venue_count": 2,
            "latest_execution_comparison_all_registries_present": True,
            "latest_execution_gap_history_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "degraded",
            "latest_readiness_execution_ready": False,
            "latest_remediation_planner_status": "stalled",
            "latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
            "latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_execution_plan_status": "stalled",
            "latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
            "latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_session_status": "ready_for_dry_run",
            "latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
            "latest_remediation_session_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_checkpoint_status": "retry_pending",
            "latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
            "latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
            "latest_remediation_scoreboard_status": "retrying",
            "latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
            "latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        },
    )
    write_json(
        audit_pack,
        {
            "overall_status": "ok",
            "cycle_count": 2,
            "completed_cycle_count": 2,
        },
    )
    write_json(
        audit_bundle_history,
        {
            "snapshot_count": 3,
            "ok_count": 3,
            "latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "latest_execution_overall_status": "ok",
            "latest_execution_venue_count": 2,
            "latest_execution_comparison_all_registries_present": True,
            "latest_execution_gap_history_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "degraded",
            "latest_readiness_execution_ready": False,
        },
    )
    write_json(execution, {"overall_status": "ok", "venue_count": 2})
    write_json(execution_comparison, {"all_registries_present": True})
    write_json(
        execution_diagnostics,
        {"overall_status": "degraded", "balance_gap_detected": True, "fills_gap_detected": False},
    )
    write_json(
        execution_gap_history,
        {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"},
    )
    write_json(execution_state_comparison, {"entry_count": 4, "latest_status_match": False, "mismatching_count": 1})
    write_json(
        execution_snapshot_drift,
        {
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
        },
    )
    write_json(
        execution_drift_overview,
        {
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
    )
    write_json(readiness, {"next_phase_candidate": "Stay Phase 1", "execution_ready": False})
    write_json(
        phase_gate,
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
        },
    )

    report = build_audit_bundle_manifest(
        audit_dashboard_summary_path=audit_dashboard,
        audit_timeline_summary_path=audit_timeline,
        audit_pack_path=audit_pack,
        audit_bundle_history_summary_path=audit_bundle_history,
        execution_snapshot_summary_path=execution,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_state_comparison_history_summary_path=execution_state_comparison,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        execution_drift_overview_summary_path=execution_drift_overview,
        readiness_summary_path=readiness,
        phase_gate_summary_path=phase_gate,
        out_path=tmp_path / "audit_bundle.md",
        manifest_path=tmp_path / "audit_bundle.json",
    )

    assert "Audit Bundle Manifest" in report
    assert "overall_status: ok" in report
    assert "audit_entry_count: 5" in report
    assert "timeline_latest_operation: audit_bundle_snapshot" in report
    assert "timeline_latest_execution_overall_status: ok" in report
    assert "timeline_latest_execution_venue_count: 2" in report
    assert "timeline_latest_execution_comparison_all_registries_present: True" in report
    assert "timeline_latest_execution_gap_history_status: ok" in report
    assert "timeline_latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "timeline_latest_readiness_execution_ready: False" in report
    assert "timeline_latest_remediation_planner_status: stalled" in report
    assert "timeline_latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "timeline_latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "timeline_latest_remediation_execution_plan_next_action_command: uv run sis diagnose-quotes" in report
    assert "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "timeline_latest_remediation_checkpoint_next_action_command: uv run sis phase-gate-review" in report
    assert "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed" in report
    assert "bundle_history_snapshot_count: 3" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    assert "execution_comparison_all_registries_present: True" in report
    assert "execution_diagnostics_status: degraded" in report
    assert "execution_balance_gap_detected: True" in report
    assert "execution_gap_history_entry_count: 4" in report
    assert "execution_gap_history_latest_status: ok" in report
    assert "execution_gap_history_latest_diagnostics_status: degraded" in report
    assert "execution_state_comparison_entry_count: 4" in report
    assert "execution_state_comparison_latest_status_match: False" in report
    assert "execution_state_comparison_mismatching_count: 1" in report
    assert "execution_snapshot_drift_entry_count: 3" in report
    assert "execution_snapshot_drift_latest_status_match: True" in report
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "execution_drift_overview_status: degraded" in report
    assert "execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "readiness_next_phase_candidate: Stay Phase 1" in report
    assert "readiness_execution_ready: False" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "bundle_history_latest_execution_overall_status: ok" in report
    assert "bundle_history_latest_execution_venue_count: 2" in report
    assert "bundle_history_latest_execution_comparison_all_registries_present: True" in report
    assert "bundle_history_latest_execution_gap_history_status: ok" in report
    assert "bundle_history_latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "bundle_history_latest_readiness_execution_ready: False" in report
    assert "## Quick Navigation" in report
    assert f"- audit_bundle_report: {tmp_path / 'audit_bundle.md'}" in report
    assert "## Related Reports" in report
    manifest = read_json(tmp_path / "audit_bundle.json")
    assert isinstance(manifest, dict)
    assert manifest["timeline_latest_remediation_planner_status"] == "stalled"
    assert manifest["timeline_latest_remediation_execution_plan_next_action_command"] == "uv run sis diagnose-quotes"
    assert manifest["timeline_latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"
    assert manifest["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        manifest["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert (
        manifest["bundle_history_latest_execution_summary"]["execution_overall_status"]
        == "ok"
    )
    assert (
        manifest["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert manifest["quick_navigation"]["audit_bundle_report"] == str(tmp_path / "audit_bundle.md")


def test_build_audit_bundle_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    execution = tmp_path / "execution.json"
    operation_chain.write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok"]}',
                '{"run_id":"r2","created_at":"2026-05-24T01:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"run_id":"r3","created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_overall_status=ok","execution_venue_count=2","execution_comparison_all_registries_present=True","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field","planner_status=stalled","next_best_command=uv run sis validate-artifacts --strict","next_feedback_priority_reason=evaluation_failed","execution_plan_status=stalled","next_action_command=uv run sis phase-gate-review","next_action_feedback_priority_reason=evaluation_failed","session_status=ready_for_dry_run","next_pending_command=uv run sis monitoring-status","next_pending_feedback_priority_reason=evaluation_failed","checkpoint_status=retry_pending","scoreboard_status=retrying"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(execution, {"overall_status": "ok", "venue_count": 2})

    report = build_audit_bundle_history_report(
        operation_chain_path=operation_chain,
        execution_snapshot_summary_path=execution,
        out_path=tmp_path / "audit_bundle_history.md",
        summary_path=tmp_path / "audit_bundle_history_summary.json",
    )

    assert "Audit Bundle History Report" in report
    assert "snapshot_count: 2" in report
    assert "ok_count: 2" in report
    assert "latest_run_id: r3" in report
    assert "latest_execution_overall_status: ok" in report
    assert "latest_execution_venue_count: 2" in report
    assert "latest_execution_comparison_all_registries_present: True" in report
    assert "latest_execution_gap_history_status: ok" in report
    assert "latest_execution_drift_overview_status: degraded" in report
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in report
    assert "latest_execution_drift_overview_state_comparison_mismatching_count: 1" in report
    assert "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in report
    assert "latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "latest_execution_state_comparison_status_match: False" in report
    assert "latest_execution_state_comparison_mismatching_count: 1" in report
    assert "latest_readiness_next_phase: Phase 1" in report
    assert "latest_readiness_execution_ready: False" in report
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "latest_phase2_entry_allowed: False" in report
    assert "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "latest_phase_gate_strict_validation_passed: False" in report
    assert "latest_phase_gate_strict_validation_issue_count: 2" in report
    assert "latest_phase_gate_checked_files: 7" in report
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field" in report
    assert "latest_remediation_planner_status: stalled" in report
    assert "latest_remediation_planner_next_best_command: uv run sis validate-artifacts --strict" in report
    assert "latest_remediation_planner_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_execution_plan_status: stalled" in report
    assert "latest_remediation_execution_plan_next_action_command: uv run sis phase-gate-review" in report
    assert "latest_remediation_execution_plan_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_session_status: ready_for_dry_run" in report
    assert "latest_remediation_session_next_pending_command: uv run sis monitoring-status" in report
    assert "latest_remediation_session_feedback_priority_reason: evaluation_failed" in report
    assert "latest_remediation_checkpoint_status: retry_pending" in report
    assert "latest_remediation_scoreboard_status: retrying" in report
    assert "## Quick Navigation" in report
    assert f"- audit_bundle_history_report: {tmp_path / 'audit_bundle_history.md'}" in report
    assert "## Related Reports" in report
    assert f"- audit_dashboard_report: {tmp_path / 'reports/audit_dashboard.md'}" in report
    assert "latest_phase_gate_strict_validation_issue_count: 2" in report
    assert "latest_phase_gate_checked_files: 7" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    summary = read_json(tmp_path / "audit_bundle_history_summary.json")
    assert isinstance(summary, dict)
    assert summary["latest_remediation_planner_status"] == "stalled"
    assert summary["latest_remediation_execution_plan_next_action_command"] == "uv run sis phase-gate-review"
    assert summary["latest_remediation_scoreboard_status"] == "retrying"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        summary["latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert summary["latest_execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == "1"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert (
        summary["quick_navigation"]["audit_bundle_history_report"]
        == str(tmp_path / "audit_bundle_history.md")
    )
    assert (
        summary["related_reports"]["audit_dashboard_report"]
        == str(tmp_path / "reports/audit_dashboard.md")
    )
def test_build_quote_diagnostics_report(tmp_path) -> None:
    raw_quote = tmp_path / "raw/quotes/gtrade/2026-05-22.jsonl"
    raw_quote.parent.mkdir(parents=True, exist_ok=True)
    raw_quote.write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.0,"index_price":100.0,"spread_bps":2.0,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"a","oracle_ts_ms":1747872000000}',
                '{"ts_client":"2026-05-22T00:05:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.5,"index_price":100.5,"spread_bps":3.0,"market_status":"open","is_tradable":false,"source":"test","raw_payload_sha256":"b","oracle_ts_ms":1747872300000}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_quote_diagnostics_report(
        raw_quotes_root=tmp_path / "raw/quotes",
        venue="gtrade",
        symbol="SPY",
        stale_thresholds_ms={"gtrade": 3000},
        out_path=tmp_path / "quote_diagnostics.md",
        summary_path=tmp_path / "quote_diagnostics_summary.json",
    )

    assert "Quote Diagnostics Report" in report
    assert "## Quick Navigation" in report
    assert f"- quote_diagnostics_report: {tmp_path / 'quote_diagnostics.md'}" in report
    assert "## Related Reports" in report
    assert f"- execution_venue_diagnostics_report: {tmp_path / 'execution_venue_diagnostics.md'}" in report
    summary = read_json(tmp_path / "quote_diagnostics_summary.json")
    assert summary["diagnostic_count"] == 1
    assert summary["row_count"] == 2
    assert summary["quick_navigation"]["quote_diagnostics_report"] == str(
        tmp_path / "quote_diagnostics.md"
    )
    assert summary["related_reports"]["execution_venue_diagnostics_report"] == str(
        tmp_path / "execution_venue_diagnostics.md"
    )


def test_build_cost_matrix_report(tmp_path) -> None:
    csv_path = tmp_path / "venue_cost_matrix.csv"
    csv_path.write_text(
        "\n".join(
            [
                "venue,symbol,asset_class,open_fee_bps,close_fee_bps,spread_p50_bps,spread_p90_bps,spread_p99_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps,stale_rate,tradable_rate,notes",
                "gtrade,SPY,index,5,5,2.0,3.0,3.0,,,,0.5,0.5,test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_cost_matrix_report(
        cost_matrix_path=csv_path,
        out_path=tmp_path / "venue_cost_matrix.md",
        summary_path=tmp_path / "venue_cost_matrix_summary.json",
    )

    assert "Venue Cost Matrix Report" in report
    assert "## Quick Navigation" in report
    assert f"- venue_cost_matrix_report: {tmp_path / 'venue_cost_matrix.md'}" in report
    assert "## Related Reports" in report
    assert f"- quote_diagnostics_report: {tmp_path / 'quote_diagnostics.md'}" in report
    summary = read_json(tmp_path / "venue_cost_matrix_summary.json")
    assert summary["row_count"] == 1
    assert summary["venues"] == ["gtrade"]
    assert summary["symbols"] == ["SPY"]
    assert summary["quick_navigation"]["venue_cost_matrix_report"] == str(
        tmp_path / "venue_cost_matrix.md"
    )
    assert summary["related_reports"]["quote_diagnostics_report"] == str(
        tmp_path / "quote_diagnostics.md"
    )
