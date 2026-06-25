from __future__ import annotations

from sis.reports.readiness_snapshot_status import (
    backtest_ready,
    execution_ready,
    live_evidence_ready,
    operations_ready,
    phase_candidate,
)


def _execution_ready_kwargs() -> dict[str, dict[str, object]]:
    return {
        "execution_snapshot_fields": {
            "execution_overall_status": "ok",
            "execution_venue_count": "2",
        },
        "execution_comparison_fields": {
            "execution_comparison_all_registries_present": True,
        },
        "execution_diagnostics_fields": {
            "execution_diagnostics_status": "ok",
        },
        "execution_gap_history_fields": {
            "execution_gap_history_entry_count": "3",
        },
        "execution_state_comparison_fields": {
            "execution_state_comparison_mismatching_count": "0",
        },
        "execution_snapshot_drift_fields": {
            "execution_snapshot_drift_mismatching_snapshot_count": "0",
        },
        "execution_drift_fields": {
            "execution_drift_overview_status": "ok",
        },
    }


def test_execution_ready_requires_all_execution_gates() -> None:
    kwargs = _execution_ready_kwargs()

    assert execution_ready(**kwargs)

    fields = _execution_ready_kwargs()
    fields["execution_snapshot_fields"]["execution_venue_count"] = 0
    assert not execution_ready(**fields)

    fields = _execution_ready_kwargs()
    fields["execution_comparison_fields"]["execution_comparison_all_registries_present"] = False
    assert not execution_ready(**fields)

    fields = _execution_ready_kwargs()
    fields["execution_diagnostics_fields"]["execution_diagnostics_status"] = "degraded"
    assert not execution_ready(**fields)

    fields = _execution_ready_kwargs()
    fields["execution_gap_history_fields"]["execution_gap_history_entry_count"] = 0
    assert not execution_ready(**fields)

    fields = _execution_ready_kwargs()
    fields["execution_state_comparison_fields"]["execution_state_comparison_mismatching_count"] = 1
    assert not execution_ready(**fields)

    fields = _execution_ready_kwargs()
    fields["execution_snapshot_drift_fields"][
        "execution_snapshot_drift_mismatching_snapshot_count"
    ] = 1
    assert not execution_ready(**fields)

    fields = _execution_ready_kwargs()
    fields["execution_drift_fields"]["execution_drift_overview_status"] = "degraded"
    assert not execution_ready(**fields)


def test_other_readiness_helpers_preserve_thresholds() -> None:
    assert backtest_ready({"total_trade_count": 1})
    assert not backtest_ready({"total_trade_count": 0})

    assert live_evidence_ready({"decision": "GO"})
    assert live_evidence_ready({"decision": "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST"})
    assert not live_evidence_ready({"decision": "NO_GO"})

    assert operations_ready({"overall_status": "ok"})
    assert not operations_ready({"overall_status": "warn"})

    assert phase_candidate(True) == "Phase 2"
    assert phase_candidate(False) == "Stay Phase 1"
