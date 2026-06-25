from __future__ import annotations

from pathlib import Path
from typing import Callable

from sis.reports.summary_normalizers import (
    audit_summary_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
)
from sis.storage.jsonl_store import read_json


def read_json_dict(path: Path) -> dict:
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def read_normalized_schedule_summary(
    settings_data_dir: Path,
    *,
    path: Path,
    normalizer: Callable[[dict], dict],
    report_path: str | None = None,
    default: dict | None = None,
) -> dict:
    if not path.exists():
        return dict(default or {})
    payload = read_json_dict(path)
    if not payload:
        return dict(default or {})
    if report_path is not None:
        payload = {
            **payload,
            "report_path": str(settings_data_dir / report_path),
        }
    return normalizer(payload)


def read_execution_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_snapshot_summary.json",
        normalizer=normalize_execution_snapshot_summary,
        report_path="reports/execution_snapshot.md",
    )


def read_execution_comparison_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        normalizer=normalize_execution_comparison_summary,
        report_path="reports/execution_venue_comparison.md",
    )


def read_execution_diagnostics_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        normalizer=normalize_execution_diagnostics_summary,
        report_path="reports/execution_venue_diagnostics.md",
    )


def read_execution_gap_history_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_gap_history_summary.json",
        normalizer=normalize_execution_gap_history_summary,
        report_path="reports/execution_gap_history.md",
        default={
            "entry_count": 0,
            "latest_status": None,
            "latest_execution_diagnostics_status": None,
        },
    )


def read_execution_state_comparison_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_state_comparison_history_summary.json",
        normalizer=normalize_execution_state_comparison_summary,
        report_path="reports/execution_state_comparison_history.md",
        default={"entry_count": 0, "latest_status_match": None, "mismatching_count": 0},
    )


def read_execution_snapshot_drift_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_snapshot_drift_history_summary.json",
        normalizer=normalize_execution_snapshot_drift_summary,
        report_path="reports/execution_snapshot_drift_history.md",
        default={"entry_count": 0, "latest_status_match": None, "mismatching_snapshot_count": 0},
    )


def read_execution_drift_overview_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        normalizer=normalize_execution_drift_overview_summary,
        report_path="reports/execution_drift_overview.md",
        default={
            "overall_status": None,
            "diagnostics_alignment_match": None,
            "state_comparison_mismatching_count": None,
            "snapshot_drift_mismatching_snapshot_count": None,
        },
    )


def read_readiness_schedule_summary(settings_data_dir: Path) -> dict:
    readiness_path = settings_data_dir / "ops/readiness_snapshot.json"
    if not readiness_path.exists():
        return {}
    payload = read_json_dict(readiness_path)
    if not payload:
        return {}
    return normalize_readiness_summary(
        {
            "overall_status": payload.get("overall_status"),
            "next_phase_candidate": payload.get("next_phase_candidate"),
            "execution_ready": payload.get("execution_ready"),
            "readiness_next_phase_candidate": payload.get("readiness_next_phase_candidate"),
            "readiness_execution_ready": payload.get("readiness_execution_ready"),
            "phase2_entry_allowed": payload.get("phase2_entry_allowed"),
            "report_path": str(settings_data_dir / "reports/readiness_snapshot.md"),
        }
    )


def read_audit_schedule_summary(settings_data_dir: Path) -> dict:
    audit_dashboard_path = settings_data_dir / "ops/audit_dashboard_summary.json"
    audit_bundle_path = settings_data_dir / "ops/audit_bundle_manifest.json"
    audit_dashboard = read_json_dict(audit_dashboard_path) if audit_dashboard_path.exists() else {}
    audit_bundle = read_json_dict(audit_bundle_path) if audit_bundle_path.exists() else {}
    return audit_summary_fields(audit_dashboard, audit_bundle)


def read_phase_gate_schedule_summary(settings_data_dir: Path) -> dict:
    return read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/phase_gate_review_summary.json",
        normalizer=normalize_phase_gate_summary,
    )


def daemon_dry_run_context(settings_data_dir: Path) -> dict:
    return {
        "execution_summary": read_execution_schedule_summary(settings_data_dir),
        "execution_comparison_summary": read_execution_comparison_schedule_summary(
            settings_data_dir
        ),
        "execution_diagnostics_summary": read_execution_diagnostics_schedule_summary(
            settings_data_dir
        ),
        "execution_gap_history_summary": read_execution_gap_history_schedule_summary(
            settings_data_dir
        ),
        "execution_state_comparison_summary": read_execution_state_comparison_schedule_summary(
            settings_data_dir
        ),
        "execution_snapshot_drift_summary": read_execution_snapshot_drift_schedule_summary(
            settings_data_dir
        ),
        "execution_drift_overview_summary": read_execution_drift_overview_schedule_summary(
            settings_data_dir
        ),
        "readiness_summary": read_readiness_schedule_summary(settings_data_dir),
    }
