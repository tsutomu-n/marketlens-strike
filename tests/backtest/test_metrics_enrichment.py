from __future__ import annotations

from sis.backtest.engine.metrics_enrichment import enrich_run_metrics


def test_enrich_run_metrics_mutates_same_dict_with_run_context_fields() -> None:
    metrics: dict[str, object] = {"net_return_after_cost": 0.12}

    result = enrich_run_metrics(
        metrics,
        position_is_open=True,
        end_position_policy="mark_to_market_only",
        funding_events_ref="fixture://funding",
        funding_event_count=2,
    )

    assert result is metrics
    assert metrics == {
        "net_return_after_cost": 0.12,
        "open_position_at_end": True,
        "end_position_policy": "mark_to_market_only",
        "funding_events_ref": "fixture://funding",
        "funding_event_count": 2,
    }


def test_enrich_run_metrics_preserves_none_funding_events_ref_field() -> None:
    metrics: dict[str, object] = {}

    enrich_run_metrics(
        metrics,
        position_is_open=False,
        end_position_policy="force_close_if_executable",
        funding_events_ref=None,
        funding_event_count=0,
    )

    assert metrics["open_position_at_end"] is False
    assert metrics["end_position_policy"] == "force_close_if_executable"
    assert metrics["funding_events_ref"] is None
    assert metrics["funding_event_count"] == 0
