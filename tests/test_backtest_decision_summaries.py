from __future__ import annotations

from datetime import datetime, timezone
import json

from sis.backtest.decision_summaries import (
    enrich_backtest_decision_summary,
    executed_signal_summary,
    write_decision_summary,
)


def test_executed_signal_summary_aggregates_returns_counts_and_notional() -> None:
    summary = executed_signal_summary(
        [
            {
                "ts_signal": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "side": "long",
                "timeframe": "4h",
                "exit_reason": "fixed_horizon",
                "signal_return": 0.10,
                "cost_drag_bps": 3.0,
                "notional_usd": 100.0,
            },
            {
                "ts_signal": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc),
                "canonical_symbol": "SPY",
                "side": "short",
                "timeframe": "4h",
                "exit_reason": "time_stop",
                "signal_return": -0.02,
                "cost_drag_bps": 5.0,
                "notional_usd": 300.0,
            },
        ]
    )

    assert summary["result_count"] == 2
    assert summary["side_counts"] == {"long": 1, "short": 1}
    assert summary["symbol_counts"] == {"QQQ": 1, "SPY": 1}
    assert summary["timeframe_counts"] == {"4h": 2}
    assert summary["exit_reason_counts"] == {"fixed_horizon": 1, "time_stop": 1}
    assert summary["total_signal_return"] == 0.08
    assert summary["avg_signal_return"] == 0.04
    assert summary["win_rate"] == 0.5
    assert summary["total_cost_drag_bps"] == 8.0
    assert summary["total_notional_usd"] == 400.0
    assert summary["notional_weighted_signal_return"] == 0.01


def test_enrich_backtest_decision_summary_returns_copy_with_normalized_context() -> None:
    base = {"mode": "signal_driven", "executed_count": 1}

    enriched = enrich_backtest_decision_summary(
        base,
        audit_summary={"overall_status": "ok"},
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
        },
        readiness_summary={
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        },
        execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        timeline_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
    )

    assert enriched is not base
    assert base == {"mode": "signal_driven", "executed_count": 1}
    assert enriched["audit"] == {"overall_status": "ok"}
    assert enriched["phase_gate"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert enriched["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert enriched["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert enriched["execution_summary"]["execution_overall_status"] == "ok"
    assert enriched["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert enriched["timeline_latest_execution_venue_count"] == 2


def test_write_decision_summary_serializes_datetime(tmp_path) -> None:
    out = tmp_path / "decision_summary.json"

    write_decision_summary(
        {"generated_at": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc)},
        out,
    )

    assert json.loads(out.read_text(encoding="utf-8")) == {
        "generated_at": "2026-05-22 00:00:00+00:00"
    }
