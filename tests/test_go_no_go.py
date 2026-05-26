from sis.models import Decision, GoNoGoCriterion, GoNoGoReport, VenueDecision
from sis.reports.go_no_go import (
    _decision_for_state,
    _threshold_result,
    _venue_decision_from_checks,
    write_go_no_go_markdown,
)


def test_threshold_result_requires_values_for_every_row() -> None:
    rows = [
        {"venue": "gtrade", "symbol": "SPY", "stale_rate": ""},
        {"venue": "ostium", "symbol": "XAU", "stale_rate": "0.0"},
    ]

    assert _threshold_result(rows, "stale_rate", maximum=0.05) == "MISSING"


def test_threshold_result_blocks_values_outside_threshold() -> None:
    rows = [
        {"venue": "gtrade", "symbol": "SPY", "tradable_rate": "0.90"},
        {"venue": "ostium", "symbol": "XAU", "tradable_rate": "1.0"},
    ]

    assert _threshold_result(rows, "tradable_rate", minimum=0.95) == "NO_GO"


def test_decision_for_state_names_live_window_condition() -> None:
    assert (
        _decision_for_state(
            core_ready=True,
            blockers=[
                "stale_rate at or below threshold",
                "tradable_rate at or above threshold",
            ],
            signals_exists=False,
        )
        == Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW
    )


def test_decision_for_state_names_cost_failure() -> None:
    assert (
        _decision_for_state(
            core_ready=True,
            blockers=["Holding/rollover cost reproduced for target horizons"],
            signals_exists=True,
        )
        == Decision.NO_GO_COST
    )


def test_decision_for_state_names_missing_signal_backtest_when_otherwise_ready() -> None:
    assert (
        _decision_for_state(
            core_ready=True,
            blockers=[],
            signals_exists=False,
        )
        == Decision.CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST
    )


def test_decision_for_state_go_when_ready_and_signal_backtest_present() -> None:
    assert (
        _decision_for_state(
            core_ready=True,
            blockers=[],
            signals_exists=True,
        )
        == Decision.GO
    )


def test_go_no_go_markdown_includes_venue_decisions(tmp_path) -> None:
    report = GoNoGoReport(
        decision=Decision.CONDITIONAL_GO_DATA_READY,
        criteria=[],
        venue_decisions=[
            VenueDecision(venue="gtrade", decision=Decision.GO, main_blocker=None),
            VenueDecision(
                venue="ostium",
                decision=Decision.CONDITIONAL_GO_DATA_READY,
                main_blocker="Liquidation reference complete",
            ),
        ],
    )
    out = tmp_path / "go_no_go_report.md"

    write_go_no_go_markdown(
        report,
        out,
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
        },
        readiness_summary={
            "next_phase_candidate": "Stay Phase 1",
            "execution_ready": False,
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
        },
        execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
            "report_path": "data/reports/execution_snapshot.md",
        },
        execution_comparison_summary={
            "all_registries_present": True,
            "report_path": "data/reports/execution_venue_comparison.md",
        },
        execution_diagnostics_summary={
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
            "report_path": "data/reports/execution_venue_diagnostics.md",
        },
        execution_gap_history_summary={
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "report_path": "data/reports/execution_gap_history.md",
        },
        execution_state_comparison_summary={
            "entry_count": 4,
            "latest_status_match": False,
            "mismatching_count": 1,
            "report_path": "data/reports/execution_state_comparison_history.md",
        },
        execution_snapshot_drift_summary={
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_snapshot_drift_history.md",
        },
        timeline_latest_execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
        },
        timeline_latest_execution_comparison_summary={
            "all_registries_present": True,
        },
        bundle_history_latest_execution_summary={
            "overall_status": "warn",
            "venue_count": 1,
        },
        bundle_history_latest_execution_comparison_summary={
            "all_registries_present": False,
        },
        cycle_history_latest_execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
        },
        cycle_history_latest_execution_comparison_summary={
            "all_registries_present": True,
        },
    )

    text = out.read_text(encoding="utf-8")
    assert "## Quick Navigation" in text
    assert f"- go_no_go_report: {out}" in text
    assert "## Related Reports" in text
    assert "- execution_snapshot_report: data/reports/execution_snapshot.md" in text
    assert "## Audit Summary" in text
    assert "overall_status: ok" in text
    assert "## Phase Gate Summary" in text
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "## Readiness Summary" in text
    assert "next_phase_candidate: Stay Phase 1" in text
    assert "## Execution Snapshot" in text
    assert "overall_status: ok" in text
    assert "venue_count: 2" in text
    assert "## Execution Venue Comparison" in text
    assert "all_registries_present: True" in text
    assert "## Execution Venue Diagnostics" in text
    assert "balance_gap_detected: True" in text
    assert "## Execution Gap History" in text
    assert "entry_count: 4" in text
    assert "## Execution State Comparison History" in text
    assert "mismatching_count: 1" in text
    assert "## Execution Snapshot Drift History" in text
    assert "mismatching_snapshot_count: 1" in text
    assert "## Audit Timeline Latest Execution" in text
    assert "## Audit Bundle History Latest Execution" in text
    assert "## Cycle History Latest Execution" in text
    assert "## Venue Decisions" in text
    assert "| gtrade | GO |  |" in text
    assert "| ostium | CONDITIONAL_GO_DATA_READY | Liquidation reference complete |" in text


def test_ostium_venue_decision_does_not_hide_live_window_failures() -> None:
    decision = _venue_decision_from_checks(
        "ostium",
        [
            GoNoGoCriterion(
                criterion="stale_rate at or below threshold",
                result="NO_GO",
                evidence="cost matrix",
            )
        ],
    )

    assert decision.decision == Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW
    assert decision.main_blocker == "stale_rate at or below threshold"
