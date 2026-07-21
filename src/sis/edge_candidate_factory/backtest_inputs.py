from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


REQUIRED_BACKTEST_METRICS = (
    "event_count",
    "closed_trade_count",
    "after_cost_edge_over_no_trade_usd",
    "stress_edge_over_no_trade_usd",
    "largest_loss_usd",
    "profit_concentration",
)


@dataclass(frozen=True)
class BacktestMetricInputs:
    event_count: int | None = None
    closed_trade_count: int | None = None
    after_cost_edge_over_no_trade_usd: float | None = None
    stress_edge_over_no_trade_usd: float | None = None
    largest_loss_usd: float | None = None
    profit_concentration: float | None = None
    source_gap_count: int = 0
    unexecutable_reason_count: int = 0
    validation_peek_count: int = 0
    candidate_cluster_count: int = 0
    effective_trial_count: int | None = None
    metric_not_estimable_reasons: list[str] = field(default_factory=list)


def _summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = payload.get("summary", {})
    return raw if isinstance(raw, Mapping) else {}


def _number(summary: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def _integer(summary: Mapping[str, Any], *keys: str) -> int | None:
    value = _number(summary, *keys)
    return int(value) if value is not None else None


def _first_present(payloads: Sequence[Mapping[str, Any]], *keys: str) -> float | None:
    for payload in payloads:
        value = _number(_summary(payload), *keys)
        if value is not None:
            return value
    return None


def _first_present_int(payloads: Sequence[Mapping[str, Any]], *keys: str) -> int | None:
    value = _first_present(payloads, *keys)
    return int(value) if value is not None else None


def extract_backtest_metrics(payloads: Sequence[Mapping[str, Any]]) -> BacktestMetricInputs:
    event_count = _first_present_int(payloads, "event_count", "return_count")
    closed_trade_count = _first_present_int(payloads, "closed_trade_count", "trade_count")
    after_cost_edge = _first_present(payloads, "after_cost_edge_over_no_trade_usd")
    stress_edge = _first_present(payloads, "stress_edge_over_no_trade_usd")
    largest_loss = _first_present(payloads, "largest_loss_usd")
    profit_concentration = _first_present(payloads, "profit_concentration")
    source_gap_count = _first_present_int(payloads, "source_gap_count") or 0
    unexecutable_reason_count = _first_present_int(payloads, "unexecutable_reason_count") or 0
    validation_peek_count = _first_present_int(payloads, "validation_peek_count") or 0
    candidate_cluster_count = _first_present_int(payloads, "candidate_cluster_count") or 0
    effective_trial_count = _first_present_int(payloads, "effective_trial_count")
    values = {
        "event_count": event_count,
        "closed_trade_count": closed_trade_count,
        "after_cost_edge_over_no_trade_usd": after_cost_edge,
        "stress_edge_over_no_trade_usd": stress_edge,
        "largest_loss_usd": largest_loss,
        "profit_concentration": profit_concentration,
    }
    missing = [key for key in REQUIRED_BACKTEST_METRICS if values[key] is None]
    return BacktestMetricInputs(
        event_count=event_count,
        closed_trade_count=closed_trade_count,
        after_cost_edge_over_no_trade_usd=after_cost_edge,
        stress_edge_over_no_trade_usd=stress_edge,
        largest_loss_usd=largest_loss,
        profit_concentration=profit_concentration,
        source_gap_count=source_gap_count,
        unexecutable_reason_count=unexecutable_reason_count,
        validation_peek_count=validation_peek_count,
        candidate_cluster_count=candidate_cluster_count,
        effective_trial_count=effective_trial_count,
        metric_not_estimable_reasons=missing,
    )
