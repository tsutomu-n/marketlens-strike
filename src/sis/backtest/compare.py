from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest import compare_payload
from sis.backtest.compare_report import write_strategy_backtest_comparison_report
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
    native = compare_payload.native_result(metrics_payload)
    method_results = compare_payload.method_results(metrics_payload)
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
    suite_results = compare_payload.suite_results(suite_payload)
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
    adapter_spike = compare_payload.adapter_spike(adapter_spike_payload)
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
    framework_run = compare_payload.framework_run(framework_payload)
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
    external_results = compare_payload.external_results(external_payload)
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
    portfolio_comparison = compare_payload.portfolio_comparison(portfolio_payload)
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
    metric_extension = compare_payload.metric_extension(metric_payload)
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
    report_extension = compare_payload.report_extension(report_payload)
    stress_payload = (
        _read_json(stress_path) if stress_path is not None and stress_path.exists() else None
    )
    stress_hash = (
        _sha256_file(stress_path) if stress_path is not None and stress_path.exists() else None
    )
    stress = compare_payload.stress(stress_payload)
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
    regime_split = compare_payload.regime_split(regime_payload)
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
    rolling_stability = compare_payload.rolling_stability(rolling_payload)
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
    benchmark_relative = compare_payload.benchmark_relative(benchmark_payload)
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
    data_availability = compare_payload.completion_artifact(data_availability_payload)
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
    baseline_comparison = compare_payload.completion_artifact(baseline_payload)
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
    trial_ledger = compare_payload.completion_artifact(trial_payload)
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
    assumption_ledger = compare_payload.completion_artifact(assumption_payload)
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
    no_lookahead_diff = compare_payload.completion_artifact(no_lookahead_payload)
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
    execution_simulation = compare_payload.completion_artifact(execution_payload)
    comparison_diagnostics = compare_payload.comparison_diagnostics(
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
    report_path = write_strategy_backtest_comparison_report(
        reports_dir / "strategy_backtest_comparison_report.md", payload
    )
    return BacktestComparisonResult(
        comparison_path=comparison_path,
        report_path=report_path,
        payload=payload,
    )
