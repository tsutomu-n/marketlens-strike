from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_summary_registry import (
    ARTIFACT_SUMMARY_SPECS,
    summarize_artifact,
)


@dataclass(frozen=True)
class BacktestArtifactSummaryResult:
    payload: dict[str, Any]


def _summary_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_value(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _summarize_pack(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    policy = _summary_value(payload, "external_framework_policy")
    artifacts = _summary_value(payload, "artifacts")
    benchmark_relative = artifacts.get("benchmark_relative")
    report_extension = artifacts.get("report_extension")
    metric_extension = artifacts.get("metric_extension")
    comparison = artifacts.get("comparison")
    stress = artifacts.get("stress")
    regime_split = artifacts.get("regime_split")
    rolling_stability = artifacts.get("rolling_stability")
    data_availability = artifacts.get("data_availability")
    baseline_comparison = artifacts.get("baseline_comparison")
    trial_ledger = artifacts.get("trial_ledger")
    assumption_ledger = artifacts.get("assumption_ledger")
    no_lookahead_diff = artifacts.get("no_lookahead_diff")
    execution_simulation = artifacts.get("execution_simulation")
    return {
        "schema_version": payload.get("schema_version"),
        "paper_only": payload.get("paper_only"),
        "live_order_submitted": payload.get("live_order_submitted"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
        "suite_run_count": summary.get("suite_run_count"),
        "suite_method_count": summary.get("suite_method_count"),
        "external_engine_run": summary.get("external_engine_run"),
        "comparison_id": summary.get("comparison_id"),
        "capital": summary.get("capital") if isinstance(summary.get("capital"), dict) else None,
        "external_framework_policy": {
            "policy_id": policy.get("policy_id"),
            "standard_engine": policy.get("standard_engine"),
            "decision": policy.get("decision"),
            "locked_dependency_added": policy.get("locked_dependency_added"),
            "external_adapters_required_for_completion": policy.get(
                "external_adapters_required_for_completion"
            ),
        },
        "artifacts": {
            "benchmark_relative": benchmark_relative
            if isinstance(benchmark_relative, dict)
            else None,
            "baseline_comparison": baseline_comparison
            if isinstance(baseline_comparison, dict)
            else None,
            "comparison": comparison if isinstance(comparison, dict) else None,
            "data_availability": data_availability if isinstance(data_availability, dict) else None,
            "execution_simulation": execution_simulation
            if isinstance(execution_simulation, dict)
            else None,
            "assumption_ledger": assumption_ledger if isinstance(assumption_ledger, dict) else None,
            "metric_extension": metric_extension if isinstance(metric_extension, dict) else None,
            "no_lookahead_diff": no_lookahead_diff if isinstance(no_lookahead_diff, dict) else None,
            "regime_split": regime_split if isinstance(regime_split, dict) else None,
            "report_extension": report_extension if isinstance(report_extension, dict) else None,
            "rolling_stability": rolling_stability if isinstance(rolling_stability, dict) else None,
            "stress": stress if isinstance(stress, dict) else None,
            "trial_ledger": trial_ledger if isinstance(trial_ledger, dict) else None,
        },
    }


def _summarize_validation(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    return {
        "schema_version": payload.get("schema_version"),
        "decision": payload.get("decision"),
        "check_count": summary.get("check_count"),
        "passed_count": summary.get("passed_count"),
        "failed_count": summary.get("failed_count"),
        "locked_dependency_added": summary.get("locked_dependency_added"),
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_benchmark_relative(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    comparisons = payload.get("comparisons")
    return {
        "schema_version": payload.get("schema_version"),
        "source_benchmark_series_path": payload.get("source_benchmark_series_path"),
        "source_benchmark_series_hash": payload.get("source_benchmark_series_hash"),
        "benchmark_series_return_column": payload.get("benchmark_series_return_column"),
        "strategy_total_return": summary.get("strategy_total_return"),
        "benchmark_total_return": summary.get("benchmark_total_return"),
        "active_total_return": summary.get("active_total_return"),
        "tracking_error": summary.get("tracking_error"),
        "information_ratio": summary.get("information_ratio"),
        "missing_benchmark_count": summary.get("missing_benchmark_count"),
        "comparison_count": len(comparisons) if isinstance(comparisons, list) else None,
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_metric_extension(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "metric_status": payload.get("metric_status"),
        "dependency_source": payload.get("dependency_source"),
        "framework_version": payload.get("framework_version"),
        "runner_mode": payload.get("runner_mode"),
        "engine_run": payload.get("engine_run"),
        "return_count": payload.get("return_count"),
        "sharpe_ratio": payload.get("sharpe_ratio"),
        "max_drawdown": payload.get("max_drawdown"),
        "annual_return": payload.get("annual_return"),
        "annual_volatility": payload.get("annual_volatility"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_report_extension(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "report_status": payload.get("report_status"),
        "dependency_source": payload.get("dependency_source"),
        "framework_version": payload.get("framework_version"),
        "runner_mode": payload.get("runner_mode"),
        "engine_run": payload.get("engine_run"),
        "return_count": payload.get("return_count"),
        "metrics_table_row_count": payload.get("metrics_table_row_count"),
        "framework_warning_count": payload.get("framework_warning_count"),
        "quantstats_html_path": payload.get("quantstats_html_path"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_stress(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    return {
        "schema_version": payload.get("schema_version"),
        "scenario_count": payload.get("scenario_count"),
        "return_count": summary.get("return_count"),
        "base_total_return": summary.get("base_total_return"),
        "worst_scenario_id": summary.get("worst_scenario_id"),
        "worst_stressed_total_return": summary.get("worst_stressed_total_return"),
        "worst_delta_total_return": summary.get("worst_delta_total_return"),
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_regime_split(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    return {
        "schema_version": payload.get("schema_version"),
        "dimension_count": payload.get("dimension_count"),
        "return_count": summary.get("return_count"),
        "worst_dimension_id": summary.get("worst_dimension_id"),
        "worst_bucket_id": summary.get("worst_bucket_id"),
        "worst_bucket_total_return": summary.get("worst_bucket_total_return"),
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_rolling_stability(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    return {
        "schema_version": payload.get("schema_version"),
        "window_count": payload.get("window_count"),
        "return_count": summary.get("return_count"),
        "worst_window_size": summary.get("worst_window_size"),
        "worst_window_start_index": summary.get("worst_window_start_index"),
        "worst_window_end_index": summary.get("worst_window_end_index"),
        "worst_window_total_return": summary.get("worst_window_total_return"),
        "worst_window_max_drawdown": summary.get("worst_window_max_drawdown"),
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_comparison(payload: dict[str, Any]) -> dict[str, Any]:
    diagnostics = _summary_value(payload, "comparison_diagnostics")
    native = _summary_value(payload, "native_result")
    threshold_failures = _list_value(diagnostics, "threshold_failures")
    weakest_eras = _list_value(diagnostics, "weakest_eras")
    suite_best_runs = _list_value(diagnostics, "suite_best_runs")
    suite_failed_runs = _list_value(diagnostics, "suite_failed_runs")
    return {
        "schema_version": payload.get("schema_version"),
        "comparison_id": payload.get("comparison_id"),
        "method_result_count": len(_list_value(payload, "method_results")),
        "suite_result_count": len(_list_value(payload, "suite_results")),
        "framework_adapter_count": len(_list_value(payload, "framework_adapters")),
        "threshold_failure_count": len(threshold_failures),
        "weakest_era_count": len(weakest_eras),
        "suite_best_run_count": len(suite_best_runs),
        "suite_failed_run_count": len(suite_failed_runs),
        "first_threshold_failure": threshold_failures[0] if threshold_failures else None,
        "first_weakest_era": weakest_eras[0] if weakest_eras else None,
        "first_suite_best_run": suite_best_runs[0] if suite_best_runs else None,
        "capital": native.get("capital") if isinstance(native.get("capital"), dict) else None,
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _summarize_completion_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_value(payload, "summary")
    return {
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "summary": summary,
        "paper_only": payload.get("paper_only"),
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def build_strategy_backtest_artifact_summary(
    *,
    pack_path: Path,
    validation_path: Path,
    benchmark_relative_path: Path,
    metric_extension_path: Path,
    report_extension_path: Path,
    stress_path: Path,
    regime_split_path: Path,
    rolling_stability_path: Path,
    data_availability_path: Path,
    baseline_comparison_path: Path,
    trial_ledger_path: Path,
    assumption_ledger_path: Path,
    no_lookahead_path: Path,
    execution_simulation_path: Path,
    comparison_path: Path,
) -> BacktestArtifactSummaryResult:
    paths = {
        "pack_path": pack_path,
        "validation_path": validation_path,
        "benchmark_relative_path": benchmark_relative_path,
        "metric_extension_path": metric_extension_path,
        "report_extension_path": report_extension_path,
        "stress_path": stress_path,
        "regime_split_path": regime_split_path,
        "rolling_stability_path": rolling_stability_path,
        "data_availability_path": data_availability_path,
        "baseline_comparison_path": baseline_comparison_path,
        "trial_ledger_path": trial_ledger_path,
        "assumption_ledger_path": assumption_ledger_path,
        "no_lookahead_path": no_lookahead_path,
        "execution_simulation_path": execution_simulation_path,
        "comparison_path": comparison_path,
    }
    summarizers = {
        "pack": _summarize_pack,
        "validation": _summarize_validation,
        "benchmark_relative": _summarize_benchmark_relative,
        "metric_extension": _summarize_metric_extension,
        "report_extension": _summarize_report_extension,
        "stress": _summarize_stress,
        "regime_split": _summarize_regime_split,
        "rolling_stability": _summarize_rolling_stability,
        "completion_artifact": _summarize_completion_artifact,
        "comparison": _summarize_comparison,
    }
    payload: dict[str, Any] = {
        "summary_kind": "strategy_backtest_artifact_summary.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for spec in ARTIFACT_SUMMARY_SPECS:
        payload[spec.key] = summarize_artifact(paths[spec.path_field], spec, summarizers)
    return BacktestArtifactSummaryResult(payload=payload)
