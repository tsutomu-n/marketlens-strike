from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import random
from typing import Any

from sis.research.strategy_lab.authoring.backtest import (
    _optimizer_sort_value,
    _resolve_selection_direction,
    run_authoring_backtest,
)
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.contracts.spec import (
    BacktestSuiteCase,
    StrategyAuthoringSpec,
    StrategyBacktestSuiteSpec,
)
from sis.research.strategy_lab.authoring.io import load_authoring_spec


def _resolve_member_spec_path(raw: str, suite_path: Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else suite_path.parent / path


def _apply_backtest_case(
    spec: StrategyAuthoringSpec, case: BacktestSuiteCase
) -> StrategyAuthoringSpec:
    overrides = case.backtest.model_dump(mode="json", exclude_none=True)
    if not overrides:
        return spec
    payload = spec.model_dump(mode="json")
    payload["backtest"] = {**payload["backtest"], **overrides}
    return StrategyAuthoringSpec.model_validate(payload)


def _aggregate_suite_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_count": len(runs),
        "strategy_count": len({run["strategy_id"] for run in runs}),
        "case_count": len({run["case_id"] for run in runs}),
        "passed_count": sum(1 for run in runs if run["summary"].get("backtest_passed") is True),
        "failed_count": sum(1 for run in runs if run["summary"].get("backtest_passed") is False),
        "trade_count": sum(
            int(run["summary"].get("aggregate_metrics", {}).get("trade_count") or 0) for run in runs
        ),
        "total_return": sum(
            float(run["summary"].get("aggregate_metrics", {}).get("total_return") or 0.0)
            for run in runs
        ),
        "cost_drag_bps": sum(
            float(run["summary"].get("aggregate_metrics", {}).get("cost_drag_bps") or 0.0)
            for run in runs
        ),
    }


def _suite_run_method(backtest: dict[str, Any]) -> dict[str, str | None]:
    split_method = str(backtest.get("split_method") or "single_window")
    era_unit = backtest.get("era_unit")
    era_unit_text = str(era_unit) if era_unit is not None else None
    if split_method in {"walk_forward", "purged_walk_forward"}:
        method_id = f"{split_method}:{era_unit_text or 'unspecified'}"
        method_type = "walk_forward"
    elif split_method == "single_window":
        method_id = "single_window"
        method_type = "single_window"
        era_unit_text = None
    else:
        method_id = split_method
        method_type = split_method
    return {
        "method_id": method_id,
        "method_type": method_type,
        "split_method": split_method,
        "era_unit": era_unit_text,
    }


def _resampling_payload(case: BacktestSuiteCase, summary: dict[str, Any]) -> dict[str, Any]:
    method = case.resampling.method
    base = {
        "method": method,
        "iterations": case.resampling.iterations,
        "seed": case.resampling.seed,
        "block_size": case.resampling.block_size,
        "status": "not_requested",
    }
    if method == "none":
        return base

    returns = _executed_signal_returns(summary)
    if not returns:
        return {
            **base,
            "status": "skipped",
            "reason_codes": ["no_executed_signal_returns"],
            "source_result_count": 0,
        }

    rng = random.Random(case.resampling.seed)
    totals = [
        _compound_total_return(
            _resampled_returns(
                returns,
                method=method,
                block_size=case.resampling.block_size,
                rng=rng,
            )
        )
        for _ in range(case.resampling.iterations)
    ]
    sorted_totals = sorted(totals)
    return {
        **base,
        "status": "completed",
        "reason_codes": [],
        "source_result_count": len(returns),
        "sample_size": len(returns),
        "iteration_count": case.resampling.iterations,
        "total_return_min": sorted_totals[0],
        "total_return_p05": _quantile(sorted_totals, 0.05),
        "total_return_p50": _quantile(sorted_totals, 0.50),
        "total_return_p95": _quantile(sorted_totals, 0.95),
        "total_return_max": sorted_totals[-1],
        "positive_total_return_rate": sum(1 for item in totals if item > 0) / len(totals),
    }


def _executed_signal_returns(summary: dict[str, Any]) -> list[float]:
    results = summary.get("executed_signal_results")
    if not isinstance(results, list):
        return []
    returns: list[float] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        value = item.get("signal_return")
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            returns.append(float(value))
    return returns


def _resampled_returns(
    returns: list[float],
    *,
    method: str,
    block_size: int,
    rng: random.Random,
) -> list[float]:
    if method == "return_bootstrap":
        return [rng.choice(returns) for _ in returns]
    if method == "block_bootstrap":
        sample: list[float] = []
        while len(sample) < len(returns):
            start = rng.randrange(0, len(returns))
            for offset in range(block_size):
                sample.append(returns[(start + offset) % len(returns)])
                if len(sample) >= len(returns):
                    break
        return sample
    raise ValueError(f"unsupported resampling method: {method}")


def _compound_total_return(returns: list[float]) -> float:
    equity = 1.0
    for item in returns:
        equity *= 1.0 + item
    return equity - 1.0


def _quantile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute quantile for empty values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _method_with_resampling(
    method: dict[str, str | None], case: BacktestSuiteCase
) -> dict[str, str | None]:
    if case.resampling.method == "none":
        return method
    return {
        **method,
        "base_method_id": method["method_id"],
        "method_id": f"{method['method_id']}+{case.resampling.method}",
        "method_type": "resampling",
        "resampling_method": case.resampling.method,
    }


def _method_matrix(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_method: dict[str, dict[str, Any]] = {}
    for run in runs:
        method_id = str(run["method_id"])
        entry = by_method.setdefault(
            method_id,
            {
                "method_id": method_id,
                "method_type": run.get("method_type"),
                "base_method_id": run.get("base_method_id"),
                "resampling_method": run.get("resampling", {}).get("method"),
                "split_method": run.get("backtest", {}).get("split_method"),
                "era_unit": None
                if method_id == "single_window"
                else run.get("backtest", {}).get("era_unit"),
                "case_ids": [],
                "run_count": 0,
                "passed_count": 0,
                "failed_count": 0,
            },
        )
        if run["case_id"] not in entry["case_ids"]:
            entry["case_ids"].append(run["case_id"])
        entry["run_count"] += 1
        if run["summary"].get("backtest_passed") is True:
            entry["passed_count"] += 1
        elif run["summary"].get("backtest_passed") is False:
            entry["failed_count"] += 1
    methods = sorted(by_method.values(), key=lambda item: str(item["method_id"]))
    return {
        "method_count": len(methods),
        "counts_by_method": {str(method["method_id"]): method["run_count"] for method in methods},
        "methods": methods,
    }


def run_backtest_suite(
    suite: StrategyBacktestSuiteSpec, *, suite_path: Path, data_dir: Path
) -> dict[str, Any]:
    enabled_cases = [case for case in suite.cases if case.enabled]
    case_by_id = {case.case_id: case for case in enabled_cases}
    runs: list[dict[str, Any]] = []
    for member_index, member in enumerate(suite.members):
        if not member.enabled:
            continue
        spec_path = _resolve_member_spec_path(member.spec_path, suite_path)
        base_spec = load_authoring_spec(spec_path)
        selected_case_ids = member.case_ids or [case.case_id for case in enabled_cases]
        for case_id in selected_case_ids:
            case = case_by_id.get(case_id)
            if case is None:
                continue
            spec = _apply_backtest_case(base_spec, case)
            frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
            _metrics, summary = run_authoring_backtest(spec, frame, data_dir=data_dir)
            resampling = _resampling_payload(case, summary)
            if resampling["status"] != "not_requested":
                summary["resampling"] = resampling
            method = _method_with_resampling(
                _suite_run_method(spec.backtest.model_dump(mode="json")),
                case,
            )
            runs.append(
                {
                    "run_id": f"{member_index:03d}-{case.case_id}",
                    "member_index": member_index,
                    "case_id": case.case_id,
                    "spec_path": str(spec_path),
                    "strategy_id": spec.experiment.strategy_id,
                    "signal_count": frame.height,
                    "method_id": method["method_id"],
                    "method_type": method["method_type"],
                    "base_method_id": method.get("base_method_id"),
                    "resampling": resampling,
                    "backtest": spec.backtest.model_dump(mode="json"),
                    "summary": summary,
                }
            )

    resolved_direction = _resolve_selection_direction(
        suite.selection_direction, suite.selection_metric
    )
    reverse = resolved_direction == "maximize"
    ranked_runs = sorted(
        runs,
        key=lambda item: _optimizer_sort_value(
            item["summary"],
            suite.selection_metric,
            maximize=reverse,
        ),
        reverse=reverse,
    )
    return {
        "schema_version": "strategy_backtest_suite_result.v1",
        "suite_id": suite.suite_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "selection": {
            "metric": suite.selection_metric,
            "direction": suite.selection_direction,
            "resolved_direction": resolved_direction,
        },
        "aggregate": _aggregate_suite_runs(ranked_runs),
        "method_matrix": _method_matrix(ranked_runs),
        "best_run": ranked_runs[0] if ranked_runs else None,
        "runs": ranked_runs,
    }


def write_backtest_suite_outputs(payload: dict[str, Any], *, data_dir: Path) -> dict[str, Path]:
    result_path = data_dir / "research/backtest_suite/strategy_backtest_suite_result.json"
    report_path = data_dir / "reports/strategy_backtest_suite_report.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    rows = "\n".join(
        "| {case_id} | {method_id} | {strategy_id} | {trades} | {total_return:.6f} | {drawdown} | {passed} |".format(
            case_id=run["case_id"],
            method_id=run["method_id"],
            strategy_id=run["strategy_id"],
            trades=int(run["summary"].get("aggregate_metrics", {}).get("trade_count") or 0),
            total_return=float(
                run["summary"].get("aggregate_metrics", {}).get("total_return") or 0.0
            ),
            drawdown=run["summary"].get("aggregate_metrics", {}).get("max_drawdown"),
            passed=run["summary"].get("backtest_passed"),
        )
        for run in payload["runs"]
    )
    best_run = payload.get("best_run") or {}
    report_path.write_text(
        "# Strategy Backtest Suite Report\n\n"
        "paper_only: true\n\n"
        f"- suite_id: {payload['suite_id']}\n"
        f"- run_count: {payload['aggregate']['run_count']}\n"
        f"- passed_count: {payload['aggregate']['passed_count']}\n"
        f"- method_count: {payload['method_matrix']['method_count']}\n"
        f"- selection_metric: {payload['selection']['metric']}\n"
        f"- resolved_selection_direction: {payload['selection']['resolved_direction']}\n"
        f"- best_run_id: {best_run.get('run_id')}\n"
        f"- permits_live_order: {payload['permits_live_order']}\n"
        f"- wallet_used: {payload['wallet_used']}\n"
        f"- exchange_write_used: {payload['exchange_write_used']}\n\n"
        "| Case | Method | Strategy | Trades | Total Return | Max Drawdown | Passed |\n"
        "|---|---|---|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"suite_result": result_path, "suite_report": report_path}
