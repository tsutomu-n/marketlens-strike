from __future__ import annotations

from sis.edge_candidate_factory.backtest_inputs import extract_backtest_metrics


def test_extract_backtest_metrics_reads_only_explicit_known_fields() -> None:
    metrics = extract_backtest_metrics(
        [
            {
                "schema_version": "strategy_authoring_backtest_metrics.v1",
                "summary": {
                    "event_count": 42,
                    "closed_trade_count": 30,
                    "after_cost_edge_over_no_trade_usd": 12.5,
                    "largest_loss_usd": -4.0,
                    "profit_concentration": 0.45,
                },
            },
            {
                "schema_version": "strategy_backtest_stress.v1",
                "summary": {"stress_edge_over_no_trade_usd": 3.25},
            },
        ]
    )

    assert metrics.event_count == 42
    assert metrics.closed_trade_count == 30
    assert metrics.after_cost_edge_over_no_trade_usd == 12.5
    assert metrics.stress_edge_over_no_trade_usd == 3.25
    assert metrics.largest_loss_usd == -4.0
    assert metrics.profit_concentration == 0.45
    assert metrics.metric_not_estimable_reasons == []


def test_extract_backtest_metrics_does_not_infer_missing_values() -> None:
    metrics = extract_backtest_metrics([{"summary": {"return_count": 50}}])

    assert metrics.event_count == 50
    assert metrics.closed_trade_count is None
    assert metrics.after_cost_edge_over_no_trade_usd is None
    assert metrics.stress_edge_over_no_trade_usd is None
    assert "closed_trade_count" in metrics.metric_not_estimable_reasons
    assert "after_cost_edge_over_no_trade_usd" in metrics.metric_not_estimable_reasons
