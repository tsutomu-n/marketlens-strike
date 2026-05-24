from __future__ import annotations

import polars as pl

from sis.reports.audit_bundle_history import build_audit_bundle_history_report
from sis.reports.audit_bundle import build_audit_bundle_manifest
from sis.ops.monitoring import build_monitoring_snapshot, write_monitoring_snapshot
from sis.reports.audit_dashboard import build_audit_dashboard
from sis.reports.comparison import build_paper_live_comparison_report
from sis.reports.current_state_index import build_current_state_index
from sis.reports.execution_drift_overview import build_execution_drift_overview_report
from sis.reports.execution_gap_history import build_execution_gap_history_report
from sis.reports.execution_snapshot_drift_history import build_execution_snapshot_drift_history_report
from sis.reports.execution_state_comparison_history import build_execution_state_comparison_history_report
from sis.reports.weekly_review import build_weekly_review_report
from sis.reports.audit_timeline import build_audit_timeline_report
from sis.reports.operations_audit_pack import build_operations_audit_pack
from sis.reports.operations_bundle import build_operations_bundle_manifest
from sis.reports.ops_review import build_ops_review_report
from sis.reports.paper_cycle_history import build_paper_cycle_history_report
from sis.reports.operations_dashboard import build_operations_dashboard
from sis.reports.operations_timeline import build_operations_timeline_report
from sis.reports.paper_operations_runbook import build_paper_operations_runbook
from sis.reports.readiness_snapshot import build_readiness_snapshot
from sis.storage.jsonl_store import read_json, write_json


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
        },
    )
    write_json(audit_bundle, {"bundle_history_snapshot_count": 3, "bundle_history_ok_count": 3})
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
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
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
    assert "Paper Last Run Audit" in report
    assert "latest_operation: audit_bundle_snapshot" in report
    assert "Paper Last Run Phase Gate" in report
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "Paper Last Run Execution Drift Overview" in report
    assert "overall_status: degraded" in report


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
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    )

    report = build_weekly_review_report(
        backtest_metrics_path=backtest_metrics,
        daily_pnl_path=daily_pnl,
        paper_last_run_path=paper_last_run,
        out_path=tmp_path / "weekly.md",
    )

    assert "Weekly Strategy Review" in report
    assert "Paper Last Run Audit" in report
    assert "overall_status: ok" in report
    assert "Paper Last Run Phase Gate" in report
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "Paper Last Run Execution Drift Overview" in report
    assert "overall_status: degraded" in report


def test_build_ops_review_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    monitoring = tmp_path / "monitoring.json"
    daemon_dry_run = tmp_path / "daemon_dry_run.json"
    execution_snapshot = tmp_path / "execution_snapshot.json"
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
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
    write_json(audit_dashboard, {"overall_status": "ok", "timeline_latest_operation": "audit_bundle_snapshot"})
    write_json(audit_bundle, {"bundle_history_snapshot_count": 3})
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
    assert "audit_latest_operation: audit_bundle_snapshot" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    summary = read_json(tmp_path / "ops_review_summary.json")
    assert isinstance(summary, dict)
    assert summary["audit_summary"]["audit_overall_status"] == "ok"
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"


def test_build_operations_dashboard(tmp_path) -> None:
    monitoring = tmp_path / "monitoring.json"
    ops_summary = tmp_path / "ops_review_summary.json"
    decision_summary = tmp_path / "decision_summary.json"
    execution_snapshot = tmp_path / "execution_snapshot.json"
    execution_diagnostics = tmp_path / "execution_diagnostics.json"
    execution_gap_history = tmp_path / "execution_gap_history.json"
    execution_drift_overview = tmp_path / "execution_drift_overview.json"
    execution_snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    audit_dashboard = tmp_path / "audit_dashboard.json"
    audit_bundle = tmp_path / "audit_bundle.json"
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
        audit_dashboard,
        {
            "overall_status": "ok",
            "timeline_latest_operation": "audit_bundle_snapshot",
            "audit_entry_count": 4,
            "audit_bundle_snapshot_count": 1,
        },
    )
    write_json(
        audit_bundle,
        {
            "bundle_history_snapshot_count": 3,
            "bundle_history_ok_count": 3,
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
        decision_summary_path=decision_summary,
        execution_snapshot_summary_path=execution_snapshot,
        execution_venue_comparison_summary_path=execution_comparison,
        execution_venue_diagnostics_summary_path=execution_diagnostics,
        execution_gap_history_summary_path=execution_gap_history,
        execution_drift_overview_summary_path=execution_drift_overview,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift,
        audit_dashboard_summary_path=audit_dashboard,
        audit_bundle_summary_path=audit_bundle,
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
    assert "audit_latest_operation: audit_bundle_snapshot" in report
    assert "audit_bundle_history_snapshot_count: 3" in report
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    summary = read_json(tmp_path / "dashboard_summary.json")
    assert isinstance(summary, dict)
    assert summary["phase2_entry_allowed"] is False
    assert summary["audit_summary"]["audit_overall_status"] == "ok"
    assert summary["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
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

    write_json(operations_dashboard, {"overall_status": "ok"})
    write_json(operations_bundle, {"cycle_count": 2})
    write_json(audit_dashboard, {"overall_status": "ok", "timeline_latest_operation": "audit_bundle_snapshot"})
    write_json(audit_bundle, {"bundle_history_snapshot_count": 3})
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
    assert "research_quality_report_exists: True" in report
    assert "## Recommended Read Order" in report
    summary = read_json(tmp_path / "current_state_index.json")
    assert isinstance(summary, dict)
    assert summary["recommended_read_order"][0] == "docs/ACCEPTANCE_AUDIT.md"
    assert summary["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert summary["phase_gate_strict_validation_passed"] is True
    assert summary["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["phase_gate_strict_validation_issues"][0]["path"] == "data/research/backtest_metrics_summary.json"
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
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert summary["execution_diagnostics_summary"]["execution_diagnostics_status"] == "ok"
    assert summary["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert summary["execution_state_comparison_summary"]["execution_state_comparison_entry_count"] == 4
    assert summary["execution_snapshot_drift_summary"]["execution_snapshot_drift_entry_count"] == 3
    assert summary["execution_drift_overview_summary"]["execution_drift_overview_status"] == "ok"


def test_build_execution_gap_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["execution_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
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
    assert "entry_count: 3" in report
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


def test_build_execution_state_comparison_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["execution_diagnostics_status=ok","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
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
    assert "entry_count: 3" in report
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


def test_build_execution_snapshot_drift_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["execution_diagnostics_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
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
    assert "entry_count: 3" in report
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


def test_build_execution_drift_overview_report(tmp_path) -> None:
    gap_history = tmp_path / "execution_gap_history.json"
    state_comparison = tmp_path / "execution_state_comparison.json"
    snapshot_drift = tmp_path / "execution_snapshot_drift.json"
    write_json(
        gap_history,
        {"entry_count": 4, "latest_status": "ok", "latest_execution_diagnostics_status": "degraded"},
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
    assert "overall_status: ok" in report
    assert "diagnostics_alignment_match: True" in report
    summary = read_json(tmp_path / "execution_drift_overview.json")
    assert summary["execution_drift_overview_status"] == "ok"
    assert summary["execution_drift_overview_diagnostics_alignment_match"] is True
    assert summary["execution_drift_overview_state_comparison_mismatching_count"] == 0
    assert summary["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] == 0
    assert summary["execution_drift_overview_report_path"] == str(
        tmp_path / "execution_drift_overview.md"
    )


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
    write_json(dashboard, {"overall_status": "ok"})

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
        out_path=tmp_path / "runbook.md",
        summary_path=tmp_path / "runbook_summary.json",
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
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "phase2_entry_allowed: False" in report
    assert "phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_strict_validation_issue_count: 2" in report
    assert "phase_gate_checked_files: 7" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report
    assert "dashboard_status: ok" in report
    summary = read_json(tmp_path / "runbook_summary.json")
    assert isinstance(summary, dict)
    assert summary["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert summary["phase_gate_strict_validation_issue_count"] == 2
    assert summary["phase_gate_checked_files"] == 7
    assert summary["phase2_entry_allowed"] is False
    assert summary["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert summary["phase_gate_strict_validation_issues"][0]["message"] == "missing field"


def test_build_paper_cycle_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-24T00:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"run_id":"r2","created_at":"2026-05-24T01:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":[]}',
                '{"run_id":"r3","created_at":"2026-05-24T02:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=2","fills=2","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
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
    assert "cycle_count: 2" in report
    assert "completed_count: 2" in report
    assert "total_orders: 3" in report
    assert "total_fills: 3" in report
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
    write_json(dashboard, {"overall_status": "ok"})
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
    write_json(cycle_history, {"cycle_count": 2, "completed_count": 2})
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
    assert "phase_gate_decision: GO" in report
    assert "phase2_entry_allowed: True" in report
    assert "phase_gate_reason: decision_cleared_and_phase1_gate_complete" in report
    assert "phase_gate_strict_validation_passed: True" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "issues: none" in report
    assert "## Recommended Read Order" in report
    manifest = read_json(tmp_path / "bundle.json")
    assert isinstance(manifest, dict)
    assert manifest["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert manifest["readiness_execution_ready"] is False
    assert manifest["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert manifest["phase_gate_strict_validation_passed"] is True
    assert manifest["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
    assert manifest["recommended_read_order"][0] == "docs/ACCEPTANCE_AUDIT.md"
    assert manifest["phase_gate_summary"]["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert manifest["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
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
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","mode":"paper","notes":["dry_run","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=planned","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","mode":"paper","notes":["orders=1","fills=1","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=completed","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","mode":"ops","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
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
    assert "operation_count: 3" in report
    assert "latest_operation: operations_snapshot" in report
    assert "daemon_dry_run: 1" in report
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
    summary = read_json(tmp_path / "timeline_summary.json")
    assert isinstance(summary, dict)
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == "1"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"


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
            "latest_execution_gap_history_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "degraded",
            "latest_readiness_execution_ready": False,
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
    assert "timeline_latest_execution_gap_history_status: ok" in report
    assert "timeline_latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "timeline_latest_readiness_execution_ready: False" in report
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in report
    assert "- data/research/backtest_metrics_summary.json: missing field" in report


def test_build_audit_timeline_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["dry_run"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T03:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
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
    assert "degraded: 2" in report
    assert "ok: 1" in report
    assert "True: 1" in report
    assert "False: 2" in report
    assert "False: 2" in report
    assert "True: 1" in report
    assert "1: 2" in report
    assert "0: 1" in report
    summary = read_json(tmp_path / "audit_timeline_summary.json")
    assert isinstance(summary, dict)
    assert summary["latest_execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == "1"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"


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
            "operation_counts": {"operations_snapshot": 2, "operations_audit_snapshot": 2},
        },
    )
    write_json(audit_bundle_history, {"snapshot_count": 3, "ok_count": 3})
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
            "latest_execution_gap_history_status": "ok",
            "latest_execution_gap_history_diagnostics_status": "degraded",
            "latest_readiness_execution_ready": False,
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
    assert "timeline_latest_execution_gap_history_status: ok" in report
    assert "timeline_latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "timeline_latest_readiness_execution_ready: False" in report
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
    assert "bundle_history_latest_execution_gap_history_status: ok" in report
    assert "bundle_history_latest_execution_gap_history_diagnostics_status: degraded" in report
    assert "bundle_history_latest_readiness_execution_ready: False" in report


def test_build_audit_bundle_history_report(tmp_path) -> None:
    operation_chain = tmp_path / "operation_manifests.jsonl"
    execution = tmp_path / "execution.json"
    operation_chain.write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok"]}',
                '{"run_id":"r2","created_at":"2026-05-24T01:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"run_id":"r3","created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
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
    assert "latest_phase_gate_strict_validation_issue_count: 2" in report
    assert "latest_phase_gate_checked_files: 7" in report
    assert "execution_overall_status: ok" in report
    assert "execution_venue_count: 2" in report
    summary = read_json(tmp_path / "audit_bundle_history_summary.json")
    assert isinstance(summary, dict)
    assert summary["execution_summary"]["execution_overall_status"] == "ok"
    assert summary["latest_execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert summary["latest_execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert summary["latest_execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == "1"
    assert summary["latest_readiness_summary"]["readiness_next_phase_candidate"] == "Phase 1"
    assert summary["latest_phase_gate_summary"]["phase_gate_review_report_path"] == "data/reports/phase_gate_review.md"
