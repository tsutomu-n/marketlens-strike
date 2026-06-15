from __future__ import annotations

from pathlib import Path
from typing import Any


class BacktestArtifactKey:
    SIGNALS_PARQUET = "signals_parquet"
    SIGNALS_JSONL = "signals_jsonl"
    SIGNAL_MANIFEST = "signal_manifest"
    BACKTEST_METRICS = "backtest_metrics"
    BACKTEST_REPORT = "backtest_report"
    SUITE_RESULT = "suite_result"
    SUITE_REPORT = "suite_report"
    ADAPTER_SPIKE = "adapter_spike"
    ADAPTER_SPIKE_REPORT = "adapter_spike_report"
    BUNDLE_RESULT = "bundle_result"
    BUNDLE_REPORT = "bundle_report"
    EXTERNAL_RESULT = "external_result"
    EXTERNAL_REPORT = "external_report"
    PORTFOLIO_COMPARISON = "portfolio_comparison"
    PORTFOLIO_COMPARISON_REPORT = "portfolio_comparison_report"
    METRIC_EXTENSION = "metric_extension"
    METRIC_EXTENSION_REPORT = "metric_extension_report"
    RETURNS_SERIES = "returns_series"
    REPORT_EXTENSION = "report_extension"
    REPORT_EXTENSION_REPORT = "report_extension_report"
    REPORT_RETURNS_SERIES = "report_returns_series"
    STRESS = "stress"
    STRESS_REPORT = "stress_report"
    REGIME_SPLIT = "regime_split"
    REGIME_SPLIT_REPORT = "regime_split_report"
    ROLLING_STABILITY = "rolling_stability"
    ROLLING_STABILITY_REPORT = "rolling_stability_report"
    BENCHMARK_RELATIVE = "benchmark_relative"
    BENCHMARK_RELATIVE_REPORT = "benchmark_relative_report"
    DATA_AVAILABILITY = "data_availability"
    DATA_AVAILABILITY_REPORT = "data_availability_report"
    BASELINE_COMPARISON = "baseline_comparison"
    BASELINE_COMPARISON_REPORT = "baseline_comparison_report"
    NO_LOOKAHEAD_DIFF = "no_lookahead_diff"
    NO_LOOKAHEAD_DIFF_REPORT = "no_lookahead_diff_report"
    EXECUTION_SIMULATION = "execution_simulation"
    EXECUTION_SIMULATION_REPORT = "execution_simulation_report"
    ASSUMPTION_LEDGER = "assumption_ledger"
    ASSUMPTION_LEDGER_REPORT = "assumption_ledger_report"
    TRIAL_LEDGER = "trial_ledger"
    TRIAL_LEDGER_REPORT = "trial_ledger_report"
    COMPARISON = "comparison"
    COMPARISON_REPORT = "comparison_report"


PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS: tuple[str, ...] = (
    BacktestArtifactKey.DATA_AVAILABILITY,
    BacktestArtifactKey.BASELINE_COMPARISON,
    BacktestArtifactKey.TRIAL_LEDGER,
    BacktestArtifactKey.ASSUMPTION_LEDGER,
    BacktestArtifactKey.NO_LOOKAHEAD_DIFF,
    BacktestArtifactKey.EXECUTION_SIMULATION,
)

PACK_MANIFEST_ARTIFACT_KEYS: tuple[str, ...] = (
    BacktestArtifactKey.SIGNALS_PARQUET,
    BacktestArtifactKey.SIGNALS_JSONL,
    BacktestArtifactKey.SIGNAL_MANIFEST,
    BacktestArtifactKey.BACKTEST_METRICS,
    BacktestArtifactKey.BACKTEST_REPORT,
    BacktestArtifactKey.SUITE_RESULT,
    BacktestArtifactKey.SUITE_REPORT,
    BacktestArtifactKey.ADAPTER_SPIKE,
    BacktestArtifactKey.ADAPTER_SPIKE_REPORT,
    BacktestArtifactKey.BUNDLE_RESULT,
    BacktestArtifactKey.BUNDLE_REPORT,
    BacktestArtifactKey.EXTERNAL_RESULT,
    BacktestArtifactKey.EXTERNAL_REPORT,
    BacktestArtifactKey.PORTFOLIO_COMPARISON,
    BacktestArtifactKey.PORTFOLIO_COMPARISON_REPORT,
    BacktestArtifactKey.METRIC_EXTENSION,
    BacktestArtifactKey.METRIC_EXTENSION_REPORT,
    BacktestArtifactKey.RETURNS_SERIES,
    BacktestArtifactKey.REPORT_EXTENSION,
    BacktestArtifactKey.REPORT_EXTENSION_REPORT,
    BacktestArtifactKey.REPORT_RETURNS_SERIES,
    BacktestArtifactKey.STRESS,
    BacktestArtifactKey.STRESS_REPORT,
    BacktestArtifactKey.REGIME_SPLIT,
    BacktestArtifactKey.REGIME_SPLIT_REPORT,
    BacktestArtifactKey.ROLLING_STABILITY,
    BacktestArtifactKey.ROLLING_STABILITY_REPORT,
    BacktestArtifactKey.BENCHMARK_RELATIVE,
    BacktestArtifactKey.BENCHMARK_RELATIVE_REPORT,
    BacktestArtifactKey.DATA_AVAILABILITY,
    BacktestArtifactKey.DATA_AVAILABILITY_REPORT,
    BacktestArtifactKey.BASELINE_COMPARISON,
    BacktestArtifactKey.BASELINE_COMPARISON_REPORT,
    BacktestArtifactKey.NO_LOOKAHEAD_DIFF,
    BacktestArtifactKey.NO_LOOKAHEAD_DIFF_REPORT,
    BacktestArtifactKey.EXECUTION_SIMULATION,
    BacktestArtifactKey.EXECUTION_SIMULATION_REPORT,
    BacktestArtifactKey.ASSUMPTION_LEDGER,
    BacktestArtifactKey.ASSUMPTION_LEDGER_REPORT,
    BacktestArtifactKey.TRIAL_LEDGER,
    BacktestArtifactKey.TRIAL_LEDGER_REPORT,
    BacktestArtifactKey.COMPARISON,
    BacktestArtifactKey.COMPARISON_REPORT,
)

PACK_REQUIRED_SUITE_METHODS: tuple[str, ...] = (
    "single_window",
    "walk_forward:trading_day",
    "purged_walk_forward:trading_day",
    "purged_walk_forward:trading_day+return_bootstrap",
    "purged_walk_forward:trading_day+block_bootstrap",
)


def external_framework_policy() -> dict[str, Any]:
    return {
        "policy_id": "native_primary_external_evaluation_only.v1",
        "standard_engine": "strategy_authoring_native",
        "decision": "complete_without_locked_external_dependency",
        "locked_dependency_added": False,
        "external_adapters_required_for_completion": False,
        "temporary_uv_with_allowed": ["vectorbt", "bt", "empyrical-reloaded", "quantstats"],
        "candidate_frameworks": [
            "vectorbt",
            "bt",
            "backtesting.py",
            "zipline-reloaded",
            "backtrader",
            "quantstats",
            "empyrical-reloaded",
            "pyfolio-reloaded",
            "qstrader",
        ],
        "adoption_requires": [
            "license_review",
            "python_3_13_uv_lock_review",
            "ci_green",
            "schema_boundary_review",
        ],
    }


def default_pack_artifact_paths(data_dir: Path) -> dict[str, Path]:
    reports_dir = data_dir / "reports"
    research_dir = data_dir / "research"
    return {
        BacktestArtifactKey.SIGNALS_PARQUET: data_dir / "strategy_signals.parquet",
        BacktestArtifactKey.SIGNALS_JSONL: data_dir / "strategy_signals.jsonl",
        BacktestArtifactKey.SIGNAL_MANIFEST: data_dir / "strategy_signal_manifest.json",
        BacktestArtifactKey.BACKTEST_METRICS: research_dir
        / "backtests/strategy_backtest_metrics.json",
        BacktestArtifactKey.BACKTEST_REPORT: reports_dir / "strategy_backtest_report.md",
        BacktestArtifactKey.SUITE_RESULT: research_dir
        / "backtest_suite/strategy_backtest_suite_result.json",
        BacktestArtifactKey.SUITE_REPORT: reports_dir / "strategy_backtest_suite_report.md",
        BacktestArtifactKey.EXTERNAL_RESULT: research_dir
        / "backtest_external/strategy_backtest_external_result.json",
        BacktestArtifactKey.EXTERNAL_REPORT: reports_dir / "strategy_backtest_external_report.md",
        BacktestArtifactKey.PORTFOLIO_COMPARISON: research_dir
        / "backtest_portfolio/strategy_backtest_portfolio_comparison.json",
        BacktestArtifactKey.PORTFOLIO_COMPARISON_REPORT: reports_dir
        / "strategy_backtest_portfolio_comparison_report.md",
        BacktestArtifactKey.METRIC_EXTENSION: research_dir
        / "backtest_metric_extension/strategy_backtest_metric_extension.json",
        BacktestArtifactKey.METRIC_EXTENSION_REPORT: reports_dir
        / "strategy_backtest_metric_extension_report.md",
        BacktestArtifactKey.REPORT_EXTENSION: research_dir
        / "backtest_report_extension/strategy_backtest_report_extension.json",
        BacktestArtifactKey.REPORT_EXTENSION_REPORT: reports_dir
        / "strategy_backtest_report_extension_report.md",
        BacktestArtifactKey.STRESS: research_dir / "backtest_stress/strategy_backtest_stress.json",
        BacktestArtifactKey.STRESS_REPORT: reports_dir / "strategy_backtest_stress_report.md",
        BacktestArtifactKey.REGIME_SPLIT: research_dir
        / "backtest_regime_split/strategy_backtest_regime_split.json",
        BacktestArtifactKey.REGIME_SPLIT_REPORT: reports_dir
        / "strategy_backtest_regime_split_report.md",
        BacktestArtifactKey.ROLLING_STABILITY: research_dir
        / "backtest_rolling_stability/strategy_backtest_rolling_stability.json",
        BacktestArtifactKey.ROLLING_STABILITY_REPORT: reports_dir
        / "strategy_backtest_rolling_stability_report.md",
        BacktestArtifactKey.BENCHMARK_RELATIVE: research_dir
        / "backtest_benchmark_relative/strategy_backtest_benchmark_relative.json",
        BacktestArtifactKey.BENCHMARK_RELATIVE_REPORT: reports_dir
        / "strategy_backtest_benchmark_relative_report.md",
        BacktestArtifactKey.DATA_AVAILABILITY: research_dir
        / "backtest_data_availability/backtest_data_availability_ledger.json",
        BacktestArtifactKey.DATA_AVAILABILITY_REPORT: reports_dir
        / "backtest_data_availability_report.md",
        BacktestArtifactKey.BASELINE_COMPARISON: research_dir
        / "backtest_baseline_comparison/strategy_backtest_baseline_comparison.json",
        BacktestArtifactKey.BASELINE_COMPARISON_REPORT: reports_dir
        / "strategy_backtest_baseline_comparison_report.md",
        BacktestArtifactKey.NO_LOOKAHEAD_DIFF: research_dir
        / "backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json",
        BacktestArtifactKey.NO_LOOKAHEAD_DIFF_REPORT: reports_dir
        / "strategy_backtest_no_lookahead_diff_report.md",
        BacktestArtifactKey.EXECUTION_SIMULATION: research_dir
        / "backtest_execution_simulation/strategy_backtest_execution_simulation.json",
        BacktestArtifactKey.EXECUTION_SIMULATION_REPORT: reports_dir
        / "strategy_backtest_execution_simulation_report.md",
        BacktestArtifactKey.ASSUMPTION_LEDGER: research_dir
        / "backtest_assumption_ledger/strategy_backtest_assumption_ledger.json",
        BacktestArtifactKey.ASSUMPTION_LEDGER_REPORT: reports_dir
        / "strategy_backtest_assumption_ledger_report.md",
        BacktestArtifactKey.TRIAL_LEDGER: research_dir
        / "backtest_trial_ledger/strategy_backtest_trial_ledger.json",
        BacktestArtifactKey.TRIAL_LEDGER_REPORT: reports_dir
        / "strategy_backtest_trial_ledger_report.md",
        BacktestArtifactKey.COMPARISON: research_dir
        / "backtest_compare/strategy_backtest_comparison.json",
        BacktestArtifactKey.COMPARISON_REPORT: reports_dir
        / "strategy_backtest_comparison_report.md",
    }
