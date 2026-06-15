from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from sis.backtest.frameworks import framework_adapter_status


@dataclass(frozen=True)
class BacktestComparisonResult:
    comparison_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _native_result(metrics_payload: dict[str, Any]) -> dict[str, Any]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    aggregate = summary.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    executed_summary = summary.get("executed_signal_summary")
    if not isinstance(executed_summary, dict):
        executed_summary = {}
    capital = summary.get("capital")
    if not isinstance(capital, dict):
        capital = {}
    return {
        "engine_id": "strategy_authoring_native",
        "strategy_id": metrics_payload.get("strategy_id"),
        "schema_version": metrics_payload.get("schema_version"),
        "backtest_passed": summary.get("backtest_passed"),
        "signals_considered": summary.get("signals_considered"),
        "executed_count": summary.get("executed_count"),
        "blocked_count": summary.get("blocked_count"),
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "win_rate": executed_summary.get("win_rate"),
        "avg_signal_return": executed_summary.get("avg_signal_return"),
        "total_notional_usd": executed_summary.get("total_notional_usd"),
        "capital": _capital(capital),
    }


def _capital(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "initial_capital_usd": payload.get("initial_capital_usd"),
        "net_pnl_usd": payload.get("net_pnl_usd"),
        "ending_equity_usd": payload.get("ending_equity_usd"),
        "max_drawdown_loss_usd": payload.get("max_drawdown_loss_usd"),
    }


def _aggregate_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    aggregate = summary.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    return {
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "stale_rejected_count": aggregate.get("stale_rejected_count"),
        "halt_rejected_count": aggregate.get("halt_rejected_count"),
    }


def _variant_metrics(variant: dict[str, Any]) -> dict[str, Any]:
    aggregate = variant.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    return {
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "stale_rejected_count": aggregate.get("stale_rejected_count"),
        "halt_rejected_count": aggregate.get("halt_rejected_count"),
    }


def _summary_capital(summary: dict[str, Any]) -> dict[str, Any]:
    capital = summary.get("capital")
    return _capital(capital) if isinstance(capital, dict) else _capital({})


def _method_results(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")

    results: list[dict[str, Any]] = [
        {
            "method_id": "strategy_authoring_native_overall",
            "method_type": "native_overall",
            "engine_id": "strategy_authoring_native",
            "status": "available",
            "backtest_passed": summary.get("backtest_passed"),
            "split_method": summary.get("authoring_split_method"),
            "era_unit": summary.get("authoring_era_unit"),
            "signals_considered": summary.get("signals_considered"),
            "executed_count": summary.get("executed_count"),
            "blocked_count": summary.get("blocked_count"),
            "capital": _summary_capital(summary),
            "metrics": _aggregate_metrics(summary),
        }
    ]

    eras = summary.get("walk_forward_eras")
    if isinstance(eras, list) and eras:
        normalized_eras = [
            {
                "era": era.get("era"),
                "signal_count": era.get("signal_count"),
                "executed_count": era.get("executed_count"),
                "capital": _summary_capital(era),
                "metrics": _aggregate_metrics(era),
            }
            for era in eras
            if isinstance(era, dict)
        ]
        results.append(
            {
                "method_id": "strategy_authoring_walk_forward",
                "method_type": "walk_forward",
                "engine_id": "strategy_authoring_native",
                "status": "available",
                "backtest_passed": summary.get("backtest_passed"),
                "split_method": summary.get("authoring_split_method"),
                "era_unit": summary.get("authoring_era_unit"),
                "era_count": len(normalized_eras),
                "eras": normalized_eras,
                "metrics": _aggregate_metrics(summary),
            }
        )

    optimizer = summary.get("optimizer")
    if isinstance(optimizer, dict):
        variants = [
            {
                "variant_id": variant.get("variant_id"),
                "parameters": variant.get("parameters") if isinstance(variant, dict) else {},
                "backtest_passed": variant.get("backtest_passed"),
                "capital": _summary_capital(variant),
                "metrics": _variant_metrics(variant),
            }
            for variant in optimizer.get("variants") or []
            if isinstance(variant, dict)
        ]
        best_variant = optimizer.get("best_variant")
        normalized_best = (
            {
                "variant_id": best_variant.get("variant_id"),
                "parameters": best_variant.get("parameters"),
                "backtest_passed": best_variant.get("backtest_passed"),
                "capital": _summary_capital(best_variant),
                "metrics": _variant_metrics(best_variant),
            }
            if isinstance(best_variant, dict)
            else None
        )
        results.append(
            {
                "method_id": "strategy_authoring_optimizer_sweep",
                "method_type": "parameter_sweep",
                "engine_id": "strategy_authoring_native",
                "status": "available",
                "selection_metric": optimizer.get("selection_metric"),
                "selection_direction": optimizer.get("selection_direction"),
                "resolved_selection_direction": optimizer.get("resolved_selection_direction"),
                "variant_count": optimizer.get("variant_count"),
                "best_variant": normalized_best,
                "variants": variants,
                "metrics": _aggregate_metrics(summary),
            }
        )

    return results


def _suite_run_metrics(run: dict[str, Any]) -> dict[str, Any]:
    summary = run.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return _aggregate_metrics(summary)


def _suite_run(run: dict[str, Any]) -> dict[str, Any]:
    backtest = run.get("backtest")
    if not isinstance(backtest, dict):
        backtest = {}
    summary = run.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "run_id": run.get("run_id"),
        "case_id": run.get("case_id"),
        "strategy_id": run.get("strategy_id"),
        "signal_count": run.get("signal_count"),
        "source_signal_count": run.get("source_signal_count"),
        "evaluation_signal_count": run.get("evaluation_signal_count"),
        "method_id": run.get("method_id"),
        "method_type": run.get("method_type"),
        "base_method_id": run.get("base_method_id"),
        "resampling": run.get("resampling") if isinstance(run.get("resampling"), dict) else None,
        "backtest_passed": summary.get("backtest_passed"),
        "split_method": backtest.get("split_method"),
        "era_unit": backtest.get("era_unit"),
        "label_horizon_minutes": backtest.get("label_horizon_minutes"),
        "initial_capital_usd": backtest.get("initial_capital_usd"),
        "evaluation_start_at": backtest.get("evaluation_start_at"),
        "evaluation_end_at": backtest.get("evaluation_end_at"),
        "capital": _summary_capital(summary),
        "metrics": _suite_run_metrics(run),
    }


def _suite_results(suite_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if suite_payload is None:
        return []
    best_run = suite_payload.get("best_run")
    runs = [run for run in suite_payload.get("runs") or [] if isinstance(run, dict)]
    return [
        {
            "suite_id": suite_payload.get("suite_id"),
            "schema_version": suite_payload.get("schema_version"),
            "selection": suite_payload.get("selection") or {},
            "aggregate": suite_payload.get("aggregate") or {},
            "method_matrix": suite_payload.get("method_matrix") or {},
            "best_run": _suite_run(best_run) if isinstance(best_run, dict) else None,
            "runs": [_suite_run(run) for run in runs],
            "permits_live_order": suite_payload.get("permits_live_order"),
            "live_conversion_allowed": suite_payload.get("live_conversion_allowed"),
            "wallet_used": suite_payload.get("wallet_used"),
            "exchange_write_used": suite_payload.get("exchange_write_used"),
        }
    ]


def _adapter_spike(spike_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if spike_payload is None:
        return None
    candidates = [
        {
            "framework_id": candidate.get("framework_id"),
            "adapter_role": candidate.get("adapter_role"),
            "status": candidate.get("status"),
            "version": candidate.get("version"),
            "adoption_status": candidate.get("adoption_status"),
            "adoption_blockers": candidate.get("adoption_blockers") or [],
            "dependency_added": candidate.get("dependency_added"),
            "engine_run": candidate.get("engine_run"),
            "permits_live_order": candidate.get("permits_live_order"),
            "wallet_used": candidate.get("wallet_used"),
            "exchange_write_used": candidate.get("exchange_write_used"),
        }
        for candidate in spike_payload.get("candidates") or []
        if isinstance(candidate, dict)
    ]
    return {
        "schema_version": spike_payload.get("schema_version"),
        "created_at": spike_payload.get("created_at"),
        "dependency_added": spike_payload.get("dependency_added"),
        "external_engine_run": spike_payload.get("external_engine_run"),
        "permits_live_order": spike_payload.get("permits_live_order"),
        "live_conversion_allowed": spike_payload.get("live_conversion_allowed"),
        "wallet_used": spike_payload.get("wallet_used"),
        "exchange_write_used": spike_payload.get("exchange_write_used"),
        "decision": spike_payload.get("decision") or {},
        "candidates": candidates,
    }


def _external_results(external_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if external_payload is None:
        return []
    return [
        {
            "framework_id": result.get("framework_id"),
            "adapter_role": result.get("adapter_role"),
            "status": result.get("status"),
            "framework_version": result.get("framework_version"),
            "runner_mode": result.get("runner_mode"),
            "run_status": result.get("run_status"),
            "reason_codes": result.get("reason_codes") or [],
            "dependency_added": result.get("dependency_added"),
            "engine_run": result.get("engine_run"),
            "permits_live_order": result.get("permits_live_order"),
            "wallet_used": result.get("wallet_used"),
            "exchange_write_used": result.get("exchange_write_used"),
            "metrics": result.get("metrics") or {},
        }
        for result in external_payload.get("results") or []
        if isinstance(result, dict)
    ]


def _framework_run(framework_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if framework_payload is None:
        return None
    summary = framework_payload.get("summary")
    runs = [
        {
            "framework_id": run.get("framework_id"),
            "surface_type": run.get("surface_type"),
            "status": run.get("status"),
            "run_status": run.get("run_status"),
            "reason_codes": run.get("reason_codes") or [],
            "dependency_source": run.get("dependency_source"),
            "artifact": run.get("artifact") if isinstance(run.get("artifact"), dict) else None,
            "report": run.get("report") if isinstance(run.get("report"), dict) else None,
            "boundary": run.get("boundary") if isinstance(run.get("boundary"), dict) else {},
        }
        for run in framework_payload.get("runs") or []
        if isinstance(run, dict)
    ]
    return {
        "schema_version": framework_payload.get("schema_version"),
        "created_at": framework_payload.get("created_at"),
        "selected_frameworks": framework_payload.get("selected_frameworks") or [],
        "summary": summary if isinstance(summary, dict) else {},
        "dependency_added": framework_payload.get("dependency_added"),
        "permits_live_order": framework_payload.get("permits_live_order"),
        "live_conversion_allowed": framework_payload.get("live_conversion_allowed"),
        "wallet_used": framework_payload.get("wallet_used"),
        "exchange_write_used": framework_payload.get("exchange_write_used"),
        "runs": runs,
    }


def _portfolio_comparison(portfolio_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if portfolio_payload is None:
        return None
    return {
        "framework_id": portfolio_payload.get("framework_id"),
        "adapter_role": portfolio_payload.get("adapter_role"),
        "framework_version": portfolio_payload.get("framework_version"),
        "runner_mode": portfolio_payload.get("runner_mode"),
        "dependency_source": portfolio_payload.get("dependency_source"),
        "run_status": portfolio_payload.get("run_status"),
        "reason_codes": portfolio_payload.get("reason_codes") or [],
        "dependency_added": portfolio_payload.get("dependency_added"),
        "engine_run": portfolio_payload.get("engine_run"),
        "allocation_rule_id": portfolio_payload.get("allocation_rule_id"),
        "rebalance_cadence": portfolio_payload.get("rebalance_cadence"),
        "portfolio_return": portfolio_payload.get("portfolio_return"),
        "max_drawdown": portfolio_payload.get("max_drawdown"),
        "turnover": portfolio_payload.get("turnover"),
        "rebalance_count": portfolio_payload.get("rebalance_count"),
        "permits_live_order": portfolio_payload.get("permits_live_order"),
        "wallet_used": portfolio_payload.get("wallet_used"),
        "exchange_write_used": portfolio_payload.get("exchange_write_used"),
    }


def _metric_extension(metric_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if metric_payload is None:
        return None
    return {
        "framework_id": metric_payload.get("framework_id"),
        "adapter_role": metric_payload.get("adapter_role"),
        "framework_version": metric_payload.get("framework_version"),
        "runner_mode": metric_payload.get("runner_mode"),
        "dependency_source": metric_payload.get("dependency_source"),
        "metric_status": metric_payload.get("metric_status"),
        "reason_codes": metric_payload.get("reason_codes") or [],
        "dependency_added": metric_payload.get("dependency_added"),
        "engine_run": metric_payload.get("engine_run"),
        "frequency": metric_payload.get("frequency"),
        "risk_free_rate": metric_payload.get("risk_free_rate"),
        "return_count": metric_payload.get("return_count"),
        "sharpe_ratio": metric_payload.get("sharpe_ratio"),
        "sortino_ratio": metric_payload.get("sortino_ratio"),
        "max_drawdown": metric_payload.get("max_drawdown"),
        "annual_return": metric_payload.get("annual_return"),
        "annual_volatility": metric_payload.get("annual_volatility"),
        "calmar_ratio": metric_payload.get("calmar_ratio"),
        "omega_ratio": metric_payload.get("omega_ratio"),
        "permits_live_order": metric_payload.get("permits_live_order"),
        "wallet_used": metric_payload.get("wallet_used"),
        "exchange_write_used": metric_payload.get("exchange_write_used"),
    }


def _report_extension(report_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if report_payload is None:
        return None
    return {
        "framework_id": report_payload.get("framework_id"),
        "adapter_role": report_payload.get("adapter_role"),
        "framework_version": report_payload.get("framework_version"),
        "runner_mode": report_payload.get("runner_mode"),
        "dependency_source": report_payload.get("dependency_source"),
        "report_status": report_payload.get("report_status"),
        "reason_codes": report_payload.get("reason_codes") or [],
        "dependency_added": report_payload.get("dependency_added"),
        "engine_run": report_payload.get("engine_run"),
        "frequency": report_payload.get("frequency"),
        "risk_free_rate": report_payload.get("risk_free_rate"),
        "periods_per_year": report_payload.get("periods_per_year"),
        "return_count": report_payload.get("return_count"),
        "metrics_table_row_count": report_payload.get("metrics_table_row_count"),
        "quantstats_html_path": report_payload.get("quantstats_html_path"),
        "quantstats_html_hash": report_payload.get("quantstats_html_hash"),
        "permits_live_order": report_payload.get("permits_live_order"),
        "wallet_used": report_payload.get("wallet_used"),
        "exchange_write_used": report_payload.get("exchange_write_used"),
    }


def _stress(stress_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def _regime_split(regime_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def _rolling_stability(rolling_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def _benchmark_relative(benchmark_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def _completion_artifact(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    summary = payload.get("summary")
    return {
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "summary": summary if isinstance(summary, dict) else {},
        "dependency_added": payload.get("dependency_added"),
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "live_conversion_allowed": payload.get("live_conversion_allowed"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


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


def _comparison_diagnostics(
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


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    native = payload["native_result"]
    lines = [
        "# Strategy Backtest Comparison",
        "",
        f"- comparison_id: {payload['comparison_id']}",
        f"- source_metrics_path: `{payload['source_metrics_path']}`",
        f"- native_engine: {native['engine_id']}",
        f"- strategy_id: {native.get('strategy_id')}",
        f"- backtest_passed: {native.get('backtest_passed')}",
        f"- trade_count: {native.get('trade_count')}",
        f"- total_return: {native.get('total_return')}",
        f"- max_drawdown: {native.get('max_drawdown')}",
        f"- cost_drag_bps: {native.get('cost_drag_bps')}",
        f"- initial_capital_usd: {native.get('capital', {}).get('initial_capital_usd')}",
        f"- net_pnl_usd: {native.get('capital', {}).get('net_pnl_usd')}",
        f"- ending_equity_usd: {native.get('capital', {}).get('ending_equity_usd')}",
        f"- max_drawdown_loss_usd: {native.get('capital', {}).get('max_drawdown_loss_usd')}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "## Backtest Method Results",
        "",
        "| Method | Type | Status | Trades | Total Return | Max Drawdown |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for method in payload["method_results"]:
        metrics = method.get("metrics") or {}
        lines.append(
            "| {method_id} | {method_type} | {status} | {trade_count} | {total_return} | {max_drawdown} |".format(
                method_id=method["method_id"],
                method_type=method["method_type"],
                status=method["status"],
                trade_count=metrics.get("trade_count"),
                total_return=metrics.get("total_return"),
                max_drawdown=metrics.get("max_drawdown"),
            )
        )
    lines.extend(
        [
            "",
            "## Backtest Suite Results",
            "",
            "| Suite | Runs | Passed | Best Case | Best Strategy | Best Total Return |",
            "|---|---:|---:|---|---|---:|",
        ]
    )
    if payload["suite_results"]:
        for suite in payload["suite_results"]:
            aggregate = suite.get("aggregate") or {}
            best_run = suite.get("best_run") or {}
            best_metrics = best_run.get("metrics") or {}
            lines.append(
                "| {suite_id} | {run_count} | {passed_count} | {case_id} | {strategy_id} | {total_return} |".format(
                    suite_id=suite.get("suite_id"),
                    run_count=aggregate.get("run_count"),
                    passed_count=aggregate.get("passed_count"),
                    case_id=best_run.get("case_id"),
                    strategy_id=best_run.get("strategy_id"),
                    total_return=best_metrics.get("total_return"),
                )
            )
            method_matrix = suite.get("method_matrix") or {}
            methods = method_matrix.get("methods") if isinstance(method_matrix, dict) else []
            if methods:
                lines.extend(
                    [
                        "",
                        f"### Suite Methods: {suite.get('suite_id')}",
                        "",
                        "| Method | Type | Runs | Passed | Cases |",
                        "|---|---|---:|---:|---|",
                    ]
                )
                for method in methods:
                    if not isinstance(method, dict):
                        continue
                    lines.append(
                        "| {method_id} | {method_type} | {run_count} | {passed_count} | {cases} |".format(
                            method_id=method.get("method_id"),
                            method_type=method.get("method_type"),
                            run_count=method.get("run_count"),
                            passed_count=method.get("passed_count"),
                            cases=", ".join(method.get("case_ids") or []),
                        )
                    )
    else:
        lines.append("| none | 0 | 0 |  |  |  |")
    diagnostics = payload["comparison_diagnostics"]
    lines.extend(
        [
            "",
            "## Diagnostics",
            "",
            "### Threshold Failures",
            "",
        ]
    )
    if diagnostics["threshold_failures"]:
        for failure in diagnostics["threshold_failures"]:
            lines.append(
                f"- {failure['metric']}: actual={failure.get('actual')} threshold={failure.get('threshold')}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "### Weakest Eras", ""])
    if diagnostics["weakest_eras"]:
        lines.extend(
            [
                "| Method | Era | Trades | Total Return | Max Drawdown |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for era in diagnostics["weakest_eras"]:
            lines.append(
                "| {method_id} | {era} | {trade_count} | {total_return} | {max_drawdown} |".format(
                    method_id=era.get("method_id"),
                    era=era.get("era"),
                    trade_count=era.get("trade_count"),
                    total_return=era.get("total_return"),
                    max_drawdown=era.get("max_drawdown"),
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "### Suite Best Runs", ""])
    if diagnostics["suite_best_runs"]:
        lines.extend(
            [
                "| Suite | Case | Strategy | Trades | Total Return | Passed |",
                "|---|---|---|---:|---:|---:|",
            ]
        )
        for run in diagnostics["suite_best_runs"]:
            lines.append(
                "| {suite_id} | {case_id} | {strategy_id} | {trade_count} | {total_return} | {backtest_passed} |".format(
                    suite_id=run.get("suite_id"),
                    case_id=run.get("case_id"),
                    strategy_id=run.get("strategy_id"),
                    trade_count=run.get("trade_count"),
                    total_return=run.get("total_return"),
                    backtest_passed=run.get("backtest_passed"),
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Adapter Spike", ""])
    if payload["adapter_spike"]:
        spike = payload["adapter_spike"]
        decision = spike.get("decision") or {}
        lines.extend(
            [
                f"- selected_for_dependency_adoption: {decision.get('selected_for_dependency_adoption')}",
                f"- reason_codes: {decision.get('reason_codes')}",
                "",
                "| Framework | Status | Adoption Status | Blockers |",
                "|---|---:|---|---|",
            ]
        )
        for candidate in spike.get("candidates") or []:
            lines.append(
                "| {framework_id} | {status} | {adoption_status} | {blockers} |".format(
                    framework_id=candidate.get("framework_id"),
                    status=candidate.get("status"),
                    adoption_status=candidate.get("adoption_status"),
                    blockers=", ".join(candidate.get("adoption_blockers") or []) or "none",
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Framework Run Matrix", ""])
    if payload.get("framework_run"):
        framework_run = payload["framework_run"]
        summary = framework_run.get("summary") or {}
        lines.extend(
            [
                f"- framework_count: {summary.get('framework_count')}",
                f"- executed_count: {summary.get('executed_count')}",
                f"- skipped_count: {summary.get('skipped_count')}",
                f"- failed_count: {summary.get('failed_count')}",
                "",
                "| Framework | Surface | Status | Run Status | Dependency Source | Engine Run |",
                "|---|---|---:|---:|---|---:|",
            ]
        )
        for run in framework_run.get("runs") or []:
            boundary = run.get("boundary") or {}
            lines.append(
                "| {framework_id} | {surface_type} | {status} | {run_status} | {dependency_source} | {engine_run} |".format(
                    framework_id=run.get("framework_id"),
                    surface_type=run.get("surface_type"),
                    status=run.get("status"),
                    run_status=run.get("run_status"),
                    dependency_source=run.get("dependency_source"),
                    engine_run=boundary.get("engine_run"),
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## External Framework Results", ""])
    if payload["external_results"]:
        lines.extend(
            [
                "| Framework | Status | Run Status | Engine Run | Reason Codes | Trades | Total Return |",
                "|---|---:|---:|---:|---|---:|---:|",
            ]
        )
        for result in payload["external_results"]:
            metrics = result.get("metrics") or {}
            lines.append(
                "| {framework_id} | {status} | {run_status} | {engine_run} | {reasons} | {trade_count} | {total_return} |".format(
                    framework_id=result.get("framework_id"),
                    status=result.get("status"),
                    run_status=result.get("run_status"),
                    engine_run=result.get("engine_run"),
                    reasons=", ".join(result.get("reason_codes") or []) or "none",
                    trade_count=metrics.get("trade_count"),
                    total_return=metrics.get("total_return"),
                )
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Portfolio Comparison", ""])
    if payload["portfolio_comparison"]:
        portfolio = payload["portfolio_comparison"]
        lines.extend(
            [
                f"- framework_id: {portfolio.get('framework_id')}",
                f"- run_status: {portfolio.get('run_status')}",
                f"- engine_run: {portfolio.get('engine_run')}",
                f"- portfolio_return: {portfolio.get('portfolio_return')}",
                f"- max_drawdown: {portfolio.get('max_drawdown')}",
                f"- turnover: {portfolio.get('turnover')}",
                f"- rebalance_count: {portfolio.get('rebalance_count')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Metric Extension", ""])
    if payload["metric_extension"]:
        extension = payload["metric_extension"]
        lines.extend(
            [
                f"- framework_id: {extension.get('framework_id')}",
                f"- metric_status: {extension.get('metric_status')}",
                f"- dependency_source: {extension.get('dependency_source')}",
                f"- engine_run: {extension.get('engine_run')}",
                f"- frequency: {extension.get('frequency')}",
                f"- return_count: {extension.get('return_count')}",
                f"- sharpe_ratio: {extension.get('sharpe_ratio')}",
                f"- sortino_ratio: {extension.get('sortino_ratio')}",
                f"- max_drawdown: {extension.get('max_drawdown')}",
                f"- annual_return: {extension.get('annual_return')}",
                f"- annual_volatility: {extension.get('annual_volatility')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Report Extension", ""])
    if payload["report_extension"]:
        extension = payload["report_extension"]
        lines.extend(
            [
                f"- framework_id: {extension.get('framework_id')}",
                f"- report_status: {extension.get('report_status')}",
                f"- dependency_source: {extension.get('dependency_source')}",
                f"- engine_run: {extension.get('engine_run')}",
                f"- frequency: {extension.get('frequency')}",
                f"- return_count: {extension.get('return_count')}",
                f"- metrics_table_row_count: {extension.get('metrics_table_row_count')}",
                f"- quantstats_html_path: {extension.get('quantstats_html_path')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Cost / Slippage Stress", ""])
    if payload["stress"]:
        stress = payload["stress"]
        summary = stress.get("summary") or {}
        lines.extend(
            [
                f"- stress_kind: {stress.get('stress_kind')}",
                f"- scenario_count: {stress.get('scenario_count')}",
                f"- base_total_return: {summary.get('base_total_return')}",
                f"- worst_scenario_id: {summary.get('worst_scenario_id')}",
                f"- worst_stressed_total_return: {summary.get('worst_stressed_total_return')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Regime Split", ""])
    if payload["regime_split"]:
        regime_split = payload["regime_split"]
        summary = regime_split.get("summary") or {}
        lines.extend(
            [
                f"- split_kind: {regime_split.get('split_kind')}",
                f"- dimension_count: {regime_split.get('dimension_count')}",
                f"- worst_dimension_id: {summary.get('worst_dimension_id')}",
                f"- worst_bucket_id: {summary.get('worst_bucket_id')}",
                f"- worst_bucket_total_return: {summary.get('worst_bucket_total_return')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Rolling Stability", ""])
    if payload["rolling_stability"]:
        rolling = payload["rolling_stability"]
        summary = rolling.get("summary") or {}
        lines.extend(
            [
                f"- stability_kind: {rolling.get('stability_kind')}",
                f"- window_count: {rolling.get('window_count')}",
                f"- worst_window_size: {summary.get('worst_window_size')}",
                f"- worst_window_start_index: {summary.get('worst_window_start_index')}",
                f"- worst_window_end_index: {summary.get('worst_window_end_index')}",
                f"- worst_window_total_return: {summary.get('worst_window_total_return')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Benchmark Relative", ""])
    if payload["benchmark_relative"]:
        benchmark = payload["benchmark_relative"]
        summary = benchmark.get("summary") or {}
        lines.extend(
            [
                f"- comparison_kind: {benchmark.get('comparison_kind')}",
                f"- benchmark_series_return_column: {benchmark.get('benchmark_series_return_column')}",
                f"- paired_return_count: {summary.get('paired_return_count')}",
                f"- missing_benchmark_count: {summary.get('missing_benchmark_count')}",
                f"- benchmark_total_return: {summary.get('benchmark_total_return')}",
                f"- active_total_return: {summary.get('active_total_return')}",
                f"- tracking_error: {summary.get('tracking_error')}",
                f"- information_ratio: {summary.get('information_ratio')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Framework Adapter Status",
            "",
            "| Framework | Status | Version | Role | Note |",
            "|---|---:|---|---|---|",
        ]
    )
    for adapter in payload["framework_adapters"]:
        lines.append(
            "| {framework_id} | {status} | {version} | {adapter_role} | {adoption_note} |".format(
                framework_id=adapter["framework_id"],
                status=adapter["status"],
                version=adapter.get("version") or "",
                adapter_role=adapter["adapter_role"],
                adoption_note=adapter["adoption_note"],
            )
        )
    lines.extend(
        [
            "",
            "This comparison does not run external framework engines and does not permit live orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_comparison(
    *,
    metrics_path: Path,
    suite_result_path: Path | None = None,
    adapter_spike_path: Path | None = None,
    framework_run_path: Path | None = None,
    external_result_path: Path | None = None,
    portfolio_comparison_path: Path | None = None,
    metric_extension_path: Path | None = None,
    report_extension_path: Path | None = None,
    stress_path: Path | None = None,
    regime_split_path: Path | None = None,
    rolling_stability_path: Path | None = None,
    benchmark_relative_path: Path | None = None,
    data_availability_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    trial_ledger_path: Path | None = None,
    assumption_ledger_path: Path | None = None,
    no_lookahead_path: Path | None = None,
    execution_simulation_path: Path | None = None,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestComparisonResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    native = _native_result(metrics_payload)
    method_results = _method_results(metrics_payload)
    suite_payload = (
        _read_json(suite_result_path)
        if suite_result_path is not None and suite_result_path.exists()
        else None
    )
    suite_result_hash = (
        _sha256_file(suite_result_path)
        if suite_result_path is not None and suite_result_path.exists()
        else None
    )
    suite_results = _suite_results(suite_payload)
    adapter_spike_payload = (
        _read_json(adapter_spike_path)
        if adapter_spike_path is not None and adapter_spike_path.exists()
        else None
    )
    adapter_spike_hash = (
        _sha256_file(adapter_spike_path)
        if adapter_spike_path is not None and adapter_spike_path.exists()
        else None
    )
    adapter_spike = _adapter_spike(adapter_spike_payload)
    framework_payload = (
        _read_json(framework_run_path)
        if framework_run_path is not None and framework_run_path.exists()
        else None
    )
    framework_run_hash = (
        _sha256_file(framework_run_path)
        if framework_run_path is not None and framework_run_path.exists()
        else None
    )
    framework_run = _framework_run(framework_payload)
    external_payload = (
        _read_json(external_result_path)
        if external_result_path is not None and external_result_path.exists()
        else None
    )
    external_result_hash = (
        _sha256_file(external_result_path)
        if external_result_path is not None and external_result_path.exists()
        else None
    )
    external_results = _external_results(external_payload)
    portfolio_payload = (
        _read_json(portfolio_comparison_path)
        if portfolio_comparison_path is not None and portfolio_comparison_path.exists()
        else None
    )
    portfolio_comparison_hash = (
        _sha256_file(portfolio_comparison_path)
        if portfolio_comparison_path is not None and portfolio_comparison_path.exists()
        else None
    )
    portfolio_comparison = _portfolio_comparison(portfolio_payload)
    metric_payload = (
        _read_json(metric_extension_path)
        if metric_extension_path is not None and metric_extension_path.exists()
        else None
    )
    metric_extension_hash = (
        _sha256_file(metric_extension_path)
        if metric_extension_path is not None and metric_extension_path.exists()
        else None
    )
    metric_extension = _metric_extension(metric_payload)
    report_payload = (
        _read_json(report_extension_path)
        if report_extension_path is not None and report_extension_path.exists()
        else None
    )
    report_extension_hash = (
        _sha256_file(report_extension_path)
        if report_extension_path is not None and report_extension_path.exists()
        else None
    )
    report_extension = _report_extension(report_payload)
    stress_payload = (
        _read_json(stress_path) if stress_path is not None and stress_path.exists() else None
    )
    stress_hash = (
        _sha256_file(stress_path) if stress_path is not None and stress_path.exists() else None
    )
    stress = _stress(stress_payload)
    regime_payload = (
        _read_json(regime_split_path)
        if regime_split_path is not None and regime_split_path.exists()
        else None
    )
    regime_split_hash = (
        _sha256_file(regime_split_path)
        if regime_split_path is not None and regime_split_path.exists()
        else None
    )
    regime_split = _regime_split(regime_payload)
    rolling_payload = (
        _read_json(rolling_stability_path)
        if rolling_stability_path is not None and rolling_stability_path.exists()
        else None
    )
    rolling_stability_hash = (
        _sha256_file(rolling_stability_path)
        if rolling_stability_path is not None and rolling_stability_path.exists()
        else None
    )
    rolling_stability = _rolling_stability(rolling_payload)
    benchmark_payload = (
        _read_json(benchmark_relative_path)
        if benchmark_relative_path is not None and benchmark_relative_path.exists()
        else None
    )
    benchmark_relative_hash = (
        _sha256_file(benchmark_relative_path)
        if benchmark_relative_path is not None and benchmark_relative_path.exists()
        else None
    )
    benchmark_relative = _benchmark_relative(benchmark_payload)
    data_availability_payload = (
        _read_json(data_availability_path)
        if data_availability_path is not None and data_availability_path.exists()
        else None
    )
    data_availability_hash = (
        _sha256_file(data_availability_path)
        if data_availability_path is not None and data_availability_path.exists()
        else None
    )
    data_availability = _completion_artifact(data_availability_payload)
    baseline_payload = (
        _read_json(baseline_comparison_path)
        if baseline_comparison_path is not None and baseline_comparison_path.exists()
        else None
    )
    baseline_comparison_hash = (
        _sha256_file(baseline_comparison_path)
        if baseline_comparison_path is not None and baseline_comparison_path.exists()
        else None
    )
    baseline_comparison = _completion_artifact(baseline_payload)
    trial_payload = (
        _read_json(trial_ledger_path)
        if trial_ledger_path is not None and trial_ledger_path.exists()
        else None
    )
    trial_ledger_hash = (
        _sha256_file(trial_ledger_path)
        if trial_ledger_path is not None and trial_ledger_path.exists()
        else None
    )
    trial_ledger = _completion_artifact(trial_payload)
    assumption_payload = (
        _read_json(assumption_ledger_path)
        if assumption_ledger_path is not None and assumption_ledger_path.exists()
        else None
    )
    assumption_ledger_hash = (
        _sha256_file(assumption_ledger_path)
        if assumption_ledger_path is not None and assumption_ledger_path.exists()
        else None
    )
    assumption_ledger = _completion_artifact(assumption_payload)
    no_lookahead_payload = (
        _read_json(no_lookahead_path)
        if no_lookahead_path is not None and no_lookahead_path.exists()
        else None
    )
    no_lookahead_hash = (
        _sha256_file(no_lookahead_path)
        if no_lookahead_path is not None and no_lookahead_path.exists()
        else None
    )
    no_lookahead_diff = _completion_artifact(no_lookahead_payload)
    execution_payload = (
        _read_json(execution_simulation_path)
        if execution_simulation_path is not None and execution_simulation_path.exists()
        else None
    )
    execution_simulation_hash = (
        _sha256_file(execution_simulation_path)
        if execution_simulation_path is not None and execution_simulation_path.exists()
        else None
    )
    execution_simulation = _completion_artifact(execution_payload)
    comparison_diagnostics = _comparison_diagnostics(
        metrics_payload=metrics_payload,
        method_results=method_results,
        suite_results=suite_results,
    )
    created_at = datetime.now(timezone.utc).isoformat()
    source_hash = _sha256_file(metrics_path)
    comparison_id = hashlib.sha256(
        json.dumps(
            {
                "metrics_path": metrics_path.as_posix(),
                "source_hash": source_hash,
                "suite_result_path": suite_result_path.as_posix()
                if suite_result_path is not None and suite_result_path.exists()
                else None,
                "suite_result_hash": suite_result_hash,
                "adapter_spike_path": adapter_spike_path.as_posix()
                if adapter_spike_path is not None and adapter_spike_path.exists()
                else None,
                "adapter_spike_hash": adapter_spike_hash,
                "external_result_path": external_result_path.as_posix()
                if external_result_path is not None and external_result_path.exists()
                else None,
                "external_result_hash": external_result_hash,
                "native": native,
                "suite_results": suite_results,
                "adapter_spike": adapter_spike,
                "framework_run_path": framework_run_path.as_posix()
                if framework_run_path is not None and framework_run_path.exists()
                else None,
                "framework_run_hash": framework_run_hash,
                "framework_run": framework_run,
                "external_results": external_results,
                "portfolio_comparison_path": portfolio_comparison_path.as_posix()
                if portfolio_comparison_path is not None and portfolio_comparison_path.exists()
                else None,
                "portfolio_comparison_hash": portfolio_comparison_hash,
                "portfolio_comparison": portfolio_comparison,
                "metric_extension_path": metric_extension_path.as_posix()
                if metric_extension_path is not None and metric_extension_path.exists()
                else None,
                "metric_extension_hash": metric_extension_hash,
                "metric_extension": metric_extension,
                "report_extension_path": report_extension_path.as_posix()
                if report_extension_path is not None and report_extension_path.exists()
                else None,
                "report_extension_hash": report_extension_hash,
                "report_extension": report_extension,
                "stress_path": stress_path.as_posix()
                if stress_path is not None and stress_path.exists()
                else None,
                "stress_hash": stress_hash,
                "stress": stress,
                "regime_split_path": regime_split_path.as_posix()
                if regime_split_path is not None and regime_split_path.exists()
                else None,
                "regime_split_hash": regime_split_hash,
                "regime_split": regime_split,
                "rolling_stability_path": rolling_stability_path.as_posix()
                if rolling_stability_path is not None and rolling_stability_path.exists()
                else None,
                "rolling_stability_hash": rolling_stability_hash,
                "rolling_stability": rolling_stability,
                "benchmark_relative_path": benchmark_relative_path.as_posix()
                if benchmark_relative_path is not None and benchmark_relative_path.exists()
                else None,
                "benchmark_relative_hash": benchmark_relative_hash,
                "benchmark_relative": benchmark_relative,
                "data_availability_path": data_availability_path.as_posix()
                if data_availability_path is not None and data_availability_path.exists()
                else None,
                "data_availability_hash": data_availability_hash,
                "data_availability": data_availability,
                "baseline_comparison_path": baseline_comparison_path.as_posix()
                if baseline_comparison_path is not None and baseline_comparison_path.exists()
                else None,
                "baseline_comparison_hash": baseline_comparison_hash,
                "baseline_comparison": baseline_comparison,
                "trial_ledger_path": trial_ledger_path.as_posix()
                if trial_ledger_path is not None and trial_ledger_path.exists()
                else None,
                "trial_ledger_hash": trial_ledger_hash,
                "trial_ledger": trial_ledger,
                "assumption_ledger_path": assumption_ledger_path.as_posix()
                if assumption_ledger_path is not None and assumption_ledger_path.exists()
                else None,
                "assumption_ledger_hash": assumption_ledger_hash,
                "assumption_ledger": assumption_ledger,
                "no_lookahead_path": no_lookahead_path.as_posix()
                if no_lookahead_path is not None and no_lookahead_path.exists()
                else None,
                "no_lookahead_hash": no_lookahead_hash,
                "no_lookahead_diff": no_lookahead_diff,
                "execution_simulation_path": execution_simulation_path.as_posix()
                if execution_simulation_path is not None and execution_simulation_path.exists()
                else None,
                "execution_simulation_hash": execution_simulation_hash,
                "execution_simulation": execution_simulation,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_comparison.v1",
        "comparison_id": f"sha256:{comparison_id}",
        "created_at": created_at,
        "source_metrics_path": metrics_path.as_posix(),
        "source_metrics_hash": source_hash,
        "source_suite_result_path": (
            suite_result_path.as_posix()
            if suite_result_path is not None and suite_result_path.exists()
            else None
        ),
        "source_suite_result_hash": suite_result_hash,
        "source_adapter_spike_path": (
            adapter_spike_path.as_posix()
            if adapter_spike_path is not None and adapter_spike_path.exists()
            else None
        ),
        "source_adapter_spike_hash": adapter_spike_hash,
        "source_framework_run_path": (
            framework_run_path.as_posix()
            if framework_run_path is not None and framework_run_path.exists()
            else None
        ),
        "source_framework_run_hash": framework_run_hash,
        "source_external_result_path": (
            external_result_path.as_posix()
            if external_result_path is not None and external_result_path.exists()
            else None
        ),
        "source_external_result_hash": external_result_hash,
        "source_portfolio_comparison_path": (
            portfolio_comparison_path.as_posix()
            if portfolio_comparison_path is not None and portfolio_comparison_path.exists()
            else None
        ),
        "source_portfolio_comparison_hash": portfolio_comparison_hash,
        "source_metric_extension_path": (
            metric_extension_path.as_posix()
            if metric_extension_path is not None and metric_extension_path.exists()
            else None
        ),
        "source_metric_extension_hash": metric_extension_hash,
        "source_report_extension_path": (
            report_extension_path.as_posix()
            if report_extension_path is not None and report_extension_path.exists()
            else None
        ),
        "source_report_extension_hash": report_extension_hash,
        "source_stress_path": (
            stress_path.as_posix() if stress_path is not None and stress_path.exists() else None
        ),
        "source_stress_hash": stress_hash,
        "source_regime_split_path": (
            regime_split_path.as_posix()
            if regime_split_path is not None and regime_split_path.exists()
            else None
        ),
        "source_regime_split_hash": regime_split_hash,
        "source_rolling_stability_path": (
            rolling_stability_path.as_posix()
            if rolling_stability_path is not None and rolling_stability_path.exists()
            else None
        ),
        "source_rolling_stability_hash": rolling_stability_hash,
        "source_benchmark_relative_path": (
            benchmark_relative_path.as_posix()
            if benchmark_relative_path is not None and benchmark_relative_path.exists()
            else None
        ),
        "source_benchmark_relative_hash": benchmark_relative_hash,
        "source_data_availability_path": (
            data_availability_path.as_posix()
            if data_availability_path is not None and data_availability_path.exists()
            else None
        ),
        "source_data_availability_hash": data_availability_hash,
        "source_baseline_comparison_path": (
            baseline_comparison_path.as_posix()
            if baseline_comparison_path is not None and baseline_comparison_path.exists()
            else None
        ),
        "source_baseline_comparison_hash": baseline_comparison_hash,
        "source_trial_ledger_path": (
            trial_ledger_path.as_posix()
            if trial_ledger_path is not None and trial_ledger_path.exists()
            else None
        ),
        "source_trial_ledger_hash": trial_ledger_hash,
        "source_assumption_ledger_path": (
            assumption_ledger_path.as_posix()
            if assumption_ledger_path is not None and assumption_ledger_path.exists()
            else None
        ),
        "source_assumption_ledger_hash": assumption_ledger_hash,
        "source_no_lookahead_path": (
            no_lookahead_path.as_posix()
            if no_lookahead_path is not None and no_lookahead_path.exists()
            else None
        ),
        "source_no_lookahead_hash": no_lookahead_hash,
        "source_execution_simulation_path": (
            execution_simulation_path.as_posix()
            if execution_simulation_path is not None and execution_simulation_path.exists()
            else None
        ),
        "source_execution_simulation_hash": execution_simulation_hash,
        "native_result": native,
        "method_results": method_results,
        "suite_results": suite_results,
        "adapter_spike": adapter_spike,
        "framework_run": framework_run,
        "external_results": external_results,
        "portfolio_comparison": portfolio_comparison,
        "metric_extension": metric_extension,
        "report_extension": report_extension,
        "stress": stress,
        "regime_split": regime_split,
        "rolling_stability": rolling_stability,
        "benchmark_relative": benchmark_relative,
        "data_availability": data_availability,
        "baseline_comparison": baseline_comparison,
        "trial_ledger": trial_ledger,
        "assumption_ledger": assumption_ledger,
        "no_lookahead_diff": no_lookahead_diff,
        "execution_simulation": execution_simulation,
        "comparison_diagnostics": comparison_diagnostics,
        "framework_adapters": framework_adapter_status(),
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = out_dir / "strategy_backtest_comparison.json"
    comparison_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "strategy_backtest_comparison_report.md", payload)
    return BacktestComparisonResult(
        comparison_path=comparison_path,
        report_path=report_path,
        payload=payload,
    )
