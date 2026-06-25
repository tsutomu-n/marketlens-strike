from __future__ import annotations

from pathlib import Path

from sis.live_evidence_manifest import LiveEvidenceManifest
from sis.live_evidence_operation_summaries import read_live_evidence_operation_summaries


def _write_json(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_read_live_evidence_operation_summaries_normalizes_operation_files(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    _write_json(
        data_dir / "ops/phase_gate_review_summary.json",
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false}',
    )
    _write_json(
        data_dir / "ops/execution_snapshot_summary.json",
        '{"overall_status":"ok","venue_count":2}',
    )
    _write_json(
        data_dir / "ops/execution_venue_comparison_summary.json",
        '{"all_registries_present":true}',
    )
    _write_json(
        data_dir / "ops/execution_venue_diagnostics_summary.json",
        '{"overall_status":"degraded","balance_gap_detected":true}',
    )
    _write_json(
        data_dir / "ops/execution_gap_history_summary.json",
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
    )
    _write_json(
        data_dir / "ops/execution_state_comparison_history_summary.json",
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
    )
    _write_json(
        data_dir / "ops/execution_snapshot_drift_history_summary.json",
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":2}',
    )
    _write_json(
        data_dir / "ops/execution_drift_overview_summary.json",
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":2}',
    )
    _write_json(
        data_dir / "ops/readiness_snapshot.json",
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
    )
    evidence_card_path = data_dir / "evidence/evidence_card_20260522_230800.json"
    _write_json(
        evidence_card_path,
        '{"cycle_history_latest_execution_summary":{"overall_status":"ok","venue_count":2},"cycle_history_latest_execution_comparison_summary":{"all_registries_present":true}}',
    )
    manifest = LiveEvidenceManifest(
        run_id="20260522_2308",
        duration_minutes=120,
        metadata_interval_seconds=60,
        data_dir=str(data_dir),
        artifacts={"evidence_card": str(evidence_card_path)},
    )

    summaries = read_live_evidence_operation_summaries(
        data_dir=data_dir,
        manifest=manifest,
    )

    assert summaries.phase_gate_summary["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert summaries.execution_summary["execution_overall_status"] == "ok"
    assert summaries.execution_summary["execution_venue_count"] == 2
    assert (
        summaries.execution_comparison_summary["execution_comparison_all_registries_present"]
        is True
    )
    assert summaries.execution_diagnostics_summary["execution_diagnostics_status"] == "degraded"
    assert summaries.execution_gap_history_summary["execution_gap_history_entry_count"] == 4
    assert (
        summaries.execution_state_comparison_summary["execution_state_comparison_mismatching_count"]
        == 1
    )
    assert (
        summaries.execution_snapshot_drift_summary[
            "execution_snapshot_drift_mismatching_snapshot_count"
        ]
        == 2
    )
    assert (
        summaries.execution_drift_overview_summary["execution_drift_overview_status"] == "degraded"
    )
    assert summaries.readiness_summary["execution_ready"] is False
    assert (
        summaries.evidence_card_summary["cycle_history_latest_execution_summary"]["overall_status"]
        == "ok"
    )
    assert (
        summaries.latest_execution_lineage["cycle_history_latest_execution_overall_status"] == "ok"
    )
    assert summaries.latest_execution_lineage["cycle_history_latest_execution_venue_count"] == 2
    assert (
        summaries.latest_execution_lineage[
            "cycle_history_latest_execution_comparison_all_registries_present"
        ]
        is True
    )


def test_read_live_evidence_operation_summaries_defaults_missing_files(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    manifest = LiveEvidenceManifest(
        run_id="20260522_2308",
        duration_minutes=120,
        metadata_interval_seconds=60,
        data_dir=str(data_dir),
        artifacts={"evidence_card": None},
    )

    summaries = read_live_evidence_operation_summaries(
        data_dir=data_dir,
        manifest=manifest,
    )

    assert summaries.phase_gate_summary == {}
    assert summaries.execution_summary == {}
    assert summaries.execution_comparison_summary == {}
    assert summaries.execution_diagnostics_summary == {}
    assert summaries.execution_gap_history_summary == {}
    assert summaries.execution_state_comparison_summary == {}
    assert summaries.execution_snapshot_drift_summary == {}
    assert summaries.execution_drift_overview_summary == {}
    assert summaries.readiness_summary == {}
    assert summaries.evidence_card_summary == {}
    assert summaries.latest_execution_lineage == {}
