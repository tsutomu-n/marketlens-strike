from __future__ import annotations

from typing import Any, cast


def _summary_int(value: object) -> int:
    return int(cast(Any, value) or 0)


def execution_ready(
    *,
    execution_snapshot_fields: dict[str, object],
    execution_comparison_fields: dict[str, object],
    execution_diagnostics_fields: dict[str, object],
    execution_gap_history_fields: dict[str, object],
    execution_state_comparison_fields: dict[str, object],
    execution_snapshot_drift_fields: dict[str, object],
    execution_drift_fields: dict[str, object],
) -> bool:
    return (
        execution_snapshot_fields.get("execution_overall_status") == "ok"
        and _summary_int(execution_snapshot_fields.get("execution_venue_count")) > 0
        and execution_comparison_fields.get("execution_comparison_all_registries_present") is True
        and execution_diagnostics_fields.get("execution_diagnostics_status") == "ok"
        and _summary_int(execution_gap_history_fields.get("execution_gap_history_entry_count")) > 0
        and _summary_int(
            execution_state_comparison_fields.get("execution_state_comparison_mismatching_count")
        )
        == 0
        and _summary_int(
            execution_snapshot_drift_fields.get(
                "execution_snapshot_drift_mismatching_snapshot_count"
            )
        )
        == 0
        and execution_drift_fields.get("execution_drift_overview_status") == "ok"
    )


def backtest_ready(backtest: dict[str, object]) -> bool:
    return _summary_int(backtest.get("total_trade_count")) > 0


def live_evidence_ready(live_evidence: dict[str, object]) -> bool:
    return live_evidence.get("decision") in {
        "GO",
        "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST",
    }


def operations_ready(operations: dict[str, object]) -> bool:
    return operations.get("overall_status") == "ok"


def phase_candidate(phase2_entry_allowed: bool) -> str:
    return "Phase 2" if phase2_entry_allowed else "Stay Phase 1"
