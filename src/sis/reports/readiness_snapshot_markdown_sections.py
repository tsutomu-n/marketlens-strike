from __future__ import annotations

from typing import Any


def overall_section_lines(summary: dict[str, Any]) -> list[str]:
    return [
        "## Overall",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- next_phase_candidate: {summary['next_phase_candidate']}",
    ]


def phase_gate_section_lines(summary: dict[str, Any]) -> list[str]:
    return [
        "## Phase Gate",
        "",
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase2_entry_reason: {summary['phase2_entry_reason']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        (
            "- phase_gate_strict_validation_passed: "
            f"{summary['phase_gate_strict_validation_passed']}"
        ),
        (
            "- phase_gate_strict_validation_issue_count: "
            f"{summary['phase_gate_strict_validation_issue_count']}"
        ),
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
    ]


def readiness_flags_section_lines(summary: dict[str, Any]) -> list[str]:
    return [
        "## Readiness Flags",
        "",
        f"- execution_ready: {summary['execution_ready']}",
        f"- backtest_ready: {summary['backtest_ready']}",
        f"- live_evidence_ready: {summary['live_evidence_ready']}",
        f"- operations_ready: {summary['operations_ready']}",
        f"- research_quality_report_exists: {summary['research_quality_report_exists']}",
    ]
