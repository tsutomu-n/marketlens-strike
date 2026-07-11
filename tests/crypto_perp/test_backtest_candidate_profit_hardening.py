from __future__ import annotations

from decimal import Decimal

import pytest

from sis.crypto_perp.backtest_candidate_pack_reports import (
    build_profit_robustness_summary,
    decide_backtest_candidate,
)
from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows
from .test_profit_readiness_local_automation import _event, _outcome


def test_profit_robustness_summary_exposes_overlap_and_losing_action_sleeve() -> None:
    signal_rows = [
        {
            "event_id": "event-1",
            "timestamp": "2026-07-09T00:00:00Z",
            "selected_action": "CONTINUATION_LONG",
        },
        {
            "event_id": "event-2",
            "timestamp": "2026-07-09T00:05:00Z",
            "selected_action": "CONTINUATION_LONG",
        },
        {
            "event_id": "event-3",
            "timestamp": "2026-07-09T01:05:00Z",
            "selected_action": "REVERSAL_SHORT",
        },
    ]
    results = [
        {
            "event_id": "event-1",
            "selected_action": "CONTINUATION_LONG",
            "fill_status": "simulated",
            "result_usd": "1",
        },
        {
            "event_id": "event-2",
            "selected_action": "CONTINUATION_LONG",
            "fill_status": "simulated",
            "result_usd": "2",
        },
        {
            "event_id": "event-3",
            "selected_action": "REVERSAL_SHORT",
            "fill_status": "simulated",
            "result_usd": "-0.5",
        },
    ]

    tournament_rows = build_cost_aware_tournament_rows(
        outcomes=[_outcome("event-1")],
        created_at="2026-07-09T04:00:00Z",
        notional_usd=Decimal("100"),
    )
    tournament_rows = tournament_rows.model_copy(
        update={
            "event_set": ["event-1", "event-2", "event-3"],
            "summary": {
                **tournament_rows.summary,
                "execution_windows": {
                    "event-1": {
                        "entry_at": "2026-07-09T00:00:00Z",
                        "settled_at": "2026-07-09T01:00:00Z",
                        "horizon_minutes": 60,
                    },
                    "event-2": {
                        "entry_at": "2026-07-09T00:05:00Z",
                        "settled_at": "2026-07-09T01:05:00Z",
                        "horizon_minutes": 60,
                    },
                    "event-3": {
                        "entry_at": "2026-07-09T01:05:00Z",
                        "settled_at": "2026-07-09T02:05:00Z",
                        "horizon_minutes": 60,
                    },
                },
            },
        }
    )

    summary = build_profit_robustness_summary(
        signal_rows=signal_rows,
        results=results,
        holding_minutes=60,
        notional_usd=Decimal("100"),
        tournament_rows=tournament_rows,
    )

    assert summary["peak_concurrent_positions"] == 2
    assert summary["peak_gross_notional_usd"] == "200"
    assert summary["non_overlapping_trade_count"] == 2
    assert summary["single_position_total_result_usd"] == "0.5"
    assert summary["position_overlap_accounted"] is False
    assert summary["action_performance"]["CONTINUATION_LONG"]["total_result_usd"] == "3"
    assert summary["action_performance"]["REVERSAL_SHORT"]["total_result_usd"] == "-0.5"
    assert summary["break_even_extra_cost_per_trade_usd"] == str(Decimal("2.5") / Decimal("3"))


def test_holding_horizon_mismatch_rejected_even_when_selector_trades_nothing() -> None:
    tournament_rows = build_cost_aware_tournament_rows(
        outcomes=[_outcome("event-1")],
        created_at="2026-07-09T04:00:00Z",
        notional_usd=Decimal("100"),
    )

    with pytest.raises(
        ValueError,
        match="max_holding_minutes=5 does not match actual outcome horizon=60",
    ):
        build_profit_robustness_summary(
            signal_rows=[
                {
                    "event_id": "event-1",
                    "timestamp": "2026-07-09T00:00:00Z",
                    "selected_action": "NO_TRADE",
                }
            ],
            results=[
                {
                    "event_id": "event-1",
                    "selected_action": "NO_TRADE",
                    "fill_status": "no_trade_baseline",
                    "result_usd": "0",
                }
            ],
            holding_minutes=5,
            notional_usd=Decimal("100"),
            tournament_rows=tournament_rows,
        )


@pytest.mark.parametrize(
    ("market_episode_count", "selector_beats_static", "expected", "reason"),
    [
        (
            5,
            True,
            "BACKTEST_COLLECT_MORE_DATA",
            "INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET",
        ),
        (
            10,
            False,
            "BACKTEST_REVISE",
            "SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION",
        ),
    ],
)
def test_candidate_requires_independent_episodes_and_selector_value_add(
    market_episode_count: int,
    selector_beats_static: bool,
    expected: str,
    reason: str,
) -> None:
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
    )
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
    ).model_copy(update={"pbo_status": "COMPUTED_PASS"})
    backtest_summary = {
        "executed_trade_count": 1,
        "unknown_count": 0,
        "blocked_missing_action_row_count": 0,
        "total_result_usd": "1",
        "max_drawdown_usd": "0",
        "profit_robustness": {
            "peak_concurrent_positions": 1,
            "position_overlap_accounted": True,
            "market_episode_count": market_episode_count,
            "selector_beats_best_static_action": selector_beats_static,
        },
    }

    decision, reasons = decide_backtest_candidate(
        event_count=10,
        outcome_count=10,
        min_events=10,
        ledger={"summary": {"critical_missing_count": 0}},
        no_lookahead={"summary": {"failed_count": 0, "unverified_count": 0}},
        backtest={"summary": backtest_summary},
        stress={"summary": {**backtest_summary, "total_result_usd": "1"}},
        rolling={"status": "complete"},
        guard=guard,
    )

    assert decision == expected
    assert reason in reasons
