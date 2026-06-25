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
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def read_normalized_summary(
    *,
    data_dir: Path,
    summary_path: Path,
    report_path: str | None,
    normalizer: Callable[[dict], dict],
) -> dict:
    payload = read_json_dict(summary_path)
    if report_path is not None:
        payload = {
            **payload,
            "report_path": str(data_dir / report_path),
        }
    return normalizer(payload)


def read_audit_summary(data_dir: Path) -> dict:
    audit_dashboard_path = data_dir / "ops/audit_dashboard_summary.json"
    audit_bundle_path = data_dir / "ops/audit_bundle_manifest.json"
    audit_dashboard = read_json_dict(audit_dashboard_path)
    audit_bundle = read_json_dict(audit_bundle_path)
    return audit_summary_fields(audit_dashboard, audit_bundle)


def read_audit_dashboard_summary(data_dir: Path) -> dict:
    audit_dashboard_path = data_dir / "ops/audit_dashboard_summary.json"
    return read_json_dict(audit_dashboard_path)


def read_audit_bundle_summary(data_dir: Path) -> dict:
    audit_bundle_path = data_dir / "ops/audit_bundle_manifest.json"
    return read_json_dict(audit_bundle_path)


def read_operations_bundle_manifest(data_dir: Path) -> dict:
    bundle_path = data_dir / "ops/operations_bundle_manifest.json"
    return read_json_dict(bundle_path)


def read_phase_gate_summary(data_dir: Path) -> dict:
    phase_gate_path = data_dir / "ops/phase_gate_review_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=phase_gate_path,
        report_path=None,
        normalizer=normalize_phase_gate_summary,
    )


def read_execution_drift_overview_summary(data_dir: Path) -> dict:
    overview_path = data_dir / "ops/execution_drift_overview_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=overview_path,
        report_path="reports/execution_drift_overview.md",
        normalizer=normalize_execution_drift_overview_summary,
    )


def read_execution_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_snapshot_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_snapshot.md",
        normalizer=normalize_execution_snapshot_summary,
    )


def read_execution_comparison_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_venue_comparison_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_venue_comparison.md",
        normalizer=normalize_execution_comparison_summary,
    )


def read_execution_diagnostics_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_venue_diagnostics_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_venue_diagnostics.md",
        normalizer=normalize_execution_diagnostics_summary,
    )


def read_execution_gap_history_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_gap_history_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_gap_history.md",
        normalizer=normalize_execution_gap_history_summary,
    )


def read_execution_state_comparison_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_state_comparison_history_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_state_comparison_history.md",
        normalizer=normalize_execution_state_comparison_summary,
    )


def read_execution_snapshot_drift_summary(data_dir: Path) -> dict:
    summary_path = data_dir / "ops/execution_snapshot_drift_history_summary.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=summary_path,
        report_path="reports/execution_snapshot_drift_history.md",
        normalizer=normalize_execution_snapshot_drift_summary,
    )


def read_readiness_summary(data_dir: Path) -> dict:
    readiness_path = data_dir / "ops/readiness_snapshot.json"
    return read_normalized_summary(
        data_dir=data_dir,
        summary_path=readiness_path,
        report_path=None,
        normalizer=normalize_readiness_summary,
    )
