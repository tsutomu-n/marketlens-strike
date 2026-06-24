from __future__ import annotations

from typing import Any, cast


def native_result(metrics_payload: dict[str, Any]) -> dict[str, Any]:
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


def method_results(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
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


def suite_results(suite_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
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


def adapter_spike(spike_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def external_results(external_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
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


def framework_run(framework_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def portfolio_comparison(portfolio_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def metric_extension(metric_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def report_extension(report_payload: dict[str, Any] | None) -> dict[str, Any] | None:
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


def completion_artifact(payload: dict[str, Any] | None) -> dict[str, Any] | None:
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
