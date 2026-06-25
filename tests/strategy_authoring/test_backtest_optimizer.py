from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from sis.research.strategy_lab.authoring.backtest_optimizer import (
    _evaluate_pass_thresholds,
    _nested_get,
    _optimizer_sort_value,
    _resolve_selection_direction,
    _set_path,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def test_backtest_optimizer_resolves_auto_direction_for_lower_cost_metrics() -> None:
    assert _resolve_selection_direction("auto", "aggregate_metrics.total_return") == "maximize"
    assert _resolve_selection_direction("auto", "cost_drag_bps") == "minimize"
    assert (
        _resolve_selection_direction("auto", "multi_leg_group_metrics.incomplete_group_count")
        == "minimize"
    )
    assert _resolve_selection_direction("minimize", "total_return") == "minimize"
    assert _resolve_selection_direction("maximize", "cost_drag_bps") == "maximize"

    with pytest.raises(StrategyAuthoringValidationError, match="unsupported selection_direction"):
        _resolve_selection_direction("median", "total_return")


def test_backtest_optimizer_evaluates_nested_thresholds_with_direction_heuristics() -> None:
    spec = cast(
        StrategyAuthoringSpec,
        SimpleNamespace(
            backtest=SimpleNamespace(
                pass_thresholds={
                    "aggregate_metrics.total_return": 0.05,
                    "aggregate_metrics.cost_drag_bps": 1.0,
                    "multi_leg_group_metrics.incomplete_group_count": 0.0,
                    "missing_metric": 1.0,
                }
            )
        ),
    )
    summary: dict[str, Any] = {
        "aggregate_metrics": {
            "total_return": 0.06,
            "cost_drag_bps": 1.2,
        },
        "multi_leg_group_metrics": {
            "incomplete_group_count": 0,
        },
    }

    results = _evaluate_pass_thresholds(spec, summary)

    assert results["aggregate_metrics.total_return"] == {
        "actual": 0.06,
        "threshold": 0.05,
        "passed": True,
    }
    assert results["aggregate_metrics.cost_drag_bps"] == {
        "actual": 1.2,
        "threshold": 1.0,
        "passed": False,
    }
    assert results["multi_leg_group_metrics.incomplete_group_count"] == {
        "actual": 0,
        "threshold": 0.0,
        "passed": True,
    }
    assert results["missing_metric"] == {
        "actual": None,
        "threshold": 1.0,
        "passed": False,
    }


def test_backtest_optimizer_sets_and_reads_dotted_paths() -> None:
    payload: dict[str, Any] = {}

    _set_path(payload, "rules.entry_score_threshold", 0.72)

    assert payload == {"rules": {"entry_score_threshold": 0.72}}
    assert _nested_get(payload, "rules.entry_score_threshold") == 0.72
    assert _nested_get(payload, "rules.missing") is None


def test_backtest_optimizer_rejects_dotted_path_through_scalar() -> None:
    payload: dict[str, Any] = {"rules": 1}

    with pytest.raises(StrategyAuthoringValidationError, match="Cannot set optimizer path"):
        _set_path(payload, "rules.entry_score_threshold", 0.72)


def test_backtest_optimizer_sort_value_uses_missing_metric_sentinels() -> None:
    item = {"aggregate_metrics": {"total_return": 0.12}}

    assert _optimizer_sort_value(item, "aggregate_metrics.total_return", maximize=True) == 0.12
    assert _optimizer_sort_value(item, "missing", maximize=True) == float("-inf")
    assert _optimizer_sort_value(item, "missing", maximize=False) == float("inf")
