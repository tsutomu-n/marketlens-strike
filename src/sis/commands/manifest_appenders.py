from __future__ import annotations

from pathlib import Path

from sis.ops.manifest_chain import (
    append_operation_manifest,
    create_operation_manifest,
    latest_operation_manifest,
)
from sis.paper.runner import PaperRunSummary, run_paper_step
from sis.commands.runtime_context import (
    _execution_comparison_note_lines,
    _execution_diagnostics_note_lines,
    _execution_drift_note_lines,
    _execution_gap_history_note_lines,
    _execution_snapshot_drift_note_lines,
    _execution_state_comparison_note_lines,
    _execution_summary_note_lines,
    _phase_gate_note_lines,
    _read_execution_comparison_schedule_summary,
    _read_execution_diagnostics_schedule_summary,
    _read_execution_drift_overview_schedule_summary,
    _read_execution_gap_history_schedule_summary,
    _read_execution_schedule_summary,
    _read_execution_snapshot_drift_schedule_summary,
    _read_execution_state_comparison_schedule_summary,
    _read_phase_gate_schedule_summary,
    _read_readiness_schedule_summary,
    _readiness_note_lines,
)


def _run_paper_step(
    settings_data_dir: Path,
    *,
    state_path: Path | None,
    signals_path: Path | None,
) -> PaperRunSummary:
    return run_paper_step(
        settings_data_dir,
        state_path=state_path or (settings_data_dir / "state/marketlens.sqlite"),
        signals_path=signals_path,
    )


def _append_paper_operations_cycle_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    monitoring_status: str,
    orders_count: int,
    fills_count: int,
    open_positions: int,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="paper_operations_cycle",
        mode="paper",
        command="uv run sis paper-operations-cycle",
        status="completed" if monitoring_status == "ok" else monitoring_status,
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"orders={orders_count}",
            f"fills={fills_count}",
            f"open_positions={open_positions}",
            f"monitoring_status={monitoring_status}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_operations_snapshot_manifest(
    settings_data_dir: Path,
    *,
    manifest_path: Path,
    overall_status: str | None,
    cycle_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="operations_snapshot",
        mode="ops",
        command="uv run sis operations-bundle",
        status=overall_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(manifest_path)],
        notes=[
            f"overall_status={overall_status}",
            f"cycle_count={cycle_count}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_operations_audit_snapshot_manifest(
    settings_data_dir: Path,
    *,
    manifest_path: Path,
    overall_status: str | None,
    timeline_latest_operation: str | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="operations_audit_snapshot",
        mode="ops",
        command="uv run sis operations-audit-pack",
        status=overall_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(manifest_path)],
        notes=[
            f"overall_status={overall_status}",
            f"timeline_latest_operation={timeline_latest_operation}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_audit_bundle_snapshot_manifest(
    settings_data_dir: Path,
    *,
    manifest_path: Path,
    overall_status: str | None,
    timeline_latest_operation: str | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    execution = _read_execution_schedule_summary(settings_data_dir)
    execution_comparison = _read_execution_comparison_schedule_summary(settings_data_dir)
    execution_diagnostics = _read_execution_diagnostics_schedule_summary(settings_data_dir)
    gap_history = _read_execution_gap_history_schedule_summary(settings_data_dir)
    state_comparison = _read_execution_state_comparison_schedule_summary(settings_data_dir)
    snapshot_drift = _read_execution_snapshot_drift_schedule_summary(settings_data_dir)
    drift_overview = _read_execution_drift_overview_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="audit_bundle_snapshot",
        mode="ops",
        command="uv run sis audit-bundle",
        status=overall_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(manifest_path)],
        notes=[
            f"overall_status={overall_status}",
            f"timeline_latest_operation={timeline_latest_operation}",
            *_execution_summary_note_lines(execution),
            *_execution_comparison_note_lines(execution_comparison),
            *_execution_diagnostics_note_lines(execution_diagnostics),
            *_execution_gap_history_note_lines(gap_history),
            *_execution_state_comparison_note_lines(state_comparison),
            *_execution_snapshot_drift_note_lines(snapshot_drift),
            *_execution_drift_note_lines(drift_overview),
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_planner_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    planner_status: str | None,
    rerun_trend: str | None,
    next_best_command: str | None,
    next_feedback_priority_reason: str | None,
    planned_step_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_planner_dry_run",
        mode="ops",
        command="uv run sis remediation-planner",
        status=planner_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"planner_status={planner_status}",
            f"rerun_trend={rerun_trend}",
            f"planned_step_count={planned_step_count}",
            f"next_best_command={next_best_command}",
            f"next_feedback_priority_reason={next_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_execution_plan_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    execution_plan_status: str | None,
    next_action_command: str | None,
    next_action_feedback_priority_reason: str | None,
    planned_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_execution_plan_dry_run",
        mode="ops",
        command="uv run sis remediation-execution-plan",
        status=execution_plan_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"execution_plan_status={execution_plan_status}",
            f"planned_action_count={planned_action_count}",
            f"next_action_command={next_action_command}",
            f"next_action_feedback_priority_reason={next_action_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_session_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    session_status: str | None,
    next_pending_command: str | None,
    next_pending_stage_signal_confidence: str | None,
    next_pending_feedback_priority_reason: str | None,
    pending_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_session_dry_run",
        mode="ops",
        command="uv run sis remediation-session",
        status=session_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"session_status={session_status}",
            f"pending_action_count={pending_action_count}",
            f"next_pending_command={next_pending_command}",
            f"next_pending_stage_signal_confidence={next_pending_stage_signal_confidence}",
            f"next_pending_feedback_priority_reason={next_pending_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_session_checkpoint_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    checkpoint_status: str | None,
    next_action_command: str | None,
    next_action_stage_signal_confidence: str | None,
    next_action_feedback_priority_reason: str | None,
    pending_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_session_checkpoint",
        mode="ops",
        command="uv run sis remediation-session-checkpoint",
        status=checkpoint_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"checkpoint_status={checkpoint_status}",
            f"pending_action_count={pending_action_count}",
            f"next_action_command={next_action_command}",
            f"next_action_stage_signal_confidence={next_action_stage_signal_confidence}",
            f"next_action_feedback_priority_reason={next_action_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_scoreboard_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    scoreboard_status: str | None,
    next_action_command: str | None,
    next_action_stage_signal_confidence: str | None,
    next_action_feedback_priority_reason: str | None,
    completion_rate: float | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_scoreboard",
        mode="ops",
        command="uv run sis remediation-scoreboard",
        status=scoreboard_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"scoreboard_status={scoreboard_status}",
            f"completion_rate={completion_rate}",
            f"next_action_command={next_action_command}",
            f"next_action_stage_signal_confidence={next_action_stage_signal_confidence}",
            f"next_action_feedback_priority_reason={next_action_feedback_priority_reason}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_evaluator_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    evaluator_status: str | None,
    next_action_key: str | None,
    auto_fail_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_evaluator",
        mode="ops",
        command="uv run sis remediation-evaluator",
        status=evaluator_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"evaluator_status={evaluator_status}",
            f"auto_fail_count={auto_fail_count}",
            f"next_action_key={next_action_key}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_evidence_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    evidence_status: str | None,
    next_manual_review_action_key: str | None,
    manual_review_action_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_evidence",
        mode="ops",
        command="uv run sis remediation-evidence",
        status=evidence_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"evidence_status={evidence_status}",
            f"manual_review_action_count={manual_review_action_count}",
            f"next_manual_review_action_key={next_manual_review_action_key}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_command_results_manifest(
    settings_data_dir: Path,
    *,
    summary_path: Path,
    command_results_status: str | None,
    next_unobserved_action_key: str | None,
    missing_observation_count: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_command_results",
        mode="ops",
        command="uv run sis remediation-command-results",
        status=command_results_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(summary_path)],
        notes=[
            f"command_results_status={command_results_status}",
            f"missing_observation_count={missing_observation_count}",
            f"next_unobserved_action_key={next_unobserved_action_key}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)


def _append_remediation_evidence_ingest_manifest(
    settings_data_dir: Path,
    *,
    checkpoint_summary_path: Path,
    action_key: str | None,
    checkpoint_status: str | None,
    exit_code: int | None,
) -> Path:
    chain_path = settings_data_dir / "ops/operation_manifests.jsonl"
    parent = latest_operation_manifest(chain_path)
    phase_gate = _read_phase_gate_schedule_summary(settings_data_dir)
    readiness = _read_readiness_schedule_summary(settings_data_dir)
    manifest = create_operation_manifest(
        operation="remediation_evidence_ingest",
        mode="ops",
        command="uv run sis remediation-evidence-ingest",
        status=checkpoint_status or "unknown",
        parent_run_id=str(parent.get("run_id"))
        if isinstance(parent, dict) and parent.get("run_id")
        else None,
        artifacts=[str(checkpoint_summary_path)],
        notes=[
            f"action_key={action_key}",
            f"checkpoint_status={checkpoint_status}",
            f"exit_code={exit_code}",
            *_readiness_note_lines(readiness),
            *_phase_gate_note_lines(phase_gate),
        ],
    )
    return append_operation_manifest(chain_path, manifest)
