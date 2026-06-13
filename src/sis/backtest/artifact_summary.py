from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class BacktestArtifactSummaryResult:
    payload: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _artifact_exists(path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "exists": path.exists()}


def _summary_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_value(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _artifact_summary(
    path: Path, summarize: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any]:
    row = _artifact_exists(path)
    if not path.exists():
        return row
    payload = _read_json(path)
    row.update(summarize(payload))
    return row


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
            "comparison": comparison if isinstance(comparison, dict) else None,
            "metric_extension": metric_extension if isinstance(metric_extension, dict) else None,
            "regime_split": regime_split if isinstance(regime_split, dict) else None,
            "report_extension": report_extension if isinstance(report_extension, dict) else None,
            "rolling_stability": rolling_stability if isinstance(rolling_stability, dict) else None,
            "stress": stress if isinstance(stress, dict) else None,
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
    comparison_path: Path,
) -> BacktestArtifactSummaryResult:
    payload = {
        "summary_kind": "strategy_backtest_artifact_summary.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pack": _artifact_summary(pack_path, _summarize_pack),
        "pack_validation": _artifact_summary(validation_path, _summarize_validation),
        "benchmark_relative": _artifact_summary(
            benchmark_relative_path, _summarize_benchmark_relative
        ),
        "metric_extension": _artifact_summary(metric_extension_path, _summarize_metric_extension),
        "report_extension": _artifact_summary(report_extension_path, _summarize_report_extension),
        "stress": _artifact_summary(stress_path, _summarize_stress),
        "regime_split": _artifact_summary(regime_split_path, _summarize_regime_split),
        "rolling_stability": _artifact_summary(
            rolling_stability_path, _summarize_rolling_stability
        ),
        "comparison": _artifact_summary(comparison_path, _summarize_comparison),
    }
    return BacktestArtifactSummaryResult(payload=payload)
