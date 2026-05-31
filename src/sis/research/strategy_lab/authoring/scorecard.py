from __future__ import annotations

from dataclasses import asdict
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.contracts import StrategyAuthoringSpec


def _metrics_json(
    metrics: list[Any], summary: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_authoring_backtest_result.v1",
        "strategy_id": spec.experiment.strategy_id,
        "paper_only": True,
        "live_order_submitted": False,
        "summary": summary,
        "metrics": [asdict(item) for item in metrics],
    }


def _increment_count(counts: dict[str, int], raw: object) -> None:
    key = str(raw)
    if not key:
        return
    counts[key] = counts.get(key, 0) + 1


def _count_values(rows: list[dict[str, Any]], column: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(column)
        if isinstance(value, list):
            for item in value:
                _increment_count(counts, item)
        elif value is not None:
            _increment_count(counts, value)
    return dict(sorted(counts.items()))


def _compact_multi_leg_group_metrics(summary: dict[str, Any]) -> dict[str, Any] | None:
    metrics = summary.get("multi_leg_group_metrics")
    if not isinstance(metrics, dict):
        return None
    keys = (
        "group_count",
        "executed_group_count",
        "complete_group_count",
        "incomplete_group_count",
        "expected_leg_count",
        "executed_leg_count",
        "total_return",
        "avg_group_return",
        "win_rate",
        "worst_group_return",
        "max_drawdown",
        "profit_factor",
        "avg_leg_return_imbalance",
        "total_notional_usd",
        "notional_weighted_total_return",
        "cost_drag_bps",
    )
    return {key: metrics[key] for key in keys if key in metrics}


def _strategy_scorecard(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, summary: dict[str, Any]
) -> dict[str, Any]:
    rows = frame.to_dicts() if not frame.is_empty() else []
    derived_feature_ops: dict[str, int] = {}
    for feature in spec.rules.derived_features:
        derived_feature_ops[feature.op] = derived_feature_ops.get(feature.op, 0) + 1
    pass_thresholds = summary.get("pass_thresholds", {})
    failed_thresholds = [
        name
        for name, result in pass_thresholds.items()
        if isinstance(result, dict) and not bool(result.get("passed"))
    ]
    passed_thresholds = [
        name
        for name, result in pass_thresholds.items()
        if isinstance(result, dict) and bool(result.get("passed"))
    ]
    scorecard = {
        "schema_version": "strategy_authoring_scorecard.v1",
        "derived_feature_count": len(spec.rules.derived_features),
        "derived_feature_names": [feature.name for feature in spec.rules.derived_features],
        "derived_feature_ops": dict(sorted(derived_feature_ops.items())),
        "signal_count": frame.height,
        "side_counts": _count_values(rows, "side"),
        "reason_code_counts": _count_values(rows, "reason_codes"),
        "block_reason_counts": _count_values(rows, "block_reasons"),
        "execution_block_reason_counts": dict(
            sorted((summary.get("blocked_reason_counts") or {}).items())
        ),
        "exit_reason_counts": dict(sorted((summary.get("exit_reason_counts") or {}).items())),
        "passed_thresholds": sorted(passed_thresholds),
        "failed_thresholds": sorted(failed_thresholds),
        "backtest_passed": bool(summary.get("backtest_passed")),
        "paper_only": True,
        "live_order_submitted": False,
    }
    compact_group_metrics = _compact_multi_leg_group_metrics(summary)
    if compact_group_metrics is not None:
        scorecard["multi_leg_group_metrics"] = compact_group_metrics
    return scorecard


def _paper_preview_scorecard_summary(summary: dict[str, Any]) -> dict[str, Any]:
    scorecard = summary.get("strategy_scorecard")
    if not isinstance(scorecard, dict):
        return {}
    keys = (
        "schema_version",
        "derived_feature_count",
        "signal_count",
        "side_counts",
        "block_reason_counts",
        "execution_block_reason_counts",
        "exit_reason_counts",
        "passed_thresholds",
        "failed_thresholds",
        "backtest_passed",
        "paper_only",
        "live_order_submitted",
        "multi_leg_group_metrics",
    )
    return {key: scorecard[key] for key in keys if key in scorecard}
