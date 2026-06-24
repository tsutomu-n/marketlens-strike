from pathlib import Path
from types import SimpleNamespace

from sis.reports.live_evidence_html import render_live_evidence_html


def test_render_live_evidence_html_includes_sections_and_escapes_values() -> None:
    data = SimpleNamespace(
        status="completed",
        decision="GO",
        started_at_utc="2026-05-22T14:08:00Z",
        finished_at_utc="2026-05-22T16:08:30Z",
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "remain_in_phase1",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 0,
            "checked_files": 7,
        },
        readiness_summary={
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        },
        venue_decisions=[
            {"venue": "<script>alert(1)</script>", "decision": "BLOCK", "main_blocker": "x < y"}
        ],
        quote_diagnostics=[
            SimpleNamespace(
                symbol="SPY",
                rows=1,
                market_open_rows=1,
                tradable_rate=1.0,
                stale_rate=0.0,
                missing_mark_price_rate=0.0,
                missing_index_price_rate=0.0,
                oracle_age_p90_ms=None,
                spread_p90_bps=None,
            )
        ],
        cost_rows=[
            {
                "venue": "trade_xyz",
                "symbol": "SPY",
                "stale_rate": "0",
                "tradable_rate": "1",
                "spread_p90_bps": "2",
                "holding_cost_4h_bps": "0.5",
                "notes": "safe",
            }
        ],
        backtest_metrics=[
            {
                "venue": "trade_xyz",
                "canonical_symbol": "SPY",
                "trade_count": 2,
                "avg_trade_return": 0.1,
                "cost_drag_bps": 1.5,
                "stale_rejected_count": 0,
                "halt_rejected_count": 0,
            }
        ],
        blockers=["unsafe <blocker>"],
        next_actions=["rerun <check>"],
        validation=SimpleNamespace(
            checked_files=1,
            issues=[SimpleNamespace(path=Path("bad<path>.json"), message="x < y")],
        ),
        artifacts=SimpleNamespace(evidence_card=Path("data/evidence/card.json")),
        log_tail=["tail <line>"],
        row_counts={"sidecar_metadata": 1, "sidecar_pricing": 2, "raw_quotes": 3},
        execution_summary={"overall_status": "ok", "venue_count": 1},
        execution_comparison_summary={"all_registries_present": True},
        execution_diagnostics_summary={
            "overall_status": "ok",
            "balance_gap_detected": False,
            "fills_gap_detected": False,
        },
        execution_gap_history_summary={"entry_count": 1, "latest_status": "ok"},
        execution_state_comparison_summary={
            "entry_count": 1,
            "latest_status_match": True,
            "mismatching_count": 0,
        },
        execution_snapshot_drift_summary={
            "entry_count": 1,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 0,
        },
        execution_drift_overview_summary={
            "overall_status": "ok",
            "diagnostics_alignment_match": True,
            "state_comparison_mismatching_count": 0,
            "snapshot_drift_mismatching_snapshot_count": 0,
        },
        timeline_latest_execution_summary={},
        timeline_latest_execution_comparison_summary={},
        bundle_history_latest_execution_summary={},
        bundle_history_latest_execution_comparison_summary={},
        cycle_history_latest_execution_summary={},
        cycle_history_latest_execution_comparison_summary={},
    )

    html = render_live_evidence_html(data)

    assert "<!DOCTYPE html>" in html
    assert "<h2>Audit Summary</h2>" in html
    assert "<h2>GTrade Diagnostics</h2>" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "unsafe &lt;blocker&gt;" in html
    assert "tail &lt;line&gt;" in html
    assert "<script>alert(1)</script>" not in html
