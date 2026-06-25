from __future__ import annotations

import json
from pathlib import Path

from sis.commands.runtime_paper_last_run_summaries import (
    paper_last_run_audit_summary,
    paper_last_run_execution_drift_overview_summary,
    paper_last_run_latest_execution_payload,
    paper_last_run_path,
    paper_last_run_phase_gate_summary,
    paper_last_run_readiness_summary,
)
from sis.state.store import StateStore


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_paper_last_run_summaries_prefer_cached_file_payload(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "state/paper_last_run.json",
        {
            "audit": {"overall_status": "ok", "latest_operation": "paper-cycle"},
            "phase_gate": {"decision": "GO", "phase2_entry_allowed": True},
            "readiness_summary": {
                "next_phase_candidate": "paper_observation",
                "execution_ready": True,
            },
            "execution_drift_overview_summary": {
                "overall_status": "stable",
                "diagnostics_alignment_match": True,
            },
            "timeline_latest_execution_summary": {
                "overall_status": "ok",
                "venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "all_registries_present": True,
            },
        },
    )
    _write_json(
        tmp_path / "ops/phase_gate_review_summary.json",
        {"decision": "HOLD", "phase2_entry_allowed": False},
    )

    assert paper_last_run_audit_summary(tmp_path) == {
        "overall_status": "ok",
        "latest_operation": "paper-cycle",
    }
    assert paper_last_run_phase_gate_summary(tmp_path) == {
        "decision": "GO",
        "phase2_entry_allowed": True,
    }
    assert paper_last_run_readiness_summary(tmp_path)["execution_ready"] is True
    assert paper_last_run_execution_drift_overview_summary(tmp_path)["overall_status"] == "stable"
    assert paper_last_run_latest_execution_payload(tmp_path) == {
        "timeline_latest_execution_summary": {
            "overall_status": "ok",
            "venue_count": 2,
        },
        "timeline_latest_execution_comparison_summary": {
            "all_registries_present": True,
        },
        "bundle_history_latest_execution_summary": None,
        "bundle_history_latest_execution_comparison_summary": None,
        "cycle_history_latest_execution_summary": None,
        "cycle_history_latest_execution_comparison_summary": None,
    }


def test_paper_last_run_summary_falls_back_to_schedule_summary(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ops/phase_gate_review_summary.json",
        {"decision": "HOLD", "phase2_entry_allowed": False},
    )

    assert paper_last_run_phase_gate_summary(tmp_path)["decision"] == "HOLD"
    assert paper_last_run_phase_gate_summary(tmp_path)["phase2_entry_allowed"] is False


def test_paper_last_run_path_materializes_state_store_payload(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state/marketlens.sqlite")
    store.set_json("paper_last_run", {"phase_gate": {"decision": "GO"}})

    path = paper_last_run_path(tmp_path)

    assert path == tmp_path / "state/paper_last_run.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"phase_gate": {"decision": "GO"}}
    assert paper_last_run_phase_gate_summary(tmp_path)["decision"] == "GO"
