from __future__ import annotations

import json
from pathlib import Path

from sis.commands.runtime_schedule_summaries import (
    read_audit_schedule_summary,
    read_execution_drift_overview_schedule_summary,
    read_execution_gap_history_schedule_summary,
    read_execution_schedule_summary,
    read_readiness_schedule_summary,
    daemon_dry_run_context,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_read_execution_schedule_summary_adds_report_path(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ops/execution_snapshot_summary.json",
        {"overall_status": "warn", "venue_count": 2},
    )

    summary = read_execution_schedule_summary(tmp_path)

    assert summary["overall_status"] == "warn"
    assert summary["venue_count"] == 2
    assert summary["report_path"] == str(tmp_path / "reports/execution_snapshot.md")


def test_missing_execution_history_summaries_return_stable_defaults(tmp_path: Path) -> None:
    gap_history = read_execution_gap_history_schedule_summary(tmp_path)
    drift_overview = read_execution_drift_overview_schedule_summary(tmp_path)

    assert gap_history == {
        "entry_count": 0,
        "latest_status": None,
        "latest_execution_diagnostics_status": None,
    }
    assert drift_overview == {
        "overall_status": None,
        "diagnostics_alignment_match": None,
        "state_comparison_mismatching_count": None,
        "snapshot_drift_mismatching_snapshot_count": None,
    }


def test_read_readiness_schedule_summary_normalizes_snapshot(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ops/readiness_snapshot.json",
        {
            "overall_status": "blocked",
            "next_phase_candidate": "paper_observation",
            "execution_ready": False,
            "phase2_entry_allowed": False,
        },
    )

    summary = read_readiness_schedule_summary(tmp_path)

    assert summary["overall_status"] == "blocked"
    assert summary["next_phase_candidate"] == "paper_observation"
    assert summary["execution_ready"] is False
    assert summary["phase2_entry_allowed"] is False
    assert summary["report_path"] == str(tmp_path / "reports/readiness_snapshot.md")


def test_read_audit_schedule_summary_merges_dashboard_and_bundle(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ops/audit_dashboard_summary.json",
        {"overall_status": "warn", "latest_operation": "paper-cycle"},
    )
    _write_json(
        tmp_path / "ops/audit_bundle_manifest.json",
        {"bundle_history_snapshot_count": 4},
    )

    summary = read_audit_schedule_summary(tmp_path)

    assert summary["overall_status"] == "warn"
    assert summary["latest_operation"] == "paper-cycle"
    assert summary["bundle_history_snapshot_count"] == 4


def test_daemon_dry_run_context_preserves_schedule_summary_keys(tmp_path: Path) -> None:
    context = daemon_dry_run_context(tmp_path)

    assert set(context) == {
        "execution_summary",
        "execution_comparison_summary",
        "execution_diagnostics_summary",
        "execution_gap_history_summary",
        "execution_state_comparison_summary",
        "execution_snapshot_drift_summary",
        "execution_drift_overview_summary",
        "readiness_summary",
    }
    assert context["execution_gap_history_summary"]["entry_count"] == 0
    assert context["readiness_summary"] == {}
