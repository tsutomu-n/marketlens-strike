from __future__ import annotations

from pathlib import Path
from typing import Callable, cast

from sis.commands.runtime_schedule_summaries import (
    read_audit_schedule_summary,
    read_execution_drift_overview_schedule_summary,
    read_execution_gap_history_schedule_summary,
    read_execution_snapshot_drift_schedule_summary,
    read_execution_state_comparison_schedule_summary,
    read_phase_gate_schedule_summary,
    read_readiness_schedule_summary,
)
from sis.reports.summary_normalizers import latest_execution_lineage_payload_from_summary
from sis.state.store import StateStore
from sis.storage.jsonl_store import read_json, write_json


def read_json_dict(path: Path) -> dict[str, object]:
    payload = read_json(path)
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def paper_last_run_path(settings_data_dir: Path) -> Path | None:
    path = settings_data_dir / "state/paper_last_run.json"
    if not path.exists():
        store = StateStore(settings_data_dir / "state/marketlens.sqlite")
        payload = store.get_json("paper_last_run")
        if payload is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            write_json(path, payload)
    return path if path.exists() else None


def paper_last_run_payload(settings_data_dir: Path) -> dict:
    path = paper_last_run_path(settings_data_dir)
    if path is not None:
        return read_json_dict(path)
    return {}


def paper_last_run_summary(
    settings_data_dir: Path,
    key: str,
    fallback_reader: Callable[[Path], dict],
) -> dict:
    payload = paper_last_run_payload(settings_data_dir)
    summary = payload.get(key) if isinstance(payload, dict) else None
    if isinstance(summary, dict):
        return summary
    return fallback_reader(settings_data_dir)


def paper_last_run_audit_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "audit",
        read_audit_schedule_summary,
    )


def paper_last_run_phase_gate_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "phase_gate",
        read_phase_gate_schedule_summary,
    )


def paper_last_run_execution_drift_overview_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "execution_drift_overview_summary",
        read_execution_drift_overview_schedule_summary,
    )


def paper_last_run_readiness_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "readiness_summary",
        read_readiness_schedule_summary,
    )


def paper_last_run_execution_gap_history_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "execution_gap_history_summary",
        read_execution_gap_history_schedule_summary,
    )


def paper_last_run_execution_state_comparison_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "execution_state_comparison_summary",
        read_execution_state_comparison_schedule_summary,
    )


def paper_last_run_execution_snapshot_drift_summary(settings_data_dir: Path) -> dict:
    return paper_last_run_summary(
        settings_data_dir,
        "execution_snapshot_drift_summary",
        read_execution_snapshot_drift_schedule_summary,
    )


def paper_last_run_latest_execution_payload(settings_data_dir: Path) -> dict:
    return latest_execution_lineage_payload_from_summary(paper_last_run_payload(settings_data_dir))
