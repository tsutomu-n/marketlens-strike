from __future__ import annotations

from typing import Any, cast


def _numeric(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int | float) else None


def _threshold_failures(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        return []
    thresholds = summary.get("pass_thresholds")
    if not isinstance(thresholds, dict):
        return []
    failures: list[dict[str, Any]] = []
    for metric, result in sorted(thresholds.items()):
        if not isinstance(result, dict):
            continue
        result_payload = cast(dict[str, Any], result)
        if result_payload.get("passed") is not False:
            continue
        failures.append(
            {
                "metric": metric,
                "actual": _numeric(result_payload.get("actual")),
                "threshold": _numeric(result_payload.get("threshold")),
            }
        )
    return failures


def _weakest_eras(method_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eras: list[dict[str, Any]] = []
    for method in method_results:
        method_id = method.get("method_id")
        for era in method.get("eras") or []:
            if not isinstance(era, dict):
                continue
            metrics = era.get("metrics") if isinstance(era.get("metrics"), dict) else {}
            eras.append(
                {
                    "method_id": method_id,
                    "era": era.get("era"),
                    "trade_count": metrics.get("trade_count"),
                    "total_return": metrics.get("total_return"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "cost_drag_bps": metrics.get("cost_drag_bps"),
                }
            )
    return sorted(
        eras,
        key=lambda item: (
            float(item["total_return"]) if isinstance(item.get("total_return"), int | float) else 0
        ),
    )[:3]


def _suite_best_runs(suite_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_runs: list[dict[str, Any]] = []
    for suite in suite_results:
        best_run = suite.get("best_run")
        if not isinstance(best_run, dict):
            continue
        metrics = best_run.get("metrics") if isinstance(best_run.get("metrics"), dict) else {}
        best_runs.append(
            {
                "suite_id": suite.get("suite_id"),
                "run_id": best_run.get("run_id"),
                "case_id": best_run.get("case_id"),
                "method_id": best_run.get("method_id"),
                "strategy_id": best_run.get("strategy_id"),
                "backtest_passed": best_run.get("backtest_passed"),
                "trade_count": metrics.get("trade_count"),
                "total_return": metrics.get("total_return"),
                "max_drawdown": metrics.get("max_drawdown"),
                "cost_drag_bps": metrics.get("cost_drag_bps"),
            }
        )
    return best_runs


def _suite_failed_runs(suite_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed_runs: list[dict[str, Any]] = []
    for suite in suite_results:
        for run in suite.get("runs") or []:
            if not isinstance(run, dict) or run.get("backtest_passed") is not False:
                continue
            metrics = run.get("metrics") if isinstance(run.get("metrics"), dict) else {}
            failed_runs.append(
                {
                    "suite_id": suite.get("suite_id"),
                    "run_id": run.get("run_id"),
                    "case_id": run.get("case_id"),
                    "strategy_id": run.get("strategy_id"),
                    "trade_count": metrics.get("trade_count"),
                    "total_return": metrics.get("total_return"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "cost_drag_bps": metrics.get("cost_drag_bps"),
                }
            )
    return failed_runs


def comparison_diagnostics(
    *,
    metrics_payload: dict[str, Any],
    method_results: list[dict[str, Any]],
    suite_results: list[dict[str, Any]],
) -> dict[str, Any]:
    threshold_failures = _threshold_failures(metrics_payload)
    weakest_eras = _weakest_eras(method_results)
    suite_best_runs = _suite_best_runs(suite_results)
    suite_failed_runs = _suite_failed_runs(suite_results)
    notes: list[str] = []
    if threshold_failures:
        notes.append("THRESHOLD_FAILURES_PRESENT")
    if weakest_eras:
        notes.append("WEAKEST_ERAS_AVAILABLE")
    if suite_best_runs:
        notes.append("SUITE_BEST_RUN_AVAILABLE")
    if suite_failed_runs:
        notes.append("SUITE_FAILED_RUNS_PRESENT")
    if not notes:
        notes.append("NO_DIAGNOSTIC_FINDINGS")
    return {
        "threshold_failures": threshold_failures,
        "weakest_eras": weakest_eras,
        "suite_best_runs": suite_best_runs,
        "suite_failed_runs": suite_failed_runs,
        "diagnostic_notes": notes,
    }
