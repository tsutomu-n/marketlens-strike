from __future__ import annotations

from pathlib import Path
from typing import Any


def write_strategy_backtest_comparison_report(path: Path, payload: dict[str, Any]) -> Path:
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
