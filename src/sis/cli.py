from __future__ import annotations

from functools import partial

import typer

from sis.ops.manifest_chain import append_operation_manifest, create_operation_manifest
from sis.commands.ops import register_ops_commands
from sis.commands.operations_reports import register_operations_report_commands
from sis.commands.operations_refresh import register_operations_refresh_commands
from sis.commands.paper_cycle import register_paper_cycle_commands
from sis.commands.paper import register_paper_commands
from sis.commands.review import register_review_commands
from sis.commands.probe import register_probe_commands
from sis.commands.quotes import register_quote_commands
from sis.commands.remediation import register_remediation_commands
from sis.commands.research import register_research_commands
from sis.commands.strategy_authoring import register_strategy_authoring_commands
from sis.commands.strategy_ai_review import register_strategy_ai_review_commands
from sis.commands.strategy_case_lite import register_strategy_case_lite_commands
from sis.commands.crypto_perp import register_crypto_perp_commands
from sis.commands.crypto_perp_live import register_crypto_perp_live_commands
from sis.commands.strategy_daily_brief import register_strategy_daily_brief_commands
from sis.commands.strategy_drift_review import register_strategy_drift_review_commands
from sis.commands.strategy_inputs import register_strategy_input_commands
from sis.commands.strategy_learning import register_strategy_learning_commands
from sis.commands.strategy_model_loop import register_strategy_model_loop_commands
from sis.commands.strategy_micro_live_plan import register_strategy_micro_live_plan_commands
from sis.commands.strategy_next_scale_plan import register_strategy_next_scale_plan_commands
from sis.commands.strategy_live_observation import register_strategy_live_observation_commands
from sis.commands.strategy_paper_smoke import register_strategy_paper_smoke_commands
from sis.commands.strategy_review import register_strategy_review_commands
from sis.commands.strategy_runtime_observation import (
    register_strategy_runtime_observation_commands,
)
from sis.commands.strategy_scale_decision import register_strategy_scale_decision_commands
from sis.commands.strategy_stage import register_strategy_stage_commands
from sis.commands.strategy_workbench_viewer import register_strategy_workbench_viewer_commands
from sis.commands.execution import register_execution_commands
from sis.commands.bot import register_bot_commands
from sis.commands.execution_artifacts import (
    _adapter_for_venue,
    _refresh_execution_lineage_artifacts as _refresh_execution_lineage_artifacts_base,
    _write_execution_read_only_surfaces as _write_execution_read_only_surfaces_base,
    _write_execution_snapshot,
    _write_execution_venue_comparison,
    _write_execution_venue_diagnostics,
)
from sis.commands.runtime_context import (
    _daemon_dry_run_context,
    _echo_audit_summary,
    _echo_phase_gate_summary,
    _paper_last_run_audit_summary,
    _paper_last_run_execution_drift_overview_summary,
    _paper_last_run_execution_gap_history_summary,
    _paper_last_run_execution_snapshot_drift_summary,
    _paper_last_run_execution_state_comparison_summary,
    _paper_last_run_latest_execution_payload,
    _paper_last_run_phase_gate_summary,
    _paper_last_run_readiness_summary,
    _read_audit_schedule_summary,
    _read_execution_comparison_schedule_summary,
    _read_execution_diagnostics_schedule_summary,
    _read_execution_drift_overview_schedule_summary,
    _read_execution_gap_history_schedule_summary,
    _read_execution_schedule_summary,
    _read_execution_snapshot_drift_schedule_summary,
    _read_execution_state_comparison_schedule_summary,
    _read_readiness_schedule_summary,
    _recommended_read_order,
    _state_store,
    _write_comparison_report,
    _write_daemon_manifest_artifacts,
    _write_lifecycle_report,
    _write_monitoring_snapshot,
    _write_schedule_run_with_audit,
    _write_state_export_artifacts,
    _write_state_restore_artifacts,
    _write_weekly_review,
)
from sis.commands.report_writers import (
    _write_audit_bundle,
    _write_audit_bundle_history,
    _write_audit_dashboard,
    _write_audit_timeline,
    _write_current_state_index,
    _write_execution_drift_overview,
    _write_execution_gap_history,
    _write_execution_snapshot_drift_history,
    _write_execution_state_comparison_history,
    _write_operations_audit_pack,
    _write_operations_bundle,
    _write_operations_dashboard,
    _write_operations_timeline,
    _write_ops_review,
    _write_paper_cycle_history,
    _write_paper_operations_runbook,
    _write_phase_gate_review,
    _write_readiness_snapshot,
    _write_remediation_command_results,
    _write_remediation_evaluator,
    _write_remediation_evidence,
    _write_remediation_execution_plan,
    _write_remediation_planner,
    _write_remediation_scoreboard,
    _write_remediation_session,
    _write_remediation_session_checkpoint,
)
from sis.commands.manifest_appenders import (
    _append_audit_bundle_snapshot_manifest,
    _append_operations_audit_snapshot_manifest,
    _append_operations_snapshot_manifest,
    _append_paper_operations_cycle_manifest,
    _append_remediation_command_results_manifest,
    _append_remediation_evaluator_manifest,
    _append_remediation_evidence_ingest_manifest,
    _append_remediation_evidence_manifest,
    _append_remediation_execution_plan_manifest,
    _append_remediation_planner_manifest,
    _append_remediation_scoreboard_manifest,
    _append_remediation_session_checkpoint_manifest,
    _append_remediation_session_manifest,
    _run_paper_step,
)
from sis.reports.summary_normalizers import (
    normalize_phase_gate_summary,
)

app = typer.Typer(no_args_is_help=True)
register_probe_commands(app)


register_research_commands(app, _recommended_read_order)
register_strategy_authoring_commands(app)
register_strategy_input_commands(app)
register_strategy_review_commands(app)
register_strategy_stage_commands(app)
register_strategy_paper_smoke_commands(app)
register_strategy_runtime_observation_commands(app)
register_strategy_drift_review_commands(app)
register_strategy_learning_commands(app)
register_strategy_case_lite_commands(app)
register_strategy_daily_brief_commands(app)
register_strategy_ai_review_commands(app)
register_strategy_model_loop_commands(app)
register_strategy_micro_live_plan_commands(app)
register_strategy_next_scale_plan_commands(app)
register_strategy_live_observation_commands(app)
register_strategy_scale_decision_commands(app)
register_strategy_workbench_viewer_commands(app)
register_crypto_perp_commands(app)
register_crypto_perp_live_commands(app)
register_quote_commands(app, _recommended_read_order)
register_bot_commands(app, _recommended_read_order)


_write_execution_read_only_surfaces = partial(
    _write_execution_read_only_surfaces_base,
    state_store_fn=_state_store,
)
_refresh_execution_lineage_artifacts = partial(
    _refresh_execution_lineage_artifacts_base,
    write_execution_gap_history_fn=_write_execution_gap_history,
    write_execution_state_comparison_history_fn=_write_execution_state_comparison_history,
    write_execution_snapshot_drift_history_fn=_write_execution_snapshot_drift_history,
    write_execution_drift_overview_fn=_write_execution_drift_overview,
)


register_execution_commands(
    app,
    adapter_for_venue_fn=_adapter_for_venue,
    state_store_fn=_state_store,
    write_execution_snapshot_fn=_write_execution_snapshot,
    write_execution_venue_comparison_fn=_write_execution_venue_comparison,
    write_execution_venue_diagnostics_fn=_write_execution_venue_diagnostics,
    write_execution_read_only_surfaces_fn=_write_execution_read_only_surfaces,
    recommended_read_order_fn=_recommended_read_order,
)


register_ops_commands(
    app,
    state_store_fn=_state_store,
    write_monitoring_snapshot_fn=_write_monitoring_snapshot,
    write_schedule_run_with_audit_fn=_write_schedule_run_with_audit,
    create_operation_manifest_fn=create_operation_manifest,
    append_operation_manifest_fn=append_operation_manifest,
    refresh_execution_lineage_artifacts_fn=_refresh_execution_lineage_artifacts,
    write_execution_read_only_surfaces_fn=_write_execution_read_only_surfaces,
    daemon_dry_run_context_fn=_daemon_dry_run_context,
    write_daemon_manifest_artifacts_fn=_write_daemon_manifest_artifacts,
    write_state_export_artifacts_fn=_write_state_export_artifacts,
    write_state_restore_artifacts_fn=_write_state_restore_artifacts,
    normalize_phase_gate_summary_fn=normalize_phase_gate_summary,
    echo_audit_summary_fn=_echo_audit_summary,
    echo_phase_gate_summary_fn=_echo_phase_gate_summary,
    recommended_read_order_fn=_recommended_read_order,
)


register_operations_report_commands(
    app,
    write_lifecycle_report_fn=_write_lifecycle_report,
    write_comparison_report_fn=_write_comparison_report,
    write_ops_review_fn=_write_ops_review,
    write_operations_dashboard_fn=_write_operations_dashboard,
    write_paper_operations_runbook_fn=_write_paper_operations_runbook,
    write_paper_cycle_history_fn=_write_paper_cycle_history,
    write_execution_gap_history_fn=_write_execution_gap_history,
    write_execution_state_comparison_history_fn=_write_execution_state_comparison_history,
    write_execution_snapshot_drift_history_fn=_write_execution_snapshot_drift_history,
    write_execution_drift_overview_fn=_write_execution_drift_overview,
    write_phase_gate_review_fn=_write_phase_gate_review,
    write_operations_bundle_fn=_write_operations_bundle,
    write_operations_timeline_fn=_write_operations_timeline,
    write_operations_audit_pack_fn=_write_operations_audit_pack,
    write_audit_timeline_fn=_write_audit_timeline,
    write_audit_dashboard_fn=_write_audit_dashboard,
    write_audit_bundle_fn=_write_audit_bundle,
    write_audit_bundle_history_fn=_write_audit_bundle_history,
    write_current_state_index_fn=_write_current_state_index,
    write_readiness_snapshot_fn=_write_readiness_snapshot,
    append_operations_snapshot_manifest_fn=_append_operations_snapshot_manifest,
    append_operations_audit_snapshot_manifest_fn=_append_operations_audit_snapshot_manifest,
    append_audit_bundle_snapshot_manifest_fn=_append_audit_bundle_snapshot_manifest,
    recommended_read_order_fn=_recommended_read_order,
)

register_remediation_commands(
    app,
    write_remediation_planner_fn=_write_remediation_planner,
    write_remediation_execution_plan_fn=_write_remediation_execution_plan,
    write_remediation_session_fn=_write_remediation_session,
    write_remediation_session_checkpoint_fn=_write_remediation_session_checkpoint,
    write_remediation_command_results_fn=_write_remediation_command_results,
    write_remediation_scoreboard_fn=_write_remediation_scoreboard,
    write_remediation_evaluator_fn=_write_remediation_evaluator,
    write_remediation_evidence_fn=_write_remediation_evidence,
    append_remediation_planner_manifest_fn=_append_remediation_planner_manifest,
    append_remediation_execution_plan_manifest_fn=_append_remediation_execution_plan_manifest,
    append_remediation_session_manifest_fn=_append_remediation_session_manifest,
    append_remediation_session_checkpoint_manifest_fn=_append_remediation_session_checkpoint_manifest,
    append_remediation_evidence_ingest_manifest_fn=_append_remediation_evidence_ingest_manifest,
    append_remediation_scoreboard_manifest_fn=_append_remediation_scoreboard_manifest,
    append_remediation_evaluator_manifest_fn=_append_remediation_evaluator_manifest,
    append_remediation_evidence_manifest_fn=_append_remediation_evidence_manifest,
    append_remediation_command_results_manifest_fn=_append_remediation_command_results_manifest,
    recommended_read_order_fn=_recommended_read_order,
)


register_paper_commands(
    app,
    _run_paper_step=_run_paper_step,
    _read_audit_schedule_summary=_read_audit_schedule_summary,
    _paper_last_run_latest_execution_payload=_paper_last_run_latest_execution_payload,
    _paper_last_run_phase_gate_summary=_paper_last_run_phase_gate_summary,
    _paper_last_run_readiness_summary=_paper_last_run_readiness_summary,
    _paper_last_run_execution_gap_history_summary=_paper_last_run_execution_gap_history_summary,
    _paper_last_run_execution_state_comparison_summary=_paper_last_run_execution_state_comparison_summary,
    _paper_last_run_execution_snapshot_drift_summary=_paper_last_run_execution_snapshot_drift_summary,
    _paper_last_run_execution_drift_overview_summary=_paper_last_run_execution_drift_overview_summary,
    _write_weekly_review=_write_weekly_review,
    _recommended_read_order=_recommended_read_order,
)


register_operations_refresh_commands(
    app,
    _write_daemon_manifest_artifacts=_write_daemon_manifest_artifacts,
    _write_state_export_artifacts=_write_state_export_artifacts,
    _write_state_restore_artifacts=_write_state_restore_artifacts,
    _refresh_execution_lineage_artifacts=_refresh_execution_lineage_artifacts,
    _write_execution_read_only_surfaces=_write_execution_read_only_surfaces,
    _write_weekly_review=_write_weekly_review,
    _write_comparison_report=_write_comparison_report,
    _write_lifecycle_report=_write_lifecycle_report,
    _write_monitoring_snapshot=_write_monitoring_snapshot,
    _write_ops_review=_write_ops_review,
    _write_operations_dashboard=_write_operations_dashboard,
    _write_paper_operations_runbook=_write_paper_operations_runbook,
    _write_paper_cycle_history=_write_paper_cycle_history,
    _write_phase_gate_review=_write_phase_gate_review,
    _write_remediation_planner=_write_remediation_planner,
    _write_remediation_execution_plan=_write_remediation_execution_plan,
    _write_remediation_session=_write_remediation_session,
    _write_remediation_session_checkpoint=_write_remediation_session_checkpoint,
    _write_remediation_evaluator=_write_remediation_evaluator,
    _write_remediation_command_results=_write_remediation_command_results,
    _write_remediation_scoreboard=_write_remediation_scoreboard,
    _write_remediation_evidence=_write_remediation_evidence,
    _write_operations_bundle=_write_operations_bundle,
    _write_operations_timeline=_write_operations_timeline,
    _write_operations_audit_pack=_write_operations_audit_pack,
    _write_audit_timeline=_write_audit_timeline,
    _write_audit_dashboard=_write_audit_dashboard,
    _write_audit_bundle=_write_audit_bundle,
    _append_operations_snapshot_manifest=_append_operations_snapshot_manifest,
    _append_operations_audit_snapshot_manifest=_append_operations_audit_snapshot_manifest,
    _append_audit_bundle_snapshot_manifest=_append_audit_bundle_snapshot_manifest,
    _append_remediation_planner_manifest=_append_remediation_planner_manifest,
    _append_remediation_execution_plan_manifest=_append_remediation_execution_plan_manifest,
    _append_remediation_session_manifest=_append_remediation_session_manifest,
    _append_remediation_session_checkpoint_manifest=_append_remediation_session_checkpoint_manifest,
    _append_remediation_scoreboard_manifest=_append_remediation_scoreboard_manifest,
    _append_remediation_evaluator_manifest=_append_remediation_evaluator_manifest,
    _append_remediation_evidence_manifest=_append_remediation_evidence_manifest,
    _append_remediation_command_results_manifest=_append_remediation_command_results_manifest,
    _write_execution_gap_history=_write_execution_gap_history,
    _write_audit_bundle_history=_write_audit_bundle_history,
    _write_current_state_index=_write_current_state_index,
    _write_readiness_snapshot=_write_readiness_snapshot,
    _recommended_read_order=_recommended_read_order,
)


register_paper_cycle_commands(
    app,
    _run_paper_step=_run_paper_step,
    _refresh_execution_lineage_artifacts=_refresh_execution_lineage_artifacts,
    _write_execution_read_only_surfaces=_write_execution_read_only_surfaces,
    _write_weekly_review=_write_weekly_review,
    _write_comparison_report=_write_comparison_report,
    _write_lifecycle_report=_write_lifecycle_report,
    _write_monitoring_snapshot=_write_monitoring_snapshot,
    _write_ops_review=_write_ops_review,
    _write_operations_dashboard=_write_operations_dashboard,
    _write_paper_operations_runbook=_write_paper_operations_runbook,
    _write_phase_gate_review=_write_phase_gate_review,
    _read_audit_schedule_summary=_read_audit_schedule_summary,
    _paper_last_run_phase_gate_summary=_paper_last_run_phase_gate_summary,
    _read_execution_schedule_summary=_read_execution_schedule_summary,
    _read_execution_comparison_schedule_summary=_read_execution_comparison_schedule_summary,
    _read_execution_diagnostics_schedule_summary=_read_execution_diagnostics_schedule_summary,
    _read_execution_gap_history_schedule_summary=_read_execution_gap_history_schedule_summary,
    _read_execution_state_comparison_schedule_summary=_read_execution_state_comparison_schedule_summary,
    _read_execution_snapshot_drift_schedule_summary=_read_execution_snapshot_drift_schedule_summary,
    _paper_last_run_execution_drift_overview_summary=_paper_last_run_execution_drift_overview_summary,
    _read_readiness_schedule_summary=_read_readiness_schedule_summary,
    _append_paper_operations_cycle_manifest=_append_paper_operations_cycle_manifest,
    _write_paper_cycle_history=_write_paper_cycle_history,
    _write_execution_gap_history=_write_execution_gap_history,
    _write_execution_state_comparison_history=_write_execution_state_comparison_history,
    _write_execution_snapshot_drift_history=_write_execution_snapshot_drift_history,
    _write_execution_drift_overview=_write_execution_drift_overview,
    _write_operations_bundle=_write_operations_bundle,
    _write_operations_timeline=_write_operations_timeline,
    _write_operations_audit_pack=_write_operations_audit_pack,
    _write_audit_timeline=_write_audit_timeline,
    _write_audit_dashboard=_write_audit_dashboard,
    _write_audit_bundle=_write_audit_bundle,
    _append_operations_snapshot_manifest=_append_operations_snapshot_manifest,
    _append_operations_audit_snapshot_manifest=_append_operations_audit_snapshot_manifest,
    _append_audit_bundle_snapshot_manifest=_append_audit_bundle_snapshot_manifest,
    _write_audit_bundle_history=_write_audit_bundle_history,
    _write_current_state_index=_write_current_state_index,
    _write_readiness_snapshot=_write_readiness_snapshot,
    _recommended_read_order=_recommended_read_order,
)


register_review_commands(
    app,
    _paper_last_run_latest_execution_payload=_paper_last_run_latest_execution_payload,
    _paper_last_run_audit_summary=_paper_last_run_audit_summary,
    _paper_last_run_phase_gate_summary=_paper_last_run_phase_gate_summary,
    _read_readiness_schedule_summary=_read_readiness_schedule_summary,
    _read_execution_schedule_summary=_read_execution_schedule_summary,
    _read_execution_comparison_schedule_summary=_read_execution_comparison_schedule_summary,
    _read_execution_diagnostics_schedule_summary=_read_execution_diagnostics_schedule_summary,
    _read_execution_gap_history_schedule_summary=_read_execution_gap_history_schedule_summary,
    _read_execution_state_comparison_schedule_summary=_read_execution_state_comparison_schedule_summary,
    _read_execution_snapshot_drift_schedule_summary=_read_execution_snapshot_drift_schedule_summary,
    _read_execution_drift_overview_schedule_summary=_read_execution_drift_overview_schedule_summary,
    _recommended_read_order=_recommended_read_order,
)


def main() -> None:
    app()
