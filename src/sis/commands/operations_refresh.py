from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

import typer
from loguru import logger

from sis.settings import get_settings
from sis.storage.jsonl_store import read_json


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    return cast(dict[str, Any], payload) if isinstance(payload, dict) else {}


def register_operations_refresh_commands(
    app: typer.Typer,
    *,
    _write_daemon_manifest_artifacts: Callable[..., Any],
    _write_state_export_artifacts: Callable[..., Any],
    _write_state_restore_artifacts: Callable[..., Any],
    _refresh_execution_lineage_artifacts: Callable[..., Any],
    _write_execution_read_only_surfaces: Callable[..., Any],
    _write_weekly_review: Callable[..., Any],
    _write_comparison_report: Callable[..., Any],
    _write_lifecycle_report: Callable[..., Any],
    _write_monitoring_snapshot: Callable[..., Any],
    _write_ops_review: Callable[..., Any],
    _write_operations_dashboard: Callable[..., Any],
    _write_paper_operations_runbook: Callable[..., Any],
    _write_paper_cycle_history: Callable[..., Any],
    _write_phase_gate_review: Callable[..., Any],
    _write_remediation_planner: Callable[..., Any],
    _write_remediation_execution_plan: Callable[..., Any],
    _write_remediation_session: Callable[..., Any],
    _write_remediation_session_checkpoint: Callable[..., Any],
    _write_remediation_evaluator: Callable[..., Any],
    _write_remediation_command_results: Callable[..., Any],
    _write_remediation_scoreboard: Callable[..., Any],
    _write_remediation_evidence: Callable[..., Any],
    _write_operations_bundle: Callable[..., Any],
    _write_operations_timeline: Callable[..., Any],
    _write_operations_audit_pack: Callable[..., Any],
    _write_audit_timeline: Callable[..., Any],
    _write_audit_dashboard: Callable[..., Any],
    _write_audit_bundle: Callable[..., Any],
    _append_operations_snapshot_manifest: Callable[..., Any],
    _append_operations_audit_snapshot_manifest: Callable[..., Any],
    _append_audit_bundle_snapshot_manifest: Callable[..., Any],
    _append_remediation_planner_manifest: Callable[..., Any],
    _append_remediation_execution_plan_manifest: Callable[..., Any],
    _append_remediation_session_manifest: Callable[..., Any],
    _append_remediation_session_checkpoint_manifest: Callable[..., Any],
    _append_remediation_scoreboard_manifest: Callable[..., Any],
    _append_remediation_evaluator_manifest: Callable[..., Any],
    _append_remediation_evidence_manifest: Callable[..., Any],
    _append_remediation_command_results_manifest: Callable[..., Any],
    _write_execution_gap_history: Callable[..., Any],
    _write_audit_bundle_history: Callable[..., Any],
    _write_current_state_index: Callable[..., Any],
    _write_readiness_snapshot: Callable[..., Any],
    _recommended_read_order: Callable[..., Any],
) -> None:
    @app.command("refresh-operations-artifacts")
    def refresh_operations_artifacts_cmd(
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
    ) -> None:
        settings = get_settings()
        daemon_manifest_artifacts = _write_daemon_manifest_artifacts(settings.data_dir)
        state_export_artifacts = _write_state_export_artifacts(settings.data_dir)
        state_restore_artifacts = _write_state_restore_artifacts(
            settings.data_dir,
            snapshot_path=settings.data_dir / "state/state_snapshot.json",
            restored=False,
        )
        execution_lineage = _refresh_execution_lineage_artifacts(settings.data_dir)
        (
            execution_read_only_surfaces_out,
            execution_read_only_surfaces_summary_out,
            _execution_read_only_surfaces_text,
        ) = _write_execution_read_only_surfaces(
            settings.data_dir,
            state_path=state_path,
        )
        execution_snapshot_out, execution_snapshot_summary_out, _execution_snapshot_text = (
            execution_lineage["execution_snapshot"]
        )
        execution_comparison_out, execution_comparison_summary_out, _execution_comparison_text = (
            execution_lineage["execution_comparison"]
        )
        (
            execution_diagnostics_out,
            execution_diagnostics_summary_out,
            _execution_diagnostics_text,
        ) = execution_lineage["execution_diagnostics"]
        weekly_out, _weekly_text = _write_weekly_review(settings.data_dir)
        comparison_out, _comparison_text = _write_comparison_report(settings.data_dir)
        lifecycle_out, _lifecycle_text = _write_lifecycle_report(settings.data_dir)
        monitoring_out, monitoring = _write_monitoring_snapshot(settings.data_dir, state_path)
        ops_review_out, ops_review_summary_out, _ops_review_text = _write_ops_review(
            settings.data_dir
        )
        dashboard_out, dashboard_summary_out, dashboard_text = _write_operations_dashboard(
            settings.data_dir
        )
        runbook_out, runbook_summary_out, _runbook_text = _write_paper_operations_runbook(
            settings.data_dir
        )
        cycle_history_out, cycle_history_summary_out, _cycle_history_text = (
            _write_paper_cycle_history(settings.data_dir)
        )
        gap_history_out, gap_history_summary_out, _gap_history_text = execution_lineage[
            "execution_gap_history"
        ]
        state_comparison_out, state_comparison_summary_out, _state_comparison_text = (
            execution_lineage["execution_state_comparison_history"]
        )
        snapshot_drift_out, snapshot_drift_summary_out, _snapshot_drift_text = execution_lineage[
            "execution_snapshot_drift_history"
        ]
        drift_overview_out, drift_overview_summary_out, _drift_overview_text = execution_lineage[
            "execution_drift_overview"
        ]
        phase_gate_out, phase_gate_summary_out, _phase_gate_text = _write_phase_gate_review(
            settings.data_dir
        )
        remediation_planner_out, remediation_planner_summary_out, _remediation_planner_text = (
            _write_remediation_planner(settings.data_dir)
        )
        (
            remediation_execution_plan_out,
            remediation_execution_plan_summary_out,
            _remediation_execution_plan_text,
        ) = _write_remediation_execution_plan(settings.data_dir)
        remediation_session_out, remediation_session_summary_out, _remediation_session_text = (
            _write_remediation_session(settings.data_dir)
        )
        (
            remediation_session_checkpoint_out,
            remediation_session_checkpoint_summary_out,
            _remediation_session_checkpoint_text,
        ) = _write_remediation_session_checkpoint(settings.data_dir)
        (
            remediation_evaluator_out,
            remediation_evaluator_summary_out,
            _remediation_evaluator_text,
        ) = _write_remediation_evaluator(settings.data_dir)
        (
            remediation_command_results_out,
            remediation_command_results_summary_out,
            _remediation_command_results_text,
        ) = _write_remediation_command_results(settings.data_dir)
        (
            remediation_scoreboard_out,
            remediation_scoreboard_summary_out,
            _remediation_scoreboard_text,
        ) = _write_remediation_scoreboard(settings.data_dir)
        remediation_evidence_out, remediation_evidence_summary_out, _remediation_evidence_text = (
            _write_remediation_evidence(settings.data_dir)
        )
        runbook_out, runbook_summary_out, _runbook_text = _write_paper_operations_runbook(
            settings.data_dir
        )
        phase_gate_out, phase_gate_summary_out, _phase_gate_text = _write_phase_gate_review(
            settings.data_dir
        )
        remediation_planner_out, remediation_planner_summary_out, _remediation_planner_text = (
            _write_remediation_planner(settings.data_dir)
        )
        (
            remediation_execution_plan_out,
            remediation_execution_plan_summary_out,
            _remediation_execution_plan_text,
        ) = _write_remediation_execution_plan(settings.data_dir)
        remediation_session_out, remediation_session_summary_out, _remediation_session_text = (
            _write_remediation_session(settings.data_dir)
        )
        (
            remediation_session_checkpoint_out,
            remediation_session_checkpoint_summary_out,
            _remediation_session_checkpoint_text,
        ) = _write_remediation_session_checkpoint(settings.data_dir)
        (
            remediation_evaluator_out,
            remediation_evaluator_summary_out,
            _remediation_evaluator_text,
        ) = _write_remediation_evaluator(settings.data_dir)
        (
            remediation_command_results_out,
            remediation_command_results_summary_out,
            _remediation_command_results_text,
        ) = _write_remediation_command_results(settings.data_dir)
        (
            remediation_scoreboard_out,
            remediation_scoreboard_summary_out,
            _remediation_scoreboard_text,
        ) = _write_remediation_scoreboard(settings.data_dir)
        remediation_evidence_out, remediation_evidence_summary_out, _remediation_evidence_text = (
            _write_remediation_evidence(settings.data_dir)
        )
        bundle_out, bundle_manifest_out, _bundle_text = _write_operations_bundle(settings.data_dir)
        timeline_out, timeline_summary_out, _timeline_text = _write_operations_timeline(
            settings.data_dir
        )
        audit_out, audit_manifest_out, _audit_text = _write_operations_audit_pack(settings.data_dir)
        audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = (
            _write_audit_timeline(settings.data_dir)
        )
        audit_dashboard_out, audit_dashboard_summary_out, _audit_dashboard_text = (
            _write_audit_dashboard(settings.data_dir)
        )
        audit_bundle_out, audit_bundle_manifest_out, _audit_bundle_text = _write_audit_bundle(
            settings.data_dir
        )
        bundle_payload = _read_json_dict(bundle_manifest_out)
        bundle_chain_out = _append_operations_snapshot_manifest(
            settings.data_dir,
            manifest_path=bundle_manifest_out,
            overall_status=bundle_payload.get("overall_status")
            if isinstance(bundle_payload, dict)
            else None,
            cycle_count=bundle_payload.get("cycle_count")
            if isinstance(bundle_payload, dict)
            else None,
        )
        audit_payload = _read_json_dict(audit_manifest_out)
        audit_chain_out = _append_operations_audit_snapshot_manifest(
            settings.data_dir,
            manifest_path=audit_manifest_out,
            overall_status=audit_payload.get("overall_status")
            if isinstance(audit_payload, dict)
            else None,
            timeline_latest_operation=audit_payload.get("timeline_latest_operation")
            if isinstance(audit_payload, dict)
            else None,
        )
        audit_bundle_payload = _read_json_dict(audit_bundle_manifest_out)
        audit_bundle_chain_out = _append_audit_bundle_snapshot_manifest(
            settings.data_dir,
            manifest_path=audit_bundle_manifest_out,
            overall_status=audit_bundle_payload.get("overall_status")
            if isinstance(audit_bundle_payload, dict)
            else None,
            timeline_latest_operation=audit_bundle_payload.get("timeline_latest_operation")
            if isinstance(audit_bundle_payload, dict)
            else None,
        )
        remediation_planner_payload = _read_json_dict(remediation_planner_summary_out)
        remediation_planner_chain_out = _append_remediation_planner_manifest(
            settings.data_dir,
            summary_path=remediation_planner_summary_out,
            planner_status=remediation_planner_payload.get("planner_status")
            if isinstance(remediation_planner_payload, dict)
            else None,
            rerun_trend=(
                remediation_planner_payload.get("planner_rerun_diff", {}).get("trend")
                if isinstance(remediation_planner_payload, dict)
                and isinstance(remediation_planner_payload.get("planner_rerun_diff"), dict)
                else None
            ),
            next_best_command=remediation_planner_payload.get("next_best_command")
            if isinstance(remediation_planner_payload, dict)
            else None,
            next_feedback_priority_reason=(
                remediation_planner_payload.get("entries", [{}])[0].get("feedback_priority_reason")
                if isinstance(remediation_planner_payload, dict)
                and isinstance(remediation_planner_payload.get("entries"), list)
                and remediation_planner_payload.get("entries")
                else None
            ),
            planned_step_count=remediation_planner_payload.get("planned_step_count")
            if isinstance(remediation_planner_payload, dict)
            else None,
        )
        remediation_execution_plan_payload = _read_json_dict(remediation_execution_plan_summary_out)
        remediation_execution_plan_chain_out = _append_remediation_execution_plan_manifest(
            settings.data_dir,
            summary_path=remediation_execution_plan_summary_out,
            execution_plan_status=(
                remediation_execution_plan_payload.get("execution_plan_status")
                if isinstance(remediation_execution_plan_payload, dict)
                else None
            ),
            next_action_command=(
                remediation_execution_plan_payload.get("next_action_command")
                if isinstance(remediation_execution_plan_payload, dict)
                else None
            ),
            next_action_feedback_priority_reason=(
                remediation_execution_plan_payload.get("actions", [{}])[0].get(
                    "feedback_priority_reason"
                )
                if isinstance(remediation_execution_plan_payload, dict)
                and isinstance(remediation_execution_plan_payload.get("actions"), list)
                and remediation_execution_plan_payload.get("actions")
                else None
            ),
            planned_action_count=(
                remediation_execution_plan_payload.get("planned_action_count")
                if isinstance(remediation_execution_plan_payload, dict)
                else None
            ),
        )
        remediation_session_payload = _read_json_dict(remediation_session_summary_out)
        remediation_session_chain_out = _append_remediation_session_manifest(
            settings.data_dir,
            summary_path=remediation_session_summary_out,
            session_status=(
                remediation_session_payload.get("session_status")
                if isinstance(remediation_session_payload, dict)
                else None
            ),
            next_pending_command=(
                remediation_session_payload.get("next_pending_command")
                if isinstance(remediation_session_payload, dict)
                else None
            ),
            next_pending_stage_signal_confidence=(
                remediation_session_payload.get("next_pending_stage_signal_confidence")
                if isinstance(remediation_session_payload, dict)
                else None
            ),
            next_pending_feedback_priority_reason=(
                remediation_session_payload.get("next_pending_feedback_priority_reason")
                if isinstance(remediation_session_payload, dict)
                else None
            ),
            pending_action_count=(
                remediation_session_payload.get("pending_action_count")
                if isinstance(remediation_session_payload, dict)
                else None
            ),
        )
        remediation_session_checkpoint_payload = _read_json_dict(
            remediation_session_checkpoint_summary_out
        )
        remediation_session_checkpoint_chain_out = _append_remediation_session_checkpoint_manifest(
            settings.data_dir,
            summary_path=remediation_session_checkpoint_summary_out,
            checkpoint_status=(
                remediation_session_checkpoint_payload.get("checkpoint_status")
                if isinstance(remediation_session_checkpoint_payload, dict)
                else None
            ),
            next_action_command=(
                remediation_session_checkpoint_payload.get("next_action_command")
                if isinstance(remediation_session_checkpoint_payload, dict)
                else None
            ),
            next_action_stage_signal_confidence=(
                remediation_session_checkpoint_payload.get("next_action_stage_signal_confidence")
                if isinstance(remediation_session_checkpoint_payload, dict)
                else None
            ),
            next_action_feedback_priority_reason=(
                next(
                    (
                        item.get("feedback_priority_reason")
                        for item in remediation_session_checkpoint_payload.get("actions", [])
                        if isinstance(item, dict)
                        and item.get("command")
                        == remediation_session_checkpoint_payload.get("next_action_command")
                    ),
                    None,
                )
                if isinstance(remediation_session_checkpoint_payload, dict)
                else None
            ),
            pending_action_count=(
                remediation_session_checkpoint_payload.get("pending_action_count")
                if isinstance(remediation_session_checkpoint_payload, dict)
                else None
            ),
        )
        remediation_scoreboard_payload = _read_json_dict(remediation_scoreboard_summary_out)
        remediation_scoreboard_chain_out = _append_remediation_scoreboard_manifest(
            settings.data_dir,
            summary_path=remediation_scoreboard_summary_out,
            scoreboard_status=(
                remediation_scoreboard_payload.get("scoreboard_status")
                if isinstance(remediation_scoreboard_payload, dict)
                else None
            ),
            next_action_command=(
                remediation_scoreboard_payload.get("next_action_command")
                if isinstance(remediation_scoreboard_payload, dict)
                else None
            ),
            next_action_stage_signal_confidence=(
                remediation_scoreboard_payload.get("next_action_stage_signal_confidence")
                if isinstance(remediation_scoreboard_payload, dict)
                else None
            ),
            next_action_feedback_priority_reason=(
                next(
                    (
                        item.get("feedback_priority_reason")
                        for item in remediation_scoreboard_payload.get("actions", [])
                        if isinstance(item, dict)
                        and item.get("command")
                        == remediation_scoreboard_payload.get("next_action_command")
                    ),
                    None,
                )
                if isinstance(remediation_scoreboard_payload, dict)
                else None
            ),
            completion_rate=(
                remediation_scoreboard_payload.get("completion_rate")
                if isinstance(remediation_scoreboard_payload, dict)
                else None
            ),
        )
        remediation_evaluator_payload = _read_json_dict(remediation_evaluator_summary_out)
        remediation_evaluator_chain_out = _append_remediation_evaluator_manifest(
            settings.data_dir,
            summary_path=remediation_evaluator_summary_out,
            evaluator_status=(
                remediation_evaluator_payload.get("evaluator_status")
                if isinstance(remediation_evaluator_payload, dict)
                else None
            ),
            next_action_key=(
                remediation_evaluator_payload.get("next_action_key")
                if isinstance(remediation_evaluator_payload, dict)
                else None
            ),
            auto_fail_count=(
                remediation_evaluator_payload.get("auto_fail_count")
                if isinstance(remediation_evaluator_payload, dict)
                else None
            ),
        )
        remediation_evidence_payload = _read_json_dict(remediation_evidence_summary_out)
        remediation_evidence_chain_out = _append_remediation_evidence_manifest(
            settings.data_dir,
            summary_path=remediation_evidence_summary_out,
            evidence_status=(
                remediation_evidence_payload.get("evidence_status")
                if isinstance(remediation_evidence_payload, dict)
                else None
            ),
            next_manual_review_action_key=(
                remediation_evidence_payload.get("next_manual_review_action_key")
                if isinstance(remediation_evidence_payload, dict)
                else None
            ),
            manual_review_action_count=(
                remediation_evidence_payload.get("manual_review_action_count")
                if isinstance(remediation_evidence_payload, dict)
                else None
            ),
        )
        remediation_command_results_payload = _read_json_dict(
            remediation_command_results_summary_out
        )
        remediation_command_results_chain_out = _append_remediation_command_results_manifest(
            settings.data_dir,
            summary_path=remediation_command_results_summary_out,
            command_results_status=(
                remediation_command_results_payload.get("command_results_status")
                if isinstance(remediation_command_results_payload, dict)
                else None
            ),
            next_unobserved_action_key=(
                remediation_command_results_payload.get("next_unobserved_action_key")
                if isinstance(remediation_command_results_payload, dict)
                else None
            ),
            missing_observation_count=(
                remediation_command_results_payload.get("missing_observation_count")
                if isinstance(remediation_command_results_payload, dict)
                else None
            ),
        )
        gap_history_out, gap_history_summary_out, _gap_history_text = _write_execution_gap_history(
            settings.data_dir
        )
        audit_timeline_out, audit_timeline_summary_out, _audit_timeline_text = (
            _write_audit_timeline(settings.data_dir)
        )
        audit_dashboard_out, audit_dashboard_summary_out, _refreshed_audit_dashboard_text = (
            _write_audit_dashboard(settings.data_dir)
        )
        audit_bundle_out, audit_bundle_manifest_out, _audit_bundle_text = _write_audit_bundle(
            settings.data_dir
        )
        audit_bundle_history_out, audit_bundle_history_summary_out, _audit_bundle_history_text = (
            _write_audit_bundle_history(settings.data_dir)
        )
        current_state_index_out, current_state_index_summary_out, _current_state_index_text = (
            _write_current_state_index(settings.data_dir)
        )
        readiness_snapshot_out, readiness_snapshot_summary_out, _readiness_snapshot_text = (
            _write_readiness_snapshot(settings.data_dir)
        )
        logger.info("written: {}", weekly_out)
        logger.info("written: {}", comparison_out)
        logger.info("written: {}", lifecycle_out)
        if daemon_manifest_artifacts is not None:
            logger.info("written: {}", daemon_manifest_artifacts[0])
            logger.info("written: {}", daemon_manifest_artifacts[1])
        if state_export_artifacts is not None:
            logger.info("written: {}", state_export_artifacts[0])
            logger.info("written: {}", state_export_artifacts[1])
        if state_restore_artifacts is not None:
            logger.info("written: {}", state_restore_artifacts[0])
            logger.info("written: {}", state_restore_artifacts[1])
        logger.info("written: {}", execution_snapshot_out)
        logger.info("written: {}", execution_snapshot_summary_out)
        logger.info("written: {}", execution_comparison_out)
        logger.info("written: {}", execution_comparison_summary_out)
        logger.info("written: {}", execution_diagnostics_out)
        logger.info("written: {}", execution_diagnostics_summary_out)
        logger.info("written: {}", execution_read_only_surfaces_out)
        logger.info("written: {}", execution_read_only_surfaces_summary_out)
        logger.info("written: {}", monitoring_out)
        logger.info("written: {}", ops_review_out)
        logger.info("written: {}", ops_review_summary_out)
        logger.info("written: {}", dashboard_out)
        logger.info("written: {}", dashboard_summary_out)
        logger.info("written: {}", runbook_out)
        logger.info("written: {}", runbook_summary_out)
        logger.info("written: {}", cycle_history_out)
        logger.info("written: {}", cycle_history_summary_out)
        logger.info("written: {}", gap_history_out)
        logger.info("written: {}", gap_history_summary_out)
        logger.info("written: {}", state_comparison_out)
        logger.info("written: {}", state_comparison_summary_out)
        logger.info("written: {}", snapshot_drift_out)
        logger.info("written: {}", snapshot_drift_summary_out)
        logger.info("written: {}", drift_overview_out)
        logger.info("written: {}", drift_overview_summary_out)
        logger.info("written: {}", phase_gate_out)
        logger.info("written: {}", phase_gate_summary_out)
        logger.info("written: {}", remediation_planner_out)
        logger.info("written: {}", remediation_planner_summary_out)
        logger.info("written: {}", remediation_execution_plan_out)
        logger.info("written: {}", remediation_execution_plan_summary_out)
        logger.info("written: {}", remediation_session_out)
        logger.info("written: {}", remediation_session_summary_out)
        logger.info("written: {}", remediation_session_checkpoint_out)
        logger.info("written: {}", remediation_session_checkpoint_summary_out)
        logger.info("written: {}", remediation_scoreboard_out)
        logger.info("written: {}", remediation_scoreboard_summary_out)
        logger.info("written: {}", remediation_evaluator_out)
        logger.info("written: {}", remediation_evaluator_summary_out)
        logger.info("written: {}", remediation_evidence_out)
        logger.info("written: {}", remediation_evidence_summary_out)
        logger.info("written: {}", remediation_command_results_out)
        logger.info("written: {}", remediation_command_results_summary_out)
        logger.info("written: {}", bundle_out)
        logger.info("written: {}", bundle_manifest_out)
        logger.info("written: {}", timeline_out)
        logger.info("written: {}", timeline_summary_out)
        logger.info("written: {}", audit_out)
        logger.info("written: {}", audit_manifest_out)
        logger.info("written: {}", audit_timeline_out)
        logger.info("written: {}", audit_timeline_summary_out)
        logger.info("written: {}", audit_dashboard_out)
        logger.info("written: {}", audit_dashboard_summary_out)
        logger.info("written: {}", audit_bundle_out)
        logger.info("written: {}", audit_bundle_manifest_out)
        logger.info("written: {}", audit_bundle_history_out)
        logger.info("written: {}", audit_bundle_history_summary_out)
        logger.info("written: {}", current_state_index_out)
        logger.info("written: {}", current_state_index_summary_out)
        logger.info("written: {}", readiness_snapshot_out)
        logger.info("written: {}", readiness_snapshot_summary_out)
        logger.info("appended: {}", bundle_chain_out)
        logger.info("appended: {}", audit_chain_out)
        logger.info("appended: {}", audit_bundle_chain_out)
        logger.info("appended: {}", remediation_planner_chain_out)
        logger.info("appended: {}", remediation_execution_plan_chain_out)
        logger.info("appended: {}", remediation_session_chain_out)
        logger.info("appended: {}", remediation_session_checkpoint_chain_out)
        logger.info("appended: {}", remediation_scoreboard_chain_out)
        logger.info("appended: {}", remediation_evaluator_chain_out)
        logger.info("appended: {}", remediation_evidence_chain_out)
        logger.info("appended: {}", remediation_command_results_chain_out)
        typer.echo(f"monitoring_status={monitoring['status']}")
        typer.echo(f"execution_snapshot_path={execution_snapshot_out}")
        typer.echo(f"execution_comparison_path={execution_comparison_out}")
        typer.echo(f"execution_diagnostics_path={execution_diagnostics_out}")
        typer.echo(f"execution_read_only_surfaces_path={execution_read_only_surfaces_out}")
        typer.echo(f"execution_gap_history_path={gap_history_out}")
        typer.echo(f"execution_state_comparison_history_path={state_comparison_out}")
        typer.echo(f"execution_snapshot_drift_history_path={snapshot_drift_out}")
        typer.echo(f"execution_drift_overview_path={drift_overview_out}")
        typer.echo(f"dashboard_path={dashboard_out}")
        typer.echo(f"runbook_path={runbook_out}")
        typer.echo(f"phase_gate_review_path={phase_gate_out}")
        typer.echo(f"remediation_planner_path={remediation_planner_out}")
        typer.echo(f"remediation_execution_plan_path={remediation_execution_plan_out}")
        typer.echo(f"remediation_session_path={remediation_session_out}")
        typer.echo(f"remediation_session_checkpoint_path={remediation_session_checkpoint_out}")
        typer.echo(f"remediation_scoreboard_path={remediation_scoreboard_out}")
        typer.echo(f"remediation_evaluator_path={remediation_evaluator_out}")
        typer.echo(f"remediation_evidence_path={remediation_evidence_out}")
        typer.echo(f"remediation_command_results_path={remediation_command_results_out}")
        typer.echo(f"current_state_index_path={current_state_index_out}")
        typer.echo(f"readiness_snapshot_path={readiness_snapshot_out}")
        for index, item in enumerate(_recommended_read_order(settings.data_dir), start=1):
            typer.echo(f"recommended_read_order_{index}={item}")
        typer.echo(dashboard_text)
