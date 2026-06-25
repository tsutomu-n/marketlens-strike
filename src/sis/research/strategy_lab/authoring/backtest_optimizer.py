from __future__ import annotations

import json
from itertools import product
from typing import Any, Literal, cast

from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
    _stable_digest,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _threshold_actual(summary: dict[str, Any], metric_name: str) -> float | int | None:
    aggregate_metrics = summary.get("aggregate_metrics")
    if isinstance(aggregate_metrics, dict) and metric_name in aggregate_metrics:
        value = aggregate_metrics.get(metric_name)
    else:
        current: Any = summary
        for part in metric_name.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        value = current
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    return None


def _threshold_passes(metric_name: str, actual: float | int | None, threshold: float) -> bool:
    if actual is None:
        return False
    if _metric_lower_is_better(metric_name):
        return float(actual) <= threshold
    return float(actual) >= threshold


def _metric_lower_is_better(metric_name: str) -> bool:
    lower_is_better = {
        "cost_drag_bps",
        "stale_rejected_count",
        "halt_rejected_count",
        "blocked_count",
        "no_signal_count",
        "entry_order_unfilled_count",
        "multi_leg_group_metrics.incomplete_group_count",
        "multi_leg_group_metrics.cost_drag_bps",
    }
    if metric_name in lower_is_better:
        return True
    leaf = metric_name.rsplit(".", maxsplit=1)[-1]
    lower_leaf_suffixes = (
        "_cost_bps",
        "_drag_bps",
        "_imbalance",
        "_imbalance_bps",
        "_rejected_count",
        "_blocked_count",
        "_unfilled_count",
    )
    return leaf.endswith(lower_leaf_suffixes) or leaf.startswith(("incomplete_", "rejected_"))


def _resolve_selection_direction(
    direction: str, metric_name: str
) -> Literal["maximize", "minimize"]:
    if direction == "auto":
        return "minimize" if _metric_lower_is_better(metric_name) else "maximize"
    if direction in {"maximize", "minimize"}:
        return cast(Literal["maximize", "minimize"], direction)
    raise StrategyAuthoringValidationError(f"unsupported selection_direction: {direction}")


def _evaluate_pass_thresholds(
    spec: StrategyAuthoringSpec, summary: dict[str, Any]
) -> dict[str, dict[str, float | int | bool | None]]:
    results: dict[str, dict[str, float | int | bool | None]] = {}
    for metric_name, threshold in spec.backtest.pass_thresholds.items():
        actual = _threshold_actual(summary, metric_name)
        results[metric_name] = {
            "actual": actual,
            "threshold": threshold,
            "passed": _threshold_passes(metric_name, actual, threshold),
        }
    return results


def _set_path(payload: dict[str, Any], dotted_path: str, value: float | int | str) -> None:
    current: dict[str, Any] = payload
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        next_item = current.setdefault(part, {})
        if not isinstance(next_item, dict):
            raise StrategyAuthoringValidationError(f"Cannot set optimizer path: {dotted_path}")
        current = next_item
    current[parts[-1]] = value


def _nested_get(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _optimizer_sort_value(item: dict[str, Any], metric_name: str, *, maximize: bool) -> float:
    value = _threshold_actual(item, metric_name)
    if value is None:
        return float("-inf") if maximize else float("inf")
    return float(value)


def _optimizer_variants(spec: StrategyAuthoringSpec) -> list[tuple[str, StrategyAuthoringSpec]]:
    sweep = spec.optimizer.parameter_sweep
    if not sweep:
        return []
    paths = sorted(sweep)
    combinations = list(product(*(sweep[path] for path in paths)))
    if len(combinations) > spec.optimizer.max_variants:
        raise StrategyAuthoringValidationError(
            f"optimizer variants exceed max_variants: {len(combinations)} > {spec.optimizer.max_variants}"
        )
    variants: list[tuple[str, StrategyAuthoringSpec]] = []
    base_payload = spec.model_dump(mode="json")
    for index, values in enumerate(combinations):
        payload = json.loads(json.dumps(base_payload))
        payload["optimizer"]["parameter_sweep"] = {}
        parameters = dict(zip(paths, values, strict=True))
        for path, value in parameters.items():
            _set_path(payload, path, value)
        variant = StrategyAuthoringSpec.model_validate(payload)
        variants.append((f"variant-{index:03d}-{_stable_digest(parameters)}", variant))
    return variants
