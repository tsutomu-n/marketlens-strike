from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import read_json, write_json


def _safe_read_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def build_paper_operations_runbook(
    *,
    scheduled_run_path: Path | None = None,
    daemon_manifest_path: Path | None = None,
    monitoring_snapshot_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    readiness_summary_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    ops_dashboard_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    scheduled_run = _safe_read_json(scheduled_run_path)
    daemon_manifest = _safe_read_json(daemon_manifest_path)
    monitoring = _safe_read_json(monitoring_snapshot_path)
    execution = _safe_read_json(execution_snapshot_summary_path)
    execution_comparison = _safe_read_json(execution_venue_comparison_summary_path)
    execution_diagnostics = _safe_read_json(execution_venue_diagnostics_summary_path)
    execution_gap_history = _safe_read_json(execution_gap_history_summary_path)
    execution_state_comparison = _safe_read_json(execution_state_comparison_history_summary_path)
    execution_snapshot_drift = _safe_read_json(execution_snapshot_drift_history_summary_path)
    execution_drift_overview = normalize_execution_drift_overview_summary(
        _safe_read_json(execution_drift_overview_summary_path)
    )
    readiness = normalize_readiness_summary(_safe_read_json(readiness_summary_path))
    phase_gate = normalize_phase_gate_summary(_safe_read_json(phase_gate_summary_path))
    dashboard = _safe_read_json(ops_dashboard_summary_path)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    readiness_fields = readiness_flat_fields(readiness)
    phase_gate_fields = phase_gate_flat_fields(phase_gate)

    summary = {
        "scheduled_run_type": scheduled_run.get("run_type"),
        "scheduled_for": scheduled_run.get("scheduled_for"),
        "scheduled_command": scheduled_run.get("command"),
        "daemon_mode": daemon_manifest.get("mode"),
        "monitoring_status": monitoring.get("status"),
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        "dashboard_status": dashboard.get("overall_status"),
    }

    lines = [
        "# Scheduled Paper Operations Runbook",
        "",
        "## Current Schedule",
        "",
        f"- run_type: {summary['scheduled_run_type']}",
        f"- scheduled_for: {summary['scheduled_for']}",
        f"- command: {summary['scheduled_command']}",
        "",
        "## Current Daemon Context",
        "",
        f"- daemon_mode: {summary['daemon_mode']}",
        f"- daemon_command: {daemon_manifest.get('command')}",
        f"- state_store_path: {daemon_manifest.get('state_store_path')}",
        "",
        "## Current Status",
        "",
        f"- monitoring_status: {summary['monitoring_status']}",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}",
        f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
        f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}",
        f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}",
        f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}",
        f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}",
        (
            "- execution_state_comparison_latest_status_match: "
            f"{summary['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{summary['execution_state_comparison_mismatching_count']}"
        ),
        f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}",
        (
            "- execution_snapshot_drift_latest_status_match: "
            f"{summary['execution_snapshot_drift_latest_status_match']}"
        ),
        (
            "- execution_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}",
        (
            "- execution_drift_overview_diagnostics_alignment_match: "
            f"{summary['execution_drift_overview_diagnostics_alignment_match']}"
        ),
        (
            "- execution_drift_overview_state_comparison_mismatching_count: "
            f"{summary['execution_drift_overview_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
        ),
        f"- readiness_next_phase_candidate: {summary['readiness_next_phase_candidate']}",
        f"- readiness_execution_ready: {summary['readiness_execution_ready']}",
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        f"- dashboard_status: {summary['dashboard_status']}",
        "",
        "## Strict Validation Preview",
        "",
    ]
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(
        [
            "",
        "## Recommended Sequence",
        "",
        "1. Run `uv run sis refresh-operations-artifacts`.",
        "2. Review `data/reports/execution_venue_comparison.md` for cross-venue execution state.",
        "3. Review `data/reports/execution_venue_diagnostics.md` for cross-venue gaps and deltas.",
        "4. Review `data/reports/execution_gap_history.md` for gap/reaction history.",
        "5. Review `data/reports/execution_state_comparison_history.md` for diagnostics-vs-history mismatches.",
        "6. Review `data/reports/execution_snapshot_drift_history.md` for snapshot-only drift.",
        "7. Review `data/reports/execution_drift_overview.md` for the combined drift judgement.",
        "8. Review `data/reports/readiness_snapshot.md` for current phase readiness.",
        "9. Review `data/reports/operations_dashboard.md` for overall status.",
        "10. Review `data/reports/ops_review_report.md` for latest operation chain details.",
        "11. If status is acceptable, run `uv run sis paper-step` or the scheduled paper command.",
        "12. Re-run `uv run sis refresh-operations-artifacts` after the paper step.",
        "",
        "## Stop Conditions",
        "",
        "- If `monitoring_status` is `degraded`, inspect missing artifacts before continuing.",
        "- If `dashboard_status` is `blocked`, do not proceed until the latest blocked cause is understood.",
        "- If `execution_diagnostics_status` is not `ok`, inspect execution venue gaps before continuing.",
        "- If `execution_state_comparison_latest_status_match` is not `True`, inspect diagnostics/history drift before continuing.",
        "- If `execution_snapshot_drift_mismatching_snapshot_count` is not `0`, inspect snapshot-only drift before continuing.",
        "- If `execution_drift_overview_status` is not `ok`, resolve the combined drift judgement before continuing.",
        "- If `readiness_execution_ready` is not `True`, stay in the current phase and inspect readiness blockers before continuing.",
        "- If `phase_gate_strict_validation_issue_count` is not `0`, run strict artifact validation and clear the reported issues before continuing.",
        "- If the kill switch is enabled, do not run paper or live-adjacent commands.",
        "",
        ]
    )

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
