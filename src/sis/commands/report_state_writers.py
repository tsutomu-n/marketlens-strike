from __future__ import annotations

from pathlib import Path

from sis.commands.report_writer_common import write_operation_chain_report
from sis.reports.audit_bundle import build_audit_bundle_manifest
from sis.reports.audit_bundle_history import build_audit_bundle_history_report
from sis.reports.audit_dashboard import build_audit_dashboard
from sis.reports.audit_timeline import build_audit_timeline_report
from sis.reports.current_state_index import build_current_state_index
from sis.reports.readiness_snapshot import build_readiness_snapshot


def _write_audit_timeline(settings_data_dir: Path) -> tuple[Path, Path, str]:
    return write_operation_chain_report(
        settings_data_dir=settings_data_dir,
        report_filename="audit_timeline_report.md",
        summary_filename="audit_timeline_summary.json",
        build_report=build_audit_timeline_report,
    )


def _write_audit_dashboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_dashboard.md"
    summary_out = settings_data_dir / "ops/audit_dashboard_summary.json"
    text = build_audit_dashboard(
        bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        audit_pack_path=settings_data_dir / "ops/operations_audit_pack.json",
        audit_timeline_summary_path=settings_data_dir / "ops/audit_timeline_summary.json",
        audit_bundle_history_summary_path=settings_data_dir
        / "ops/audit_bundle_history_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir
        / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_audit_bundle(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_bundle_manifest.md"
    manifest_out = settings_data_dir / "ops/audit_bundle_manifest.json"
    text = build_audit_bundle_manifest(
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_timeline_summary_path=settings_data_dir / "ops/audit_timeline_summary.json",
        audit_pack_path=settings_data_dir / "ops/operations_audit_pack.json",
        audit_bundle_history_summary_path=settings_data_dir
        / "ops/audit_bundle_history_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir
        / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_audit_bundle_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_bundle_history_report.md"
    summary_out = settings_data_dir / "ops/audit_bundle_history_summary.json"
    text = build_audit_bundle_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _latest_live_evidence_summary_path() -> Path | None:
    summaries_root = Path("logs/live_evidence/summaries")
    paths = sorted(summaries_root.glob("live_evidence_summary_*.json"))
    return paths[-1] if paths else None


def _write_current_state_index(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/current_state_index.md"
    summary_out = settings_data_dir / "ops/current_state_index.json"
    text = build_current_state_index(
        operations_dashboard_summary_path=settings_data_dir
        / "ops/operations_dashboard_summary.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_manifest_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir
        / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        backtest_metrics_summary_path=settings_data_dir / "research/backtest_metrics_summary.json",
        live_evidence_summary_path=_latest_live_evidence_summary_path(),
        research_quality_report_path=settings_data_dir / "research/research_quality_report.md",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_readiness_snapshot(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/readiness_snapshot.md"
    summary_out = settings_data_dir / "ops/readiness_snapshot.json"
    text = build_readiness_snapshot(
        current_state_index_path=settings_data_dir / "ops/current_state_index.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir
        / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        backtest_metrics_summary_path=settings_data_dir / "research/backtest_metrics_summary.json",
        live_evidence_summary_path=_latest_live_evidence_summary_path(),
        operations_dashboard_summary_path=settings_data_dir
        / "ops/operations_dashboard_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
