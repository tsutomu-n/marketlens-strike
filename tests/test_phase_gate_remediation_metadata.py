from __future__ import annotations

from sis.reports.phase_gate_remediation_metadata import (
    remediation_execute_expected_outputs,
    remediation_postcheck_commands,
    remediation_postcheck_pass_signals,
    remediation_preflight_commands,
    remediation_preflight_expected_outputs,
    remediation_signal_snapshot_before,
    remediation_signal_snapshot_target,
    remediation_success_criteria,
)


def test_phase_gate_remediation_metadata_preserves_known_reason_outputs() -> None:
    assert remediation_success_criteria("missing_required_artifacts") == [
        "missing_required_artifact_paths is empty",
        "required artifact paths are non-null",
    ]
    assert remediation_preflight_commands("phase_gate_not_cleared") == ["uv run sis check-go-no-go"]
    assert remediation_postcheck_commands("phase_gate_not_cleared") == [
        "uv run sis build-evidence-card",
        "uv run sis phase-gate-review",
    ]
    assert remediation_execute_expected_outputs("execution_drift_unresolved") == [
        "execution_drift_overview_summary.json is regenerated",
        "drift status is re-evaluated from fresh artifacts",
    ]
    assert remediation_postcheck_pass_signals("diagnostics_unavailable") == [
        "diagnostics_all_available == True",
    ]


def test_phase_gate_remediation_metadata_preserves_code_status_expected_output() -> None:
    outputs = remediation_preflight_expected_outputs("missing_required_artifacts")

    assert outputs == [
        "implementation-status exits 0",
        "docs/CODE_STATUS.md is regenerated",
    ]


def test_phase_gate_remediation_signal_snapshots_preserve_summary_values() -> None:
    summary = {
        "strict_validation_issue_count": "2",
        "phase_gate_strict_validation_issue_count": 2,
    }

    assert remediation_signal_snapshot_before("strict_validation_failed", summary) == {
        "strict_validation_issue_count": "2",
        "phase_gate_strict_validation_issue_count": 2,
    }
    assert remediation_signal_snapshot_target("strict_validation_failed") == {
        "strict_validation_issue_count": 0,
        "phase_gate_strict_validation_issue_count": 0,
    }


def test_phase_gate_remediation_metadata_unknown_reason_returns_empty_values() -> None:
    assert remediation_success_criteria("unknown") == []
    assert remediation_preflight_commands("unknown") == []
    assert remediation_postcheck_commands("unknown") == []
    assert remediation_preflight_expected_outputs("unknown") == []
    assert remediation_execute_expected_outputs("unknown") == []
    assert remediation_postcheck_pass_signals("unknown") == []
    assert remediation_signal_snapshot_before("unknown", {}) == {}
    assert remediation_signal_snapshot_target("unknown") == {}
