from __future__ import annotations

from sis.backtest.compare_quality_results import (
    benchmark_relative,
    regime_split,
    rolling_stability,
    stress,
)


def test_quality_result_helpers_return_none_for_missing_payloads() -> None:
    assert stress(None) is None
    assert regime_split(None) is None
    assert rolling_stability(None) is None
    assert benchmark_relative(None) is None


def test_stress_normalizes_summary_scenarios_and_boundaries() -> None:
    assert stress(
        {
            "stress_kind": "cost_slippage",
            "scenario_count": 2,
            "summary": "not-a-dict",
            "scenarios": [{"id": "wide_spread"}],
            "dependency_added": False,
            "paper_only": True,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "stress_kind": "cost_slippage",
        "scenario_count": 2,
        "summary": {},
        "scenarios": [{"id": "wide_spread"}],
        "dependency_added": False,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def test_regime_split_normalizes_summary_dimensions_and_boundaries() -> None:
    assert regime_split(
        {
            "split_kind": "volatility",
            "dimension_count": 3,
            "summary": {"worst_dimension": "high_vol"},
            "dimensions": None,
            "dependency_added": False,
            "paper_only": True,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "split_kind": "volatility",
        "dimension_count": 3,
        "summary": {"worst_dimension": "high_vol"},
        "dimensions": [],
        "dependency_added": False,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def test_rolling_stability_normalizes_summary_windows_and_boundaries() -> None:
    assert rolling_stability(
        {
            "stability_kind": "rolling_window",
            "window_count": 4,
            "summary": "not-a-dict",
            "windows": [{"window_id": "w1"}],
            "dependency_added": False,
            "paper_only": True,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "stability_kind": "rolling_window",
        "window_count": 4,
        "summary": {},
        "windows": [{"window_id": "w1"}],
        "dependency_added": False,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def test_benchmark_relative_normalizes_comparison_fields_and_boundaries() -> None:
    assert benchmark_relative(
        {
            "comparison_kind": "relative_return",
            "benchmark_return_column": "spy_return",
            "benchmark_series_return_column": "benchmark_return",
            "price_column": "close",
            "horizon_minutes": 240,
            "summary": {"alpha": 0.02},
            "comparisons": None,
            "dependency_added": False,
            "paper_only": True,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "comparison_kind": "relative_return",
        "benchmark_return_column": "spy_return",
        "benchmark_series_return_column": "benchmark_return",
        "price_column": "close",
        "horizon_minutes": 240,
        "summary": {"alpha": 0.02},
        "comparisons": [],
        "dependency_added": False,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
