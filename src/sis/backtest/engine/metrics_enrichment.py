from __future__ import annotations

from typing import Any


def enrich_run_metrics(
    metrics: dict[str, Any],
    *,
    position_is_open: bool,
    end_position_policy: str | None,
    funding_events_ref: str | None,
    funding_event_count: int,
) -> dict[str, Any]:
    metrics["open_position_at_end"] = position_is_open
    metrics["end_position_policy"] = end_position_policy
    metrics["funding_events_ref"] = funding_events_ref
    metrics["funding_event_count"] = funding_event_count
    return metrics
