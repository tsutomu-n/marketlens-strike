from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sis.reports.live_evidence_followup import (
    default_followup_output_path,
    default_html_output_path,
    render_live_evidence_followup,
)


def _followup_data(**overrides: object) -> SimpleNamespace:
    values = {
        "status": "completed",
        "decision": "GO",
        "log_path": Path("logs/live_evidence/live_evidence_20260522_2308.log"),
        "manifest_path": Path("logs/live_evidence/manifests/live_evidence_20260522_2308.json"),
        "output_path": Path("docs/live_evidence_reports/live_evidence_report_20260522_2308.md"),
        "audit_summary": {
            "overall_status": "ok",
            "latest_operation": "live_evidence",
            "bundle_history_snapshot_count": 2,
        },
        "phase_gate_summary": {
            "decision": "READ_ONLY_GO",
            "phase2_entry_allowed": True,
            "phase_gate_reason": "decision_cleared",
            "strict_validation_passed": True,
            "phase_gate_strict_validation_issue_count": 0,
            "phase_gate_checked_files": 10,
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        },
        "readiness_summary": {
            "next_phase_candidate": "Phase 2",
            "execution_ready": False,
        },
        "timeline_latest_execution_summary": {"overall_status": "ok", "venue_count": 2},
        "timeline_latest_execution_comparison_summary": {"all_registries_present": True},
        "bundle_history_latest_execution_summary": {},
        "bundle_history_latest_execution_comparison_summary": {},
        "cycle_history_latest_execution_summary": {},
        "cycle_history_latest_execution_comparison_summary": {},
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
            "overall_status": "ok",
            "balance_gap_detected": False,
            "fills_gap_detected": False,
            "report_path": "data/reports/execution_venue_diagnostics.md",
        },
        "execution_gap_history_summary": {
            "entry_count": 1,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "ok",
            "report_path": "data/reports/execution_gap_history.md",
        },
        "execution_state_comparison_summary": {
            "entry_count": 1,
            "latest_status_match": True,
            "mismatching_count": 0,
            "report_path": "data/reports/execution_state_comparison.md",
        },
        "execution_snapshot_drift_summary": {
            "entry_count": 1,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 0,
            "report_path": "data/reports/execution_snapshot_drift_history.md",
        },
        "execution_drift_overview_summary": {
            "execution_drift_overview_status": "ok",
            "execution_drift_overview_diagnostics_alignment_match": True,
            "execution_drift_overview_state_comparison_mismatching_count": 0,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 0,
        },
        "next_actions": [],
        "log_tail": ["tail line"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_default_followup_and_html_paths() -> None:
    log_path = Path("logs/live_evidence/live_evidence_20260522_2308.log")

    assert default_html_output_path(log_path) == Path(
        "docs/live_evidence_reports/live_evidence_report_20260522_2308.html"
    )
    assert default_followup_output_path(log_path) == Path(
        "docs/live_evidence_reports/live_evidence_followup_20260522_2308.md"
    )


def test_render_live_evidence_followup_direct_import_includes_core_sections() -> None:
    text = render_live_evidence_followup(_followup_data())

    assert "# Live Evidence Follow-up" in text
    assert "## Quick Navigation" in text
    assert "live_evidence_followup_report:" in text
    assert "## Audit Summary" in text
    assert "- overall_status: `ok`" in text
    assert "## Latest Execution Lineage" in text
    assert "timeline_latest_execution_overall_status" in text
    assert "## Immediate Next Work" in text
    assert "- no blocking follow-up was emitted by the report" in text


def test_render_live_evidence_followup_uses_status_specific_next_work() -> None:
    running = render_live_evidence_followup(_followup_data(status="running"))
    failed = render_live_evidence_followup(_followup_data(status="failed"))
    emitted = render_live_evidence_followup(_followup_data(next_actions=["rerun diagnostics"]))

    assert "collection is still running" in running
    assert "fix the first blocking error" in failed
    assert "- rerun diagnostics" in emitted
