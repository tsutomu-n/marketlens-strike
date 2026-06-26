from __future__ import annotations

from sis.reports.readiness_snapshot_markdown_sections import (
    overall_section_lines,
    phase_gate_section_lines,
    readiness_flags_section_lines,
)


def _summary() -> dict[str, object]:
    return {
        "overall_status": "ok",
        "next_phase_candidate": "Phase 2",
        "phase_gate_decision": "GO",
        "phase2_entry_allowed": True,
        "phase2_entry_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 0,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "execution_ready": True,
        "backtest_ready": True,
        "live_evidence_ready": True,
        "operations_ready": True,
        "research_quality_report_exists": True,
    }


def test_overall_section_lines_preserve_exact_order() -> None:
    assert overall_section_lines(_summary()) == [
        "## Overall",
        "",
        "- overall_status: ok",
        "- next_phase_candidate: Phase 2",
    ]


def test_phase_gate_section_lines_preserve_exact_order() -> None:
    assert phase_gate_section_lines(_summary()) == [
        "## Phase Gate",
        "",
        "- phase_gate_decision: GO",
        "- phase2_entry_allowed: True",
        "- phase2_entry_reason: decision_cleared_and_phase1_gate_complete",
        "- phase_gate_reason: decision_cleared_and_phase1_gate_complete",
        "- phase_gate_strict_validation_passed: True",
        "- phase_gate_strict_validation_issue_count: 0",
        "- phase_gate_checked_files: 7",
        "- phase_gate_review_report_path: data/reports/phase_gate_review.md",
    ]


def test_readiness_flags_section_lines_preserve_exact_order() -> None:
    assert readiness_flags_section_lines(_summary()) == [
        "## Readiness Flags",
        "",
        "- execution_ready: True",
        "- backtest_ready: True",
        "- live_evidence_ready: True",
        "- operations_ready: True",
        "- research_quality_report_exists: True",
    ]
