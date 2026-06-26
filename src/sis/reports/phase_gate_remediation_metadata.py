from __future__ import annotations

from sis.reports.doc_paths import CODE_STATUS_DOC


def remediation_success_criteria(reason: str) -> list[str]:
    criteria_map = {
        "missing_required_artifacts": [
            "missing_required_artifact_paths is empty",
            "required artifact paths are non-null",
        ],
        "strict_validation_failed": [
            "strict_validation_issue_count == 0",
            "phase_gate_strict_validation_issue_count == 0",
        ],
        "diagnostics_unavailable": [
            "diagnostics_all_available == True",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_status == ok",
            "execution_drift_overview_diagnostics_alignment_match == True",
        ],
        "phase_gate_not_cleared": [
            "phase2_entry_allowed == True",
            "decision in {GO, CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST}",
        ],
    }
    return criteria_map.get(reason, [])


def remediation_preflight_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis implementation-status"],
        "strict_validation_failed": ["uv run sis validate-artifacts --strict"],
        "diagnostics_unavailable": ["uv run sis diagnose-quotes"],
        "execution_drift_unresolved": ["uv run sis refresh-operations-artifacts"],
        "phase_gate_not_cleared": ["uv run sis check-go-no-go"],
    }
    return command_map.get(reason, [])


def remediation_postcheck_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis phase-gate-review"],
        "strict_validation_failed": ["uv run sis phase-gate-review"],
        "diagnostics_unavailable": ["uv run sis phase-gate-review"],
        "execution_drift_unresolved": ["uv run sis phase-gate-review"],
        "phase_gate_not_cleared": [
            "uv run sis build-evidence-card",
            "uv run sis phase-gate-review",
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
        "diagnostics_unavailable": [
            "diagnose-quotes prints per-symbol diagnostics rows",
            "required symbols show quote diagnostics coverage",
        ],
        "execution_drift_unresolved": [
            "refresh-operations-artifacts regenerates execution summaries",
            "execution drift overview summary is rewritten",
        ],
        "phase_gate_not_cleared": [
            "check-go-no-go prints the current decision and blockers",
            "current gate decision is visible before regeneration",
            "phase gate summary lists blockers",
            "phase gate summary lists next actions",
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
            "strict validation output reports checked_files >= 1",
        ],
        "diagnostics_unavailable": [
            "diagnostics report is regenerated",
            "required quote diagnostics artifacts are available",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_summary.json is regenerated",
            "drift status is re-evaluated from fresh artifacts",
        ],
        "phase_gate_not_cleared": [
            "evidence card is regenerated",
            "go/no-go decision artifacts are refreshed",
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
            "strict_validation_issue_count == 0",
            "phase_gate_strict_validation_issue_count == 0",
        ],
        "diagnostics_unavailable": [
            "diagnostics_all_available == True",
        ],
        "execution_drift_unresolved": [
            "execution_drift_overview_status == ok",
            "execution_drift_overview_diagnostics_alignment_match == True",
        ],
        "phase_gate_not_cleared": [
            "phase2_entry_allowed == True",
            "decision in {GO, CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST}",
        ],
    }
    return signal_map.get(reason, [])


def remediation_signal_snapshot_before(
    reason: str, summary: dict[str, object]
) -> dict[str, object]:
    snapshot_map = {
        "missing_required_artifacts": {
            "missing_required_artifact_paths": summary.get("missing_required_artifact_paths"),
            "latest_manifest_path": summary.get("latest_manifest_path"),
            "latest_evidence_card_path": summary.get("latest_evidence_card_path"),
        },
        "strict_validation_failed": {
            "strict_validation_issue_count": summary.get("strict_validation_issue_count"),
            "phase_gate_strict_validation_issue_count": summary.get(
                "phase_gate_strict_validation_issue_count"
            ),
        },
        "diagnostics_unavailable": {
            "diagnostics_all_available": summary.get("diagnostics_all_available"),
            "diagnostics_symbols": summary.get("diagnostics_symbols"),
        },
        "execution_drift_unresolved": {
            "execution_drift_overview_status": summary.get("execution_drift_overview_status"),
            "execution_drift_overview_diagnostics_alignment_match": summary.get(
                "execution_drift_overview_diagnostics_alignment_match"
            ),
        },
        "phase_gate_not_cleared": {
            "phase2_entry_allowed": summary.get("phase2_entry_allowed"),
            "decision": summary.get("decision"),
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
            "strict_validation_issue_count": 0,
            "phase_gate_strict_validation_issue_count": 0,
        },
        "diagnostics_unavailable": {
            "diagnostics_all_available": True,
        },
        "execution_drift_unresolved": {
            "execution_drift_overview_status": "ok",
            "execution_drift_overview_diagnostics_alignment_match": True,
        },
        "phase_gate_not_cleared": {
            "phase2_entry_allowed": True,
            "decision": ["GO", "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST"],
        },
    }
    return snapshot_map.get(reason, {})
