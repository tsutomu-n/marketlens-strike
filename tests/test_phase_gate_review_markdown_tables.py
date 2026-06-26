from sis.reports.phase_gate_review_markdown_tables import (
    diagnostics_table_lines,
    execution_drift_classification_lines,
    venue_decision_lines,
)


def test_diagnostics_table_lines_render_first_item_values() -> None:
    assert diagnostics_table_lines(
        [
            {
                "symbol": "SP500",
                "available": True,
                "items": [
                    {
                        "rows": 120,
                        "tradable_rate": 1.0,
                        "stale_rate": 0.0,
                        "l2_only_rate": 0.0,
                        "fee_mode_unknown_rate": 0.0,
                        "missing_mark_price_rate": 0.0,
                        "missing_index_price_rate": 0.0,
                        "spread_p90_bps": 5.0,
                    }
                ],
            }
        ]
    ) == [
        "| symbol | available | rows | tradable_rate | stale_rate | l2_only_rate | fee_mode_unknown_rate | missing_mark_price_rate | missing_index_price_rate | spread_p90_bps |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        "| SP500 | True | 120 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5.0 |",
    ]


def test_venue_decision_lines_render_rows_or_fallback() -> None:
    assert venue_decision_lines(
        [
            {
                "venue": "trade_xyz",
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "main_blocker": None,
            }
        ]
    ) == [
        "| venue | decision | main_blocker |",
        "| --- | --- | --- |",
        "| trade_xyz | CONDITIONAL_GO_NEEDS_LIVE_WINDOW |  |",
    ]
    assert venue_decision_lines([]) == ["- venue_decisions: unavailable"]


def test_execution_drift_classification_lines_escape_pipes_or_fallback() -> None:
    assert execution_drift_classification_lines(
        [
            {
                "signal": "execution_drift_overview_status",
                "observed": "degraded",
                "expected": "ok",
                "classification": "LIVE_READINESS_BLOCKER",
                "reason": "one|two",
                "root_source": "source|json",
                "derived_from": "field|name",
                "recommended_next_action": "run|again",
            }
        ]
    ) == [
        "| signal | observed | expected | classification | reason | root_source | derived_from | recommended_next_action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        "| execution_drift_overview_status | degraded | ok | LIVE_READINESS_BLOCKER | one/two | source/json | field/name | run/again |",
    ]
    assert execution_drift_classification_lines([]) == ["- execution_drift_classifications: none"]
