from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import CODE_STATUS_DOC
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    compare_signal_snapshots,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    latest_execution_lineage_flat_lines,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    latest_execution_lineage_fields_from_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
    readiness_flat_fields,
    recommend_remediation_actions,
    signal_observed_sources_by_reason,
    signal_source_confidence,
)
from sis.storage.jsonl_store import write_json


def _report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    readiness_summary_path = (
        Path(summary["readiness_summary_path"])
        if isinstance(summary.get("readiness_summary_path"), str)
        else None
    )
    ops_dashboard_summary_path = (
        Path(summary["ops_dashboard_summary_path"])
        if isinstance(summary.get("ops_dashboard_summary_path"), str)
        else None
    )
    ordered_items = (
        (
            "paper_operations_runbook_report",
            summary.get("paper_operations_runbook_report_path"),
        ),
        (
            "readiness_snapshot_report",
            _report_path_for_summary(readiness_summary_path, "readiness_snapshot.md"),
        ),
        (
            "current_state_index_report",
            _report_path_for_summary(readiness_summary_path, "current_state_index.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "operations_dashboard_report",
            _report_path_for_summary(ops_dashboard_summary_path, "operations_dashboard.md"),
        ),
        (
            "ops_review_report",
            _report_path_for_summary(ops_dashboard_summary_path, "ops_review_report.md"),
        ),
        (
            "remediation_scoreboard_report",
            _report_path_for_summary(ops_dashboard_summary_path, "remediation_scoreboard.md"),
        ),
        (
            "remediation_session_checkpoint_report",
            _report_path_for_summary(
                ops_dashboard_summary_path,
                "remediation_session_checkpoint.md",
            ),
        ),
        (
            "remediation_session_report",
            _report_path_for_summary(ops_dashboard_summary_path, "remediation_session.md"),
        ),
        (
            "remediation_execution_plan_report",
            _report_path_for_summary(
                ops_dashboard_summary_path,
                "remediation_execution_plan.md",
            ),
        ),
        (
            "remediation_planner_report",
            _report_path_for_summary(ops_dashboard_summary_path, "remediation_planner.md"),
        ),
        ("live_evidence_report", summary.get("live_evidence_report_path")),
    )
    return {
        key: value
        for key, value in ordered_items
        if isinstance(value, str) and value
    }


def _quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    items = (
        (
            "paper_operations_runbook_report",
            summary.get("paper_operations_runbook_report_path"),
        ),
        ("readiness_snapshot_report", summary["related_reports"].get("readiness_snapshot_report")),
        ("current_state_index_report", summary["related_reports"].get("current_state_index_report")),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "remediation_scoreboard_report",
            summary["related_reports"].get("remediation_scoreboard_report"),
        ),
        ("live_evidence_report", summary.get("live_evidence_report_path")),
    )
    return {
        key: value
        for key, value in items
        if isinstance(value, str) and value
    }


def _required_artifact_paths(summary: dict[str, object]) -> dict[str, str | None]:
    artifact_keys = (
        "scheduled_run_path",
        "daemon_manifest_path",
        "monitoring_snapshot_path",
        "execution_snapshot_summary_path",
        "execution_venue_comparison_summary_path",
        "execution_venue_diagnostics_summary_path",
        "execution_gap_history_summary_path",
        "execution_state_comparison_history_summary_path",
        "execution_snapshot_drift_history_summary_path",
        "execution_drift_overview_summary_path",
        "readiness_summary_path",
        "phase_gate_summary_path",
        "ops_dashboard_summary_path",
    )
    return {
        key: summary.get(key) if isinstance(summary.get(key), str) else None
        for key in artifact_keys
    }


def _artifact_recovery_commands(artifact_names: list[str]) -> dict[str, list[str]]:
    command_map = {
        "scheduled_run_path": ["uv run sis schedule-run --run-type paper --when <ISO8601>"],
        "daemon_manifest_path": ["uv run sis daemon-manifest"],
        "monitoring_snapshot_path": ["uv run sis monitoring-status"],
        "execution_snapshot_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_venue_comparison_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_venue_diagnostics_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_gap_history_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_state_comparison_history_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_snapshot_drift_history_summary_path": ["uv run sis refresh-operations-artifacts"],
        "execution_drift_overview_summary_path": ["uv run sis refresh-operations-artifacts"],
        "readiness_summary_path": ["uv run sis refresh-operations-artifacts"],
        "phase_gate_summary_path": ["uv run sis phase-gate-review"],
        "ops_dashboard_summary_path": ["uv run sis refresh-operations-artifacts"],
    }
    return {
        name: command_map.get(name, ["uv run sis refresh-operations-artifacts"])
        for name in artifact_names
    }


def _remediation_order(
    summary: dict[str, object],
    missing_required_artifact_paths: list[str],
    artifact_recovery_commands: dict[str, list[str]],
) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    if missing_required_artifact_paths:
        commands: list[str] = []
        for name in missing_required_artifact_paths:
            commands.extend(artifact_recovery_commands.get(name, []))
        steps.append(
            {
                "priority": 1,
                "reason": "missing_required_artifacts",
                "commands": list(dict.fromkeys(commands)),
            }
        )
    if int(summary.get("phase_gate_strict_validation_issue_count") or 0) > 0:
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
                "commands": ["uv run sis refresh-operations-artifacts", "uv run sis phase-gate-review"],
            }
        )
    return steps


def _remediation_success_criteria(reason: str) -> list[str]:
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


def _remediation_preflight_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis implementation-status"],
        "strict_validation_failed": ["uv run sis validate-artifacts --strict"],
        "execution_diagnostics_degraded": ["uv run sis monitoring-status"],
        "execution_drift_unresolved": ["uv run sis monitoring-status"],
        "readiness_not_cleared": ["uv run sis phase-gate-review"],
    }
    return command_map.get(reason, [])


def _remediation_postcheck_commands(reason: str) -> list[str]:
    command_map = {
        "missing_required_artifacts": ["uv run sis paper-operations-runbook"],
        "strict_validation_failed": ["uv run sis phase-gate-review", "uv run sis paper-operations-runbook"],
        "execution_diagnostics_degraded": ["uv run sis paper-operations-runbook"],
        "execution_drift_unresolved": ["uv run sis paper-operations-runbook"],
        "readiness_not_cleared": ["uv run sis phase-gate-review", "uv run sis paper-operations-runbook"],
    }
    return command_map.get(reason, [])


def _remediation_preflight_expected_outputs(reason: str) -> list[str]:
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


def _remediation_execute_expected_outputs(reason: str) -> list[str]:
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


def _remediation_postcheck_pass_signals(reason: str) -> list[str]:
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


def _remediation_signal_snapshot_before(
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
            "execution_drift_overview_status": summary.get(
                "execution_drift_overview_status"
            ),
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


def _remediation_signal_snapshot_target(reason: str) -> dict[str, object]:
    snapshot_map = {
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
    remediation_planner_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    prior_summary = safe_read_json_dict(summary_path)
    scheduled_run = safe_read_json_dict(scheduled_run_path)
    daemon_manifest = safe_read_json_dict(daemon_manifest_path)
    monitoring = safe_read_json_dict(monitoring_snapshot_path)
    execution = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    readiness = normalized_summary(readiness_summary_path, normalize_readiness_summary)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    dashboard = safe_read_json_dict(ops_dashboard_summary_path)
    latest_execution_lineage = latest_execution_lineage_fields_from_summary(dashboard)
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
        "scheduled_run_path": str(scheduled_run_path) if scheduled_run_path is not None else None,
        "daemon_manifest_path": str(daemon_manifest_path) if daemon_manifest_path is not None else None,
        "monitoring_snapshot_path": str(monitoring_snapshot_path) if monitoring_snapshot_path is not None else None,
        "execution_snapshot_summary_path": (
            str(execution_snapshot_summary_path) if execution_snapshot_summary_path is not None else None
        ),
        "execution_venue_comparison_summary_path": (
            str(execution_venue_comparison_summary_path)
            if execution_venue_comparison_summary_path is not None
            else None
        ),
        "execution_venue_diagnostics_summary_path": (
            str(execution_venue_diagnostics_summary_path)
            if execution_venue_diagnostics_summary_path is not None
            else None
        ),
        "execution_gap_history_summary_path": (
            str(execution_gap_history_summary_path) if execution_gap_history_summary_path is not None else None
        ),
        "execution_state_comparison_history_summary_path": (
            str(execution_state_comparison_history_summary_path)
            if execution_state_comparison_history_summary_path is not None
            else None
        ),
        "execution_snapshot_drift_history_summary_path": (
            str(execution_snapshot_drift_history_summary_path)
            if execution_snapshot_drift_history_summary_path is not None
            else None
        ),
        "execution_drift_overview_summary_path": (
            str(execution_drift_overview_summary_path)
            if execution_drift_overview_summary_path is not None
            else None
        ),
        "readiness_summary_path": str(readiness_summary_path) if readiness_summary_path is not None else None,
        "phase_gate_summary_path": str(phase_gate_summary_path) if phase_gate_summary_path is not None else None,
        "ops_dashboard_summary_path": str(ops_dashboard_summary_path) if ops_dashboard_summary_path is not None else None,
        "daemon_mode": daemon_manifest.get("mode"),
        "monitoring_status": monitoring.get("status"),
        "phase_gate_summary": phase_gate,
        "readiness_summary": readiness,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        **latest_execution_lineage,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **readiness_fields,
        **phase_gate_fields,
        **{
            key: value
            for key, value in dashboard.items()
            if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
        },
        "dashboard_status": dashboard.get("overall_status"),
    }
    required_artifact_paths = _required_artifact_paths(summary)
    missing_required_artifact_paths = [
        key for key, value in required_artifact_paths.items() if not value
    ]
    artifact_recovery_commands = _artifact_recovery_commands(missing_required_artifact_paths)
    remediation_order = _remediation_order(
        summary,
        missing_required_artifact_paths,
        artifact_recovery_commands,
    )
    remediation_success_criteria = {
        item["reason"]: _remediation_success_criteria(str(item["reason"]))
        for item in remediation_order
    }
    remediation_preflight_commands = {
        item["reason"]: _remediation_preflight_commands(str(item["reason"]))
        for item in remediation_order
    }
    remediation_postcheck_commands = {
        item["reason"]: _remediation_postcheck_commands(str(item["reason"]))
        for item in remediation_order
    }
    remediation_preflight_expected_outputs = {
        item["reason"]: _remediation_preflight_expected_outputs(str(item["reason"]))
        for item in remediation_order
    }
    remediation_execute_expected_outputs = {
        item["reason"]: _remediation_execute_expected_outputs(str(item["reason"]))
        for item in remediation_order
    }
    remediation_postcheck_pass_signals = {
        item["reason"]: _remediation_postcheck_pass_signals(str(item["reason"]))
        for item in remediation_order
    }
    remediation_signal_snapshots_before = {
        item["reason"]: _remediation_signal_snapshot_before(str(item["reason"]), summary)
        for item in remediation_order
    }
    remediation_signal_snapshots_target = {
        item["reason"]: _remediation_signal_snapshot_target(str(item["reason"]))
        for item in remediation_order
    }
    previous_signal_snapshots = (
        prior_summary.get("remediation_signal_snapshots_before")
        if isinstance(prior_summary.get("remediation_signal_snapshots_before"), dict)
        else {}
    )
    remediation_signal_snapshot_diffs = {
        item["reason"]: compare_signal_snapshots(
            previous_signal_snapshots.get(str(item["reason"])),
            remediation_signal_snapshots_before.get(str(item["reason"])),
            remediation_signal_snapshots_target.get(str(item["reason"])),
        )
        for item in remediation_order
    }
    previous_recommendations = (
        prior_summary.get("remediation_recommendations")
        if isinstance(prior_summary.get("remediation_recommendations"), dict)
        else {}
    )
    current_planner_summary = safe_read_json_dict(remediation_planner_summary_path)
    current_evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    current_provenance_hints = {
        str(item.get("reason")): item
        for item in current_planner_summary.get("entries", [])
        if isinstance(item, dict)
        and item.get("source") == "paper_operations_runbook"
        and item.get("reason")
    }
    current_signal_provenance_hints = signal_observed_sources_by_reason(
        current_evaluator_summary,
        source="paper_operations_runbook",
    )
    remediation_recommendations = {
        str(item["reason"]): recommend_remediation_actions(
            remediation_signal_snapshot_diffs.get(str(item["reason"])),
            preflight_commands=remediation_preflight_commands.get(str(item["reason"]), []),
            execute_commands=item["commands"],
            postcheck_commands=remediation_postcheck_commands.get(str(item["reason"]), []),
            source_confidence=(
                current_provenance_hints.get(str(item["reason"]), {}).get("source_confidence")
                if isinstance(current_provenance_hints.get(str(item["reason"])), dict)
                else (
                    previous_recommendations.get(str(item["reason"]), {}).get("source_confidence")
                    if isinstance(previous_recommendations.get(str(item["reason"])), dict)
                    else None
                )
            ),
            source_policy=(
                current_provenance_hints.get(str(item["reason"]), {}).get("source_policy")
                if isinstance(current_provenance_hints.get(str(item["reason"])), dict)
                else (
                    previous_recommendations.get(str(item["reason"]), {}).get("source_policy")
                    if isinstance(previous_recommendations.get(str(item["reason"])), dict)
                    else None
                )
            ),
            execute_signal_confidence=signal_source_confidence(
                current_signal_provenance_hints.get(str(item["reason"])),
                remediation_execute_expected_outputs.get(str(item["reason"]), []),
            ),
            postcheck_signal_confidence=signal_source_confidence(
                current_signal_provenance_hints.get(str(item["reason"])),
                remediation_postcheck_pass_signals.get(str(item["reason"]), []),
            ),
        )
        for item in remediation_order
    }
    summary["remediation_planner_summary_path"] = (
        str(remediation_planner_summary_path) if remediation_planner_summary_path is not None else None
    )
    summary["remediation_evaluator_summary_path"] = (
        str(remediation_evaluator_summary_path) if remediation_evaluator_summary_path is not None else None
    )
    summary["required_artifact_paths"] = required_artifact_paths
    summary["missing_required_artifact_paths"] = missing_required_artifact_paths
    summary["artifact_recovery_commands"] = artifact_recovery_commands
    summary["remediation_order"] = remediation_order
    summary["remediation_success_criteria"] = remediation_success_criteria
    summary["remediation_preflight_commands"] = remediation_preflight_commands
    summary["remediation_postcheck_commands"] = remediation_postcheck_commands
    summary["remediation_preflight_expected_outputs"] = remediation_preflight_expected_outputs
    summary["remediation_execute_expected_outputs"] = remediation_execute_expected_outputs
    summary["remediation_postcheck_pass_signals"] = remediation_postcheck_pass_signals
    summary["remediation_signal_snapshots_before"] = remediation_signal_snapshots_before
    summary["remediation_signal_snapshots_target"] = remediation_signal_snapshots_target
    summary["remediation_signal_snapshots_previous"] = previous_signal_snapshots
    summary["remediation_signal_snapshot_diffs"] = remediation_signal_snapshot_diffs
    summary["remediation_recommendations"] = remediation_recommendations
    summary["paper_operations_runbook_report_path"] = str(out_path) if out_path is not None else None
    summary["live_evidence_report_path"] = readiness.get("live_evidence_report_path")
    summary["related_reports"] = _related_reports(summary)
    summary["quick_navigation"] = _quick_navigation(summary)

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
        f"- daemon_manifest_path: {summary['daemon_manifest_path']}",
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
        "## Current Remediation Queue",
        "",
        f"- timeline_latest_remediation_planner_status: {summary.get('timeline_latest_remediation_planner_status')}",
        f"- timeline_latest_remediation_planner_next_best_command: {summary.get('timeline_latest_remediation_planner_next_best_command')}",
        (
            "- timeline_latest_remediation_planner_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_planner_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_execution_plan_status: {summary.get('timeline_latest_remediation_execution_plan_status')}",
        f"- timeline_latest_remediation_execution_plan_next_action_command: {summary.get('timeline_latest_remediation_execution_plan_next_action_command')}",
        (
            "- timeline_latest_remediation_execution_plan_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_session_status: {summary.get('timeline_latest_remediation_session_status')}",
        f"- timeline_latest_remediation_session_next_pending_command: {summary.get('timeline_latest_remediation_session_next_pending_command')}",
        (
            "- timeline_latest_remediation_session_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_session_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_checkpoint_status: {summary.get('timeline_latest_remediation_checkpoint_status')}",
        f"- timeline_latest_remediation_checkpoint_next_action_command: {summary.get('timeline_latest_remediation_checkpoint_next_action_command')}",
        (
            "- timeline_latest_remediation_checkpoint_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}"
        ),
        f"- timeline_latest_remediation_scoreboard_status: {summary.get('timeline_latest_remediation_scoreboard_status')}",
        f"- timeline_latest_remediation_scoreboard_next_action_command: {summary.get('timeline_latest_remediation_scoreboard_next_action_command')}",
        (
            "- timeline_latest_remediation_scoreboard_feedback_priority_reason: "
            f"{summary.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}"
        ),
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in summary["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
        "## Related Reports",
        "",
    ]
    )
    for key, value in summary["related_reports"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
        "## Strict Validation Preview",
        "",
        ]
    )
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(
        [
            "",
            "## Required Artifacts",
            "",
            *[f"- {name}: {value}" for name, value in required_artifact_paths.items()],
            (
                "- missing_required_artifact_paths: none"
                if not missing_required_artifact_paths
                else "- missing_required_artifact_paths:"
            ),
            *[f"  - {name}" for name in missing_required_artifact_paths],
            "",
            "## Recovery Commands",
            "",
        ]
    )
    if artifact_recovery_commands:
        for name, commands in artifact_recovery_commands.items():
            lines.append(f"- {name}:")
            lines.extend(f"  - `{command}`" for command in commands)
    else:
        lines.append("- recovery_commands: none")
    lines.extend(["", "## Remediation Order", ""])
    if remediation_order:
        for item in remediation_order:
            lines.append(f"- priority_{item['priority']}: {item['reason']}")
            lines.extend(f"  - `{command}`" for command in item["commands"])
    else:
        lines.append("- remediation_order: none")
    lines.extend(["", "## Remediation Success Criteria", ""])
    if remediation_success_criteria:
        for reason, criteria in remediation_success_criteria.items():
            lines.append(f"- {reason}:")
            lines.extend(f"  - {criterion}" for criterion in criteria)
    else:
        lines.append("- remediation_success_criteria: none")
    lines.extend(["", "## Remediation Command Flow", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight:")
            for command in remediation_preflight_commands.get(reason, []):
                lines.append(f"    - `{command}`")
            lines.append("  - execute:")
            for command in item["commands"]:
                lines.append(f"    - `{command}`")
            lines.append("  - post_check:")
            for command in remediation_postcheck_commands.get(reason, []):
                lines.append(f"    - `{command}`")
    else:
        lines.append("- remediation_command_flow: none")
    lines.extend(["", "## Remediation Verification Signals", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight_expected_output:")
            for value in remediation_preflight_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - execute_expected_output:")
            for value in remediation_execute_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - postcheck_pass_signal:")
            for value in remediation_postcheck_pass_signals.get(reason, []):
                lines.append(f"    - {value}")
    else:
        lines.append("- remediation_verification_signals: none")
    lines.extend(["", "## Remediation Signal Snapshots", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - before:")
            for key, value in remediation_signal_snapshots_before.get(reason, {}).items():
                lines.append(f"    - {key}: {value}")
            lines.append("  - target:")
            for key, value in remediation_signal_snapshots_target.get(reason, {}).items():
                lines.append(f"    - {key}: {value}")
    else:
        lines.append("- remediation_signal_snapshots: none")
    lines.extend(["", "## Remediation Signal Diffs", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            for key, diff in remediation_signal_snapshot_diffs.get(reason, {}).items():
                lines.append(
                    "  - {key}: previous={previous} current={current} target={target} trend={trend} target_matched={target_matched}".format(
                        key=key,
                        previous=diff.get("previous"),
                        current=diff.get("current"),
                        target=diff.get("target"),
                        trend=diff.get("trend"),
                        target_matched=diff.get("target_matched"),
                    )
                )
    else:
        lines.append("- remediation_signal_diffs: none")
    lines.extend(["", "## Remediation Recommendations", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            recommendation = remediation_recommendations.get(reason, {})
            lines.append(f"- {reason}:")
            lines.append(f"  - status: {recommendation.get('status')}")
            lines.append(f"  - why: {recommendation.get('why')}")
            for command in recommendation.get("commands", []):
                lines.append(f"  - next: `{command}`")
    else:
        lines.append("- remediation_recommendations: none")
    lines.extend(
        [
            "",
            "## Latest Execution Lineage",
            "",
            *latest_execution_lineage_flat_lines(summary),
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
        "9. Review `data/reports/remediation_scoreboard.md` for the current retry queue and blocker status.",
        "10. Review `data/reports/remediation_session_checkpoint.md` for the next action checkpoint.",
        "11. Review `data/reports/remediation_session.md` for the pending command queue.",
        "12. Review `data/reports/remediation_execution_plan.md` for staged command ordering.",
        "13. Review `data/reports/remediation_planner.md` for the current next-best command.",
        "14. Review `data/reports/operations_dashboard.md` for overall status.",
        "15. Review `data/reports/ops_review_report.md` for latest operation chain details.",
        "16. If status is acceptable, run `uv run sis paper-step` or the scheduled paper command.",
        "17. Re-run `uv run sis refresh-operations-artifacts` after the paper step.",
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
        "- If `missing_required_artifact_paths` is not empty, regenerate the missing artifacts before continuing.",
        "- If `missing_required_artifact_paths` is not empty, run the mapped commands in `Recovery Commands` before continuing.",
        "- Execute the commands in `Remediation Order` from lower priority number to higher before retrying paper operations.",
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
