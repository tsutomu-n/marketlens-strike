from __future__ import annotations

from typing import TypedDict

from sis.reports.doc_paths import CODE_STATUS_DOC


class RemediationStep(TypedDict):
    priority: int
    reason: str
    commands: list[str]


def as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def artifact_recovery_commands(artifact_names: list[str]) -> dict[str, list[str]]:
    command_map = {
        "scheduled_run_path": ["uv run sis schedule-run --run-type paper --when <ISO8601>"],
        "daemon_manifest_path": ["uv run sis daemon-manifest"],
        "monitoring_snapshot_path": ["uv run sis monitoring-status"],
        "execution_snapshot_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_venue_comparison_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_venue_diagnostics_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_gap_history_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_state_comparison_history_summary_path": [
            "uv run sis refresh-operations-artifacts"
        ],
        "execution_snapshot_drift_history_summary_path": [
            "uv run sis refresh-operations-artifacts"
        ],
        "execution_drift_overview_summary_path": ["uv run sis refresh-operations-artifacts"],
        "readiness_summary_path": ["uv run sis refresh-operations-artifacts"],
        "phase_gate_summary_path": ["uv run sis phase-gate-review"],
        "ops_dashboard_summary_path": ["uv run sis refresh-operations-artifacts"],
    }
    return {
        name: command_map.get(name, ["uv run sis refresh-operations-artifacts"])
        for name in artifact_names
    }


def remediation_order(
    summary: dict[str, object],
    missing_required_artifact_paths: list[str],
    recovery_commands: dict[str, list[str]],
) -> list[RemediationStep]:
    steps: list[RemediationStep] = []
    if missing_required_artifact_paths:
        commands: list[str] = []
        for name in missing_required_artifact_paths:
            commands.extend(recovery_commands.get(name, []))
        steps.append(
            {
                "priority": 1,
                "reason": "missing_required_artifacts",
                "commands": list(dict.fromkeys(commands)),
            }
        )
    phase_gate_strict_validation_issue_count = (
        as_int(summary.get("phase_gate_strict_validation_issue_count")) or 0
    )
    if phase_gate_strict_validation_issue_count > 0:
        steps.append(
            {
                "priority": 2,
                "reason": "strict_validation_failed",
                "commands": ["uv run sis validate-artifacts --strict"],
            }
        )
    if summary.get("execution_diagnostics_status") != "ok":
        steps.append(
            {
                "priority": 3,
                "reason": "execution_diagnostics_degraded",
                "commands": ["uv run sis refresh-operations-artifacts"],
            }
        )
    if summary.get("execution_drift_overview_status") != "ok":
        steps.append(
            {
                "priority": 4,
                "reason": "execution_drift_unresolved",
                "commands": ["uv run sis refresh-operations-artifacts"],
            }
        )
    if summary.get("readiness_execution_ready") is not True:
        steps.append(
            {
                "priority": 5,
                "reason": "readiness_not_cleared",
                "commands": [
                    "uv run sis refresh-operations-artifacts",
                    "uv run sis phase-gate-review",
                ],
            }
        )
    return steps


def remediation_success_criteria(reason: str) -> list[str]:
    criteria_map = {
        "missing_required_artifacts": [
            "missing_required_artifact_paths is empty",
            "required artifact paths are non-null",
        ],
        "strict_validation_failed": [
            "phase_gate_strict_validation_issue_count == 0",
        ],
        "execution_diagnostics_degraded": [
            "execution_diagnostics_status == ok",
            "execution_balance_gap_detected == False",
            "execution_fills_gap_detected == False",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_status == ok",
            "execution_state_comparison_mismatching_count == 0",
            "execution_snapshot_drift_mismatching_snapshot_count == 0",
        ],
        "readiness_not_cleared": [
            "readiness_execution_ready == True",
            "phase2_entry_allowed == True",
        ],
    }
    return criteria_map.get(reason, [])


def remediation_preflight_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis implementation-status"],
        "strict_validation_failed": ["uv run sis validate-artifacts --strict"],
        "execution_diagnostics_degraded": ["uv run sis monitoring-status"],
        "execution_drift_unresolved": ["uv run sis monitoring-status"],
        "readiness_not_cleared": ["uv run sis phase-gate-review"],
    }
    return command_map.get(reason, [])


def remediation_postcheck_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis paper-operations-runbook"],
        "strict_validation_failed": [
            "uv run sis phase-gate-review",
            "uv run sis paper-operations-runbook",
        ],
        "execution_diagnostics_degraded": ["uv run sis paper-operations-runbook"],
        "execution_drift_unresolved": ["uv run sis paper-operations-runbook"],
        "readiness_not_cleared": [
            "uv run sis phase-gate-review",
            "uv run sis paper-operations-runbook",
        ],
    }
    return command_map.get(reason, [])


def remediation_preflight_expected_outputs(reason: str) -> list[str]:
    output_map = {
        "missing_required_artifacts": [
            "implementation-status exits 0",
            f"{CODE_STATUS_DOC} is regenerated",
        ],
        "strict_validation_failed": [
            "validate-artifacts --strict reports the current issue count",
            "strict validation output includes checked_files",
            "strict validation preview lists current issues",
        ],
        "execution_diagnostics_degraded": [
            "monitoring-status prints execution_diagnostics_status",
            "monitoring output shows current balance/fills gap flags",
        ],
        "execution_drift_unresolved": [
            "monitoring-status prints execution_drift_overview_status",
            "monitoring output shows current mismatch counts",
        ],
        "readiness_not_cleared": [
            "phase-gate-review prints phase2_entry_allowed",
            "phase gate output shows current readiness blockers",
        ],
    }
    return output_map.get(reason, [])


def remediation_execute_expected_outputs(reason: str) -> list[str]:
    output_map = {
        "missing_required_artifacts": [
            "mapped recovery commands exit 0",
            "missing required artifact paths shrink or become empty",
        ],
        "strict_validation_failed": [
            "strict validation output reports issues=0",
            "phase gate summary can be regenerated cleanly",
        ],
        "execution_diagnostics_degraded": [
            "execution_venue_diagnostics_summary.json is regenerated",
            "execution diagnostics status is re-evaluated from fresh artifacts",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_summary.json is regenerated",
            "drift mismatch counts are recalculated from fresh artifacts",
        ],
        "readiness_not_cleared": [
            "refresh-operations-artifacts and phase-gate-review exit 0",
            "readiness and phase gate summaries are refreshed",
        ],
    }
    return output_map.get(reason, [])


def remediation_postcheck_pass_signals(reason: str) -> list[str]:
    signal_map = {
        "missing_required_artifacts": [
            "missing_required_artifact_paths is empty",
            "required artifact paths are non-null",
        ],
        "strict_validation_failed": [
            "phase_gate_strict_validation_issue_count == 0",
        ],
        "execution_diagnostics_degraded": [
            "execution_diagnostics_status == ok",
            "execution_balance_gap_detected == False",
            "execution_fills_gap_detected == False",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_status == ok",
            "execution_state_comparison_mismatching_count == 0",
            "execution_snapshot_drift_mismatching_snapshot_count == 0",
        ],
        "readiness_not_cleared": [
            "readiness_execution_ready == True",
            "phase2_entry_allowed == True",
        ],
    }
    return signal_map.get(reason, [])


def remediation_signal_snapshot_before(
    reason: str, summary: dict[str, object]
) -> dict[str, object]:
    snapshot_map = {
        "missing_required_artifacts": {
            "missing_required_artifact_paths": summary.get("missing_required_artifact_paths"),
            "scheduled_run_path": summary.get("scheduled_run_path"),
            "phase_gate_summary_path": summary.get("phase_gate_summary_path"),
        },
        "strict_validation_failed": {
            "phase_gate_strict_validation_issue_count": summary.get(
                "phase_gate_strict_validation_issue_count"
            ),
            "phase_gate_checked_files": summary.get("phase_gate_checked_files"),
        },
        "execution_diagnostics_degraded": {
            "execution_diagnostics_status": summary.get("execution_diagnostics_status"),
            "execution_balance_gap_detected": summary.get("execution_balance_gap_detected"),
            "execution_fills_gap_detected": summary.get("execution_fills_gap_detected"),
        },
        "execution_drift_unresolved": {
            "execution_drift_overview_status": summary.get("execution_drift_overview_status"),
            "execution_state_comparison_mismatching_count": summary.get(
                "execution_state_comparison_mismatching_count"
            ),
            "execution_snapshot_drift_mismatching_snapshot_count": summary.get(
                "execution_snapshot_drift_mismatching_snapshot_count"
            ),
        },
        "readiness_not_cleared": {
            "readiness_execution_ready": summary.get("readiness_execution_ready"),
            "phase2_entry_allowed": summary.get("phase2_entry_allowed"),
        },
    }
    return snapshot_map.get(reason, {})


def remediation_signal_snapshot_target(reason: str) -> dict[str, object]:
    snapshot_map: dict[str, dict[str, object]] = {
        "missing_required_artifacts": {
            "missing_required_artifact_paths": [],
            "required_artifact_paths_non_null": True,
        },
        "strict_validation_failed": {
            "phase_gate_strict_validation_issue_count": 0,
        },
        "execution_diagnostics_degraded": {
            "execution_diagnostics_status": "ok",
            "execution_balance_gap_detected": False,
            "execution_fills_gap_detected": False,
        },
        "execution_drift_unresolved": {
            "execution_drift_overview_status": "ok",
            "execution_state_comparison_mismatching_count": 0,
            "execution_snapshot_drift_mismatching_snapshot_count": 0,
        },
        "readiness_not_cleared": {
            "readiness_execution_ready": True,
            "phase2_entry_allowed": True,
        },
    }
    return snapshot_map.get(reason, {})
