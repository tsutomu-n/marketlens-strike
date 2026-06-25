from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sis.live_evidence_manifest import LiveEvidenceManifest
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    latest_execution_lineage_fields_from_summary,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
)


@dataclass(frozen=True)
class LiveEvidenceOperationSummaries:
    phase_gate_summary: dict
    execution_summary: dict
    execution_comparison_summary: dict
    execution_diagnostics_summary: dict
    execution_gap_history_summary: dict
    execution_state_comparison_summary: dict
    execution_snapshot_drift_summary: dict
    execution_drift_overview_summary: dict
    readiness_summary: dict
    evidence_card_summary: dict
    latest_execution_lineage: dict


def read_evidence_card_summary(manifest: LiveEvidenceManifest) -> dict:
    evidence_card_path = manifest.artifacts.get("evidence_card")
    if isinstance(evidence_card_path, str) and evidence_card_path:
        return safe_read_json_dict(Path(evidence_card_path))
    return {}


def read_live_evidence_operation_summaries(
    *,
    data_dir: Path,
    manifest: LiveEvidenceManifest,
) -> LiveEvidenceOperationSummaries:
    ops_dir = data_dir / "ops"
    evidence_card_summary = read_evidence_card_summary(manifest)
    return LiveEvidenceOperationSummaries(
        phase_gate_summary=safe_read_json_dict(ops_dir / "phase_gate_review_summary.json"),
        execution_summary=normalized_summary(
            ops_dir / "execution_snapshot_summary.json",
            normalize_execution_snapshot_summary,
        ),
        execution_comparison_summary=normalized_summary(
            ops_dir / "execution_venue_comparison_summary.json",
            normalize_execution_comparison_summary,
        ),
        execution_diagnostics_summary=normalized_summary(
            ops_dir / "execution_venue_diagnostics_summary.json",
            normalize_execution_diagnostics_summary,
        ),
        execution_gap_history_summary=normalized_summary(
            ops_dir / "execution_gap_history_summary.json",
            normalize_execution_gap_history_summary,
        ),
        execution_state_comparison_summary=normalized_summary(
            ops_dir / "execution_state_comparison_history_summary.json",
            normalize_execution_state_comparison_summary,
        ),
        execution_snapshot_drift_summary=normalized_summary(
            ops_dir / "execution_snapshot_drift_history_summary.json",
            normalize_execution_snapshot_drift_summary,
        ),
        execution_drift_overview_summary=normalized_summary(
            ops_dir / "execution_drift_overview_summary.json",
            normalize_execution_drift_overview_summary,
        ),
        readiness_summary=safe_read_json_dict(ops_dir / "readiness_snapshot.json"),
        evidence_card_summary=evidence_card_summary,
        latest_execution_lineage=latest_execution_lineage_fields_from_summary(
            evidence_card_summary
        ),
    )
