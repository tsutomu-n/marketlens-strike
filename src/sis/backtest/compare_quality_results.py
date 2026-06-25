from __future__ import annotations

from typing import Any

__all__ = ["benchmark_relative", "regime_split", "rolling_stability", "stress"]


def stress(stress_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if stress_payload is None:
        return None
    summary = stress_payload.get("summary")
    return {
        "stress_kind": stress_payload.get("stress_kind"),
        "scenario_count": stress_payload.get("scenario_count"),
        "summary": summary if isinstance(summary, dict) else {},
        "scenarios": stress_payload.get("scenarios") or [],
        "dependency_added": stress_payload.get("dependency_added"),
        "paper_only": stress_payload.get("paper_only"),
        "permits_live_order": stress_payload.get("permits_live_order"),
        "live_conversion_allowed": stress_payload.get("live_conversion_allowed"),
        "wallet_used": stress_payload.get("wallet_used"),
        "exchange_write_used": stress_payload.get("exchange_write_used"),
    }


def regime_split(regime_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if regime_payload is None:
        return None
    summary = regime_payload.get("summary")
    return {
        "split_kind": regime_payload.get("split_kind"),
        "dimension_count": regime_payload.get("dimension_count"),
        "summary": summary if isinstance(summary, dict) else {},
        "dimensions": regime_payload.get("dimensions") or [],
        "dependency_added": regime_payload.get("dependency_added"),
        "paper_only": regime_payload.get("paper_only"),
        "permits_live_order": regime_payload.get("permits_live_order"),
        "live_conversion_allowed": regime_payload.get("live_conversion_allowed"),
        "wallet_used": regime_payload.get("wallet_used"),
        "exchange_write_used": regime_payload.get("exchange_write_used"),
    }


def rolling_stability(rolling_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if rolling_payload is None:
        return None
    summary = rolling_payload.get("summary")
    return {
        "stability_kind": rolling_payload.get("stability_kind"),
        "window_count": rolling_payload.get("window_count"),
        "summary": summary if isinstance(summary, dict) else {},
        "windows": rolling_payload.get("windows") or [],
        "dependency_added": rolling_payload.get("dependency_added"),
        "paper_only": rolling_payload.get("paper_only"),
        "permits_live_order": rolling_payload.get("permits_live_order"),
        "live_conversion_allowed": rolling_payload.get("live_conversion_allowed"),
        "wallet_used": rolling_payload.get("wallet_used"),
        "exchange_write_used": rolling_payload.get("exchange_write_used"),
    }


def benchmark_relative(benchmark_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if benchmark_payload is None:
        return None
    summary = benchmark_payload.get("summary")
    return {
        "comparison_kind": benchmark_payload.get("comparison_kind"),
        "benchmark_return_column": benchmark_payload.get("benchmark_return_column"),
        "benchmark_series_return_column": benchmark_payload.get("benchmark_series_return_column"),
        "price_column": benchmark_payload.get("price_column"),
        "horizon_minutes": benchmark_payload.get("horizon_minutes"),
        "summary": summary if isinstance(summary, dict) else {},
        "comparisons": benchmark_payload.get("comparisons") or [],
        "dependency_added": benchmark_payload.get("dependency_added"),
        "paper_only": benchmark_payload.get("paper_only"),
        "permits_live_order": benchmark_payload.get("permits_live_order"),
        "live_conversion_allowed": benchmark_payload.get("live_conversion_allowed"),
        "wallet_used": benchmark_payload.get("wallet_used"),
        "exchange_write_used": benchmark_payload.get("exchange_write_used"),
    }
