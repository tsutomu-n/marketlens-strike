from sis.reports.doc_paths import CODE_STATUS_DOC
from sis.reports.paper_operations_remediation import artifact_recovery_commands
from sis.reports.paper_operations_remediation import remediation_execute_expected_outputs
from sis.reports.paper_operations_remediation import remediation_order
from sis.reports.paper_operations_remediation import remediation_postcheck_commands
from sis.reports.paper_operations_remediation import remediation_postcheck_pass_signals
from sis.reports.paper_operations_remediation import remediation_preflight_commands
from sis.reports.paper_operations_remediation import remediation_preflight_expected_outputs
from sis.reports.paper_operations_remediation import remediation_signal_snapshot_before
from sis.reports.paper_operations_remediation import remediation_signal_snapshot_target
from sis.reports.paper_operations_remediation import remediation_success_criteria


def test_artifact_recovery_commands_maps_known_and_unknown_artifacts() -> None:
    assert artifact_recovery_commands(
        [
            "scheduled_run_path",
            "phase_gate_summary_path",
            "unknown_artifact_path",
        ]
    ) == {
        "scheduled_run_path": ["uv run sis schedule-run --run-type paper --when <ISO8601>"],
        "phase_gate_summary_path": ["uv run sis phase-gate-review"],
        "unknown_artifact_path": ["uv run sis refresh-operations-artifacts"],
    }


def test_remediation_order_deduplicates_missing_artifact_recovery_commands() -> None:
    recovery_commands = artifact_recovery_commands(
        [
            "execution_snapshot_summary_path",
            "execution_venue_comparison_summary_path",
            "phase_gate_summary_path",
        ]
    )

    order = remediation_order(
        {
            "phase_gate_strict_validation_issue_count": "2",
            "execution_diagnostics_status": "degraded",
            "execution_drift_overview_status": "blocked",
            "readiness_execution_ready": False,
        },
        [
            "execution_snapshot_summary_path",
            "execution_venue_comparison_summary_path",
            "phase_gate_summary_path",
        ],
        recovery_commands,
    )

    assert order == [
        {
            "priority": 1,
            "reason": "missing_required_artifacts",
            "commands": [
                "uv run sis refresh-operations-artifacts",
                "uv run sis phase-gate-review",
            ],
        },
        {
            "priority": 2,
            "reason": "strict_validation_failed",
            "commands": ["uv run sis validate-artifacts --strict"],
        },
        {
            "priority": 3,
            "reason": "execution_diagnostics_degraded",
            "commands": ["uv run sis refresh-operations-artifacts"],
        },
        {
            "priority": 4,
            "reason": "execution_drift_unresolved",
            "commands": ["uv run sis refresh-operations-artifacts"],
        },
        {
            "priority": 5,
            "reason": "readiness_not_cleared",
            "commands": [
                "uv run sis refresh-operations-artifacts",
                "uv run sis phase-gate-review",
            ],
        },
    ]


def test_remediation_stage_commands_and_expected_outputs_are_reason_specific() -> None:
    assert remediation_success_criteria("strict_validation_failed") == [
        "phase_gate_strict_validation_issue_count == 0"
    ]
    assert remediation_preflight_commands("strict_validation_failed") == [
        "uv run sis validate-artifacts --strict"
    ]
    assert remediation_postcheck_commands("strict_validation_failed") == [
        "uv run sis phase-gate-review",
        "uv run sis paper-operations-runbook",
    ]
    assert remediation_preflight_expected_outputs("missing_required_artifacts") == [
        "implementation-status exits 0",
        f"{CODE_STATUS_DOC} is regenerated",
    ]
    assert remediation_execute_expected_outputs("execution_drift_unresolved") == [
        "execution_drift_overview_summary.json is regenerated",
        "drift mismatch counts are recalculated from fresh artifacts",
    ]
    assert remediation_postcheck_pass_signals("readiness_not_cleared") == [
        "readiness_execution_ready == True",
        "phase2_entry_allowed == True",
    ]
    assert remediation_preflight_commands("unknown_reason") == []


def test_remediation_signal_snapshots_capture_before_and_target_values() -> None:
    summary = {
        "execution_drift_overview_status": "blocked",
        "execution_state_comparison_mismatching_count": 3,
        "execution_snapshot_drift_mismatching_snapshot_count": 2,
        "readiness_execution_ready": False,
        "phase2_entry_allowed": False,
    }

    assert remediation_signal_snapshot_before("execution_drift_unresolved", summary) == {
        "execution_drift_overview_status": "blocked",
        "execution_state_comparison_mismatching_count": 3,
        "execution_snapshot_drift_mismatching_snapshot_count": 2,
    }
    assert remediation_signal_snapshot_target("execution_drift_unresolved") == {
        "execution_drift_overview_status": "ok",
        "execution_state_comparison_mismatching_count": 0,
        "execution_snapshot_drift_mismatching_snapshot_count": 0,
    }
    assert remediation_signal_snapshot_before("readiness_not_cleared", summary) == {
        "readiness_execution_ready": False,
        "phase2_entry_allowed": False,
    }
    assert remediation_signal_snapshot_target("unknown_reason") == {}
