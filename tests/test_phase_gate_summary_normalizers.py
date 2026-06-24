from __future__ import annotations

from sis.reports import summary_normalizers
from sis.reports.phase_gate_summary_normalizers import (
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_note_lines,
    phase_gate_issue_note_previews,
    phase_gate_issue_preview_lines,
    phase_gate_nested_fields,
    readiness_flat_fields,
)


def test_normalize_phase_gate_summary_preserves_prefixed_and_legacy_aliases() -> None:
    normalized = normalize_phase_gate_summary(
        {
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "legacy-reason",
            "phase_gate_reason": "prefixed-reason",
            "phase_gate_strict_validation_passed": False,
            "phase_gate_strict_validation_issue_count": 3,
            "phase_gate_checked_files": 9,
            "phase_gate_strict_validation_issues": [
                {"path": "data/research/backtest_metrics_summary.json", "message": "missing"}
            ],
            "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        }
    )

    assert normalized["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert normalized["phase2_entry_reason"] == "legacy-reason"
    assert normalized["phase_gate_reason"] == "prefixed-reason"
    assert normalized["strict_validation_passed"] is False
    assert normalized["strict_validation_issue_count"] == 3
    assert normalized["checked_files"] == 9
    assert normalized["strict_validation_issues"] == [
        {"path": "data/research/backtest_metrics_summary.json", "message": "missing"}
    ]


def test_phase_gate_flat_and_nested_fields_keep_expected_keys() -> None:
    summary = {
        "decision": "READ_ONLY_GO",
        "phase2_entry_allowed": True,
        "phase_gate_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 0,
        "phase_gate_checked_files": 7,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
    }

    assert phase_gate_flat_fields(summary) == {
        "phase_gate_decision": "READ_ONLY_GO",
        "phase2_entry_allowed": True,
        "phase2_entry_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 0,
        "phase_gate_checked_files": 7,
        "phase_gate_strict_validation_issues": None,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "strict_validation_passed": True,
    }
    assert phase_gate_nested_fields(summary) == {
        "decision": "READ_ONLY_GO",
        "phase2_entry_allowed": True,
        "phase2_entry_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_reason": "decision_cleared_and_phase1_gate_complete",
        "phase_gate_strict_validation_passed": True,
        "phase_gate_strict_validation_issue_count": 0,
        "phase_gate_checked_files": 7,
        "phase_gate_strict_validation_issues": None,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "strict_validation_issue_count": 0,
        "checked_files": 7,
        "strict_validation_issues": None,
        "strict_validation_passed": True,
    }


def test_phase_gate_issue_helpers_accept_dict_strings_and_notes() -> None:
    summary = {
        "phase_gate_strict_validation_issues": [
            {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"},
            {"path": "data/ops/execution_snapshot_summary.json"},
            {"message": "malformed payload"},
            "data/ops/execution_gap_history_summary.json: missing",
        ]
    }

    assert phase_gate_issue_preview_lines(summary) == [
        "data/research/backtest_metrics_summary.json: missing field",
        "data/ops/execution_snapshot_summary.json",
        "malformed payload",
        "data/ops/execution_gap_history_summary.json: missing",
    ]
    assert phase_gate_issue_note_lines(summary) == [
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field",
        "phase_gate_issue_2=data/ops/execution_snapshot_summary.json",
        "phase_gate_issue_3=malformed payload",
        "phase_gate_issue_4=data/ops/execution_gap_history_summary.json: missing",
    ]
    assert phase_gate_issue_note_previews(
        [
            "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field",
            "unrelated=value",
            "phase_gate_issue_2=data/ops/execution_snapshot_summary.json",
        ]
    ) == [
        "data/research/backtest_metrics_summary.json: missing field",
        "data/ops/execution_snapshot_summary.json",
    ]


def test_phase_gate_issue_note_lines_reports_none_without_issues() -> None:
    assert phase_gate_issue_note_lines({}) == ["phase_gate_issues=none"]


def test_readiness_normalizer_preserves_aliases_and_flat_fields() -> None:
    normalized = normalize_readiness_summary(
        {
            "readiness_next_phase_candidate": "Phase 2",
            "readiness_execution_ready": False,
        }
    )

    assert normalized["next_phase_candidate"] == "Phase 2"
    assert normalized["execution_ready"] is False
    assert readiness_flat_fields(normalized) == {
        "readiness_next_phase_candidate": "Phase 2",
        "readiness_execution_ready": False,
    }


def test_summary_normalizers_keeps_phase_gate_compatibility_aliases() -> None:
    assert summary_normalizers.normalize_phase_gate_summary is normalize_phase_gate_summary
    assert summary_normalizers.normalize_readiness_summary is normalize_readiness_summary
    assert summary_normalizers.phase_gate_flat_fields is phase_gate_flat_fields
    assert summary_normalizers.phase_gate_nested_fields is phase_gate_nested_fields
    assert summary_normalizers.phase_gate_issue_preview_lines is phase_gate_issue_preview_lines
    assert summary_normalizers.phase_gate_issue_note_previews is phase_gate_issue_note_previews
    assert summary_normalizers.phase_gate_issue_note_lines is phase_gate_issue_note_lines
    assert summary_normalizers.readiness_flat_fields is readiness_flat_fields
