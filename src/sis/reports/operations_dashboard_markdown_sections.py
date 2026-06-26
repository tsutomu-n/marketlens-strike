from __future__ import annotations

from typing import Any


def overall_section_lines(summary: dict[str, Any]) -> list[str]:
    return [
        "## Overall",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- monitoring_status: {summary['monitoring_status']}",
        f"- ops_latest_status: {summary['ops_latest_status']}",
        f"- operations_count: {summary['operations_count']}",
    ]


def decision_state_section_lines(summary: dict[str, Any]) -> list[str]:
    return [
        "## Decision State",
        "",
        f"- decision_mode: {summary['decision_mode']}",
        f"- executed_count: {summary['executed_count']}",
        f"- blocked_count: {summary['blocked_count']}",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        (
            "- execution_comparison_all_registries_present: "
            f"{summary['execution_comparison_all_registries_present']}"
        ),
        f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
        f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
        f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
        (f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}"),
        (
            "- execution_gap_history_latest_status: "
            f"{summary['execution_gap_history_latest_status']}"
        ),
        (
            "- execution_gap_history_latest_diagnostics_status: "
            f"{summary['execution_gap_history_latest_diagnostics_status']}"
        ),
        (
            "- execution_state_comparison_entry_count: "
            f"{summary['execution_state_comparison_entry_count']}"
        ),
        (
            "- execution_state_comparison_latest_status_match: "
            f"{summary['execution_state_comparison_latest_status_match']}"
        ),
        (
            "- execution_state_comparison_mismatching_count: "
            f"{summary['execution_state_comparison_mismatching_count']}"
        ),
        (
            "- execution_snapshot_drift_entry_count: "
            f"{summary['execution_snapshot_drift_entry_count']}"
        ),
        (
            "- execution_snapshot_drift_latest_status_match: "
            f"{summary['execution_snapshot_drift_latest_status_match']}"
        ),
        (
            "- execution_snapshot_drift_mismatching_snapshot_count: "
            f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
        ),
        (f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}"),
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
    ]
