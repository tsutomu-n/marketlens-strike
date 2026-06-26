from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from sis.reports.loaders import safe_read_json_dict

PR12_FRESH_READ_ONLY_SMOKE_SUMMARY = Path("ops/pr12_fresh_read_only_smoke_summary.json")
RUN_PR12_FRESH_READ_ONLY_SMOKE_ACTION = "run_pr12_fresh_read_only_smoke"


def pr12_fresh_read_only_smoke_completed(summary: Mapping[str, object]) -> bool:
    observed_window = summary.get("observed_window_seconds")
    observed_window_ok = (
        isinstance(observed_window, int | float)
        and not isinstance(observed_window, bool)
        and observed_window >= 3600
    )
    return (
        summary.get("final_decision") == "READ_ONLY_GO"
        and observed_window_ok
        and summary.get("next_action") == "none"
    )


def pr12_fresh_read_only_smoke_next_actions(data_dir: Path) -> list[str]:
    summary = safe_read_json_dict(data_dir / PR12_FRESH_READ_ONLY_SMOKE_SUMMARY)
    if pr12_fresh_read_only_smoke_completed(summary):
        return []
    return [RUN_PR12_FRESH_READ_ONLY_SMOKE_ACTION]
