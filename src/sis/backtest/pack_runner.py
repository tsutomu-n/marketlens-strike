from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sis.backtest.adapter_spike import build_backtest_adapter_spike
from sis.backtest.assumptions import build_strategy_backtest_assumption_ledger
from sis.backtest.baselines import build_strategy_backtest_baseline_comparison
from sis.backtest.benchmark_relative import build_strategy_backtest_benchmark_relative
from sis.backtest.compare import build_strategy_backtest_comparison
from sis.backtest.data_availability import build_backtest_data_availability_ledger
from sis.backtest.execution_simulation import build_strategy_backtest_execution_simulation
from sis.backtest.external import build_strategy_backtest_external_result
from sis.backtest.framework_run import build_strategy_backtest_framework_run
from sis.backtest.metric_extension import build_strategy_backtest_metric_extension
from sis.backtest.no_lookahead import build_strategy_backtest_no_lookahead_diff
from sis.backtest.pack import validate_strategy_backtest_pack, write_strategy_backtest_pack_outputs
from sis.backtest.pack_contract import PACK_MANIFEST_ARTIFACT_KEYS, BacktestArtifactKey
from sis.backtest.portfolio_comparison import build_strategy_backtest_portfolio_comparison
from sis.backtest.regime_split import build_strategy_backtest_regime_split
from sis.backtest.report_extension import build_strategy_backtest_report_extension
from sis.backtest.rolling_stability import build_strategy_backtest_rolling_stability
from sis.backtest.stress import build_strategy_backtest_stress
from sis.backtest.trial_ledger import build_strategy_backtest_trial_ledger
from sis.research.strategy_lab.authoring.backtest import run_authoring_backtest
from sis.research.strategy_lab.authoring.backtest_outputs import (
    write_authoring_backtest_outputs,
)
from sis.research.strategy_lab.authoring.backtest_suite import run_backtest_suite
from sis.research.strategy_lab.authoring.backtest_suite_outputs import (
    write_backtest_suite_outputs,
)
from sis.research.strategy_lab.authoring.bundle import run_authoring_bundle
from sis.research.strategy_lab.authoring.bundle_outputs import (
    write_authoring_bundle_outputs,
)
from sis.research.strategy_lab.authoring.compiler.artifacts import (
    write_authoring_signal_artifacts,
)
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.evaluation_window import (
    apply_evaluation_window,
    manifest_for_evaluation_frame,
)
from sis.research.strategy_lab.authoring.io import (
    load_authoring_bundle_spec,
    load_authoring_spec,
    load_backtest_suite_spec,
)


@dataclass(frozen=True)
class StrategyBacktestPackRunInputs:
    spec_path: Path
    suite_path: Path
    bundle_path: Path
    label_horizon_minutes: int
    benchmark_series_path: Path | None
    benchmark_series_return_column: str
    out_dir: Path
    reports_dir: Path
    data_dir: Path


@dataclass(frozen=True)
class StrategyBacktestPackRunResult:
    pack_path: Path
    pack_report_path: Path
    validation_path: Path
    validation_report_path: Path
    validation_decision: str
    comparison_path: Path
    framework_run_path: Path
    portfolio_comparison_path: Path
    metric_extension_path: Path
    report_extension_path: Path
    stress_path: Path
    regime_split_path: Path
    rolling_stability_path: Path
    benchmark_relative_path: Path
    data_availability_path: Path
    baseline_comparison_path: Path
    no_lookahead_path: Path
    execution_simulation_path: Path
    assumption_ledger_path: Path
    trial_ledger_path: Path
    suite_result_path: Path


def run_strategy_backtest_pack(
    inputs: StrategyBacktestPackRunInputs,
) -> StrategyBacktestPackRunResult:
    parsed_spec = load_authoring_spec(inputs.spec_path)
    parsed_suite = load_backtest_suite_spec(inputs.suite_path)
    parsed_bundle = load_authoring_bundle_spec(inputs.bundle_path)
    quotes_path = _resolve_spec_data_path(parsed_spec.data.quote_data_path, inputs.data_dir)

    frame, manifest = build_authoring_signals(parsed_spec, data_dir=inputs.data_dir)
    evaluation_frame = apply_evaluation_window(parsed_spec, frame)
    evaluation_manifest = manifest_for_evaluation_frame(
        parsed_spec, frame, evaluation_frame, manifest
    )
    pack_signal_data_dir = inputs.out_dir / "source_artifacts"
    signal_artifacts = write_authoring_signal_artifacts(
        evaluation_frame, evaluation_manifest, data_dir=pack_signal_data_dir
    )
    metrics, summary = run_authoring_backtest(parsed_spec, frame, data_dir=inputs.data_dir)
    backtest_artifacts = write_authoring_backtest_outputs(
        parsed_spec, metrics, summary, data_dir=inputs.data_dir
    )
    suite_payload = run_backtest_suite(
        parsed_suite, suite_path=inputs.suite_path, data_dir=inputs.data_dir
    )
    suite_artifacts = write_backtest_suite_outputs(suite_payload, data_dir=inputs.data_dir)
    adapter_result = build_backtest_adapter_spike(
        out_dir=inputs.data_dir / "research/backtest_adapter_spike",
        reports_dir=inputs.reports_dir,
    )
    bundle_payload = run_authoring_bundle(
        parsed_bundle, bundle_path=inputs.bundle_path, data_dir=inputs.data_dir
    )
    bundle_artifacts = write_authoring_bundle_outputs(bundle_payload, data_dir=inputs.data_dir)
    framework_run_result = build_strategy_backtest_framework_run(
        frameworks=["vectorbt", "bt", "metrics", "reports"],
        metrics_path=backtest_artifacts["metrics"],
        bundle_path=bundle_artifacts["bundle_result"],
        price_frame_path=quotes_path,
        signals_path=signal_artifacts["signals_parquet"],
        quotes_path=quotes_path,
        label_horizon_minutes=inputs.label_horizon_minutes,
        out_dir=inputs.data_dir / "research/backtest_framework_run",
        reports_dir=inputs.reports_dir,
    )
    external_result = build_strategy_backtest_external_result(
        metrics_path=backtest_artifacts["metrics"],
        signals_path=signal_artifacts["signals_parquet"],
        quotes_path=quotes_path,
        label_horizon_minutes=inputs.label_horizon_minutes,
        initial_capital_usd=parsed_spec.backtest.initial_capital_usd,
        out_dir=inputs.data_dir / "research/backtest_external",
        reports_dir=inputs.reports_dir,
    )
    portfolio_comparison_result = build_strategy_backtest_portfolio_comparison(
        bundle_path=bundle_artifacts["bundle_result"],
        price_frame_path=quotes_path,
        initial_capital_usd=parsed_spec.backtest.initial_capital_usd,
        out_dir=inputs.data_dir / "research/backtest_portfolio",
        reports_dir=inputs.reports_dir,
    )
    metric_extension_result = build_strategy_backtest_metric_extension(
        metrics_path=backtest_artifacts["metrics"],
        out_dir=inputs.data_dir / "research/backtest_metric_extension",
        reports_dir=inputs.reports_dir,
    )
    report_extension_result = build_strategy_backtest_report_extension(
        metrics_path=backtest_artifacts["metrics"],
        out_dir=inputs.data_dir / "research/backtest_report_extension",
        reports_dir=inputs.reports_dir,
    )
    stress_result = build_strategy_backtest_stress(
        metrics_path=backtest_artifacts["metrics"],
        out_dir=inputs.data_dir / "research/backtest_stress",
        reports_dir=inputs.reports_dir,
    )
    regime_split_result = build_strategy_backtest_regime_split(
        metrics_path=backtest_artifacts["metrics"],
        out_dir=inputs.data_dir / "research/backtest_regime_split",
        reports_dir=inputs.reports_dir,
    )
    rolling_stability_result = build_strategy_backtest_rolling_stability(
        metrics_path=backtest_artifacts["metrics"],
        out_dir=inputs.data_dir / "research/backtest_rolling_stability",
        reports_dir=inputs.reports_dir,
    )
    benchmark_relative_result = build_strategy_backtest_benchmark_relative(
        metrics_path=backtest_artifacts["metrics"],
        quotes_path=quotes_path,
        benchmark_series_path=inputs.benchmark_series_path,
        benchmark_series_return_column=inputs.benchmark_series_return_column,
        horizon_minutes=parsed_spec.backtest.label_horizon_minutes,
        out_dir=inputs.data_dir / "research/backtest_benchmark_relative",
        reports_dir=inputs.reports_dir,
    )
    data_availability_result = build_backtest_data_availability_ledger(
        metrics_path=backtest_artifacts["metrics"],
        signals_path=signal_artifacts["signals_parquet"],
        quotes_path=quotes_path,
        out_dir=inputs.data_dir / "research/backtest_data_availability",
        reports_dir=inputs.reports_dir,
    )
    baseline_comparison_result = build_strategy_backtest_baseline_comparison(
        metrics_path=backtest_artifacts["metrics"],
        out_dir=inputs.data_dir / "research/backtest_baseline_comparison",
        reports_dir=inputs.reports_dir,
    )
    no_lookahead_result = build_strategy_backtest_no_lookahead_diff(
        metrics_path=backtest_artifacts["metrics"],
        signals_path=signal_artifacts["signals_parquet"],
        quotes_path=quotes_path,
        spec_path=inputs.spec_path,
        data_dir=inputs.data_dir,
        out_dir=inputs.data_dir / "research/backtest_no_lookahead",
        reports_dir=inputs.reports_dir,
    )
    execution_simulation_result = build_strategy_backtest_execution_simulation(
        metrics_path=backtest_artifacts["metrics"],
        signals_path=signal_artifacts["signals_parquet"],
        out_dir=inputs.data_dir / "research/backtest_execution_simulation",
        reports_dir=inputs.reports_dir,
    )
    assumption_ledger_result = build_strategy_backtest_assumption_ledger(
        data_availability_path=data_availability_result.ledger_path,
        baseline_comparison_path=baseline_comparison_result.comparison_path,
        no_lookahead_path=no_lookahead_result.diff_path,
        execution_simulation_path=execution_simulation_result.simulation_path,
        out_dir=inputs.data_dir / "research/backtest_assumption_ledger",
        reports_dir=inputs.reports_dir,
    )
    completion_artifacts = {
        BacktestArtifactKey.SIGNALS_PARQUET: signal_artifacts["signals_parquet"],
        BacktestArtifactKey.BACKTEST_METRICS: backtest_artifacts["metrics"],
        BacktestArtifactKey.SUITE_RESULT: suite_artifacts["suite_result"],
        BacktestArtifactKey.EXTERNAL_RESULT: external_result.external_path,
        BacktestArtifactKey.PORTFOLIO_COMPARISON: portfolio_comparison_result.comparison_path,
        BacktestArtifactKey.METRIC_EXTENSION: metric_extension_result.metric_extension_path,
        BacktestArtifactKey.REPORT_EXTENSION: report_extension_result.report_extension_path,
        BacktestArtifactKey.STRESS: stress_result.stress_path,
        BacktestArtifactKey.REGIME_SPLIT: regime_split_result.regime_split_path,
        BacktestArtifactKey.ROLLING_STABILITY: rolling_stability_result.rolling_stability_path,
        BacktestArtifactKey.BENCHMARK_RELATIVE: benchmark_relative_result.benchmark_relative_path,
        BacktestArtifactKey.DATA_AVAILABILITY: data_availability_result.ledger_path,
        BacktestArtifactKey.BASELINE_COMPARISON: baseline_comparison_result.comparison_path,
        BacktestArtifactKey.NO_LOOKAHEAD_DIFF: no_lookahead_result.diff_path,
        BacktestArtifactKey.EXECUTION_SIMULATION: execution_simulation_result.simulation_path,
        BacktestArtifactKey.ASSUMPTION_LEDGER: assumption_ledger_result.ledger_path,
    }
    trial_ledger_result = build_strategy_backtest_trial_ledger(
        artifacts=completion_artifacts,
        out_dir=inputs.data_dir / "research/backtest_trial_ledger",
        reports_dir=inputs.reports_dir,
    )
    comparison_result = build_strategy_backtest_comparison(
        metrics_path=backtest_artifacts["metrics"],
        suite_result_path=suite_artifacts["suite_result"],
        adapter_spike_path=adapter_result.spike_path,
        framework_run_path=framework_run_result.run_path,
        external_result_path=external_result.external_path,
        portfolio_comparison_path=portfolio_comparison_result.comparison_path,
        metric_extension_path=metric_extension_result.metric_extension_path,
        report_extension_path=report_extension_result.report_extension_path,
        stress_path=stress_result.stress_path,
        regime_split_path=regime_split_result.regime_split_path,
        rolling_stability_path=rolling_stability_result.rolling_stability_path,
        benchmark_relative_path=benchmark_relative_result.benchmark_relative_path,
        data_availability_path=data_availability_result.ledger_path,
        baseline_comparison_path=baseline_comparison_result.comparison_path,
        trial_ledger_path=trial_ledger_result.ledger_path,
        assumption_ledger_path=assumption_ledger_result.ledger_path,
        no_lookahead_path=no_lookahead_result.diff_path,
        execution_simulation_path=execution_simulation_result.simulation_path,
        out_dir=inputs.data_dir / "research/backtest_compare",
        reports_dir=inputs.reports_dir,
    )
    manifest_artifacts = {
        BacktestArtifactKey.SIGNALS_PARQUET: signal_artifacts["signals_parquet"],
        BacktestArtifactKey.SIGNALS_JSONL: signal_artifacts["signals_jsonl"],
        BacktestArtifactKey.SIGNAL_MANIFEST: signal_artifacts["manifest"],
        BacktestArtifactKey.BACKTEST_METRICS: backtest_artifacts["metrics"],
        BacktestArtifactKey.BACKTEST_REPORT: backtest_artifacts["report"],
        BacktestArtifactKey.SUITE_RESULT: suite_artifacts["suite_result"],
        BacktestArtifactKey.SUITE_REPORT: suite_artifacts["suite_report"],
        BacktestArtifactKey.ADAPTER_SPIKE: adapter_result.spike_path,
        BacktestArtifactKey.ADAPTER_SPIKE_REPORT: adapter_result.report_path,
        BacktestArtifactKey.BUNDLE_RESULT: bundle_artifacts["bundle_result"],
        BacktestArtifactKey.BUNDLE_REPORT: bundle_artifacts["bundle_report"],
        BacktestArtifactKey.FRAMEWORK_RUN: framework_run_result.run_path,
        BacktestArtifactKey.FRAMEWORK_RUN_REPORT: framework_run_result.report_path,
        BacktestArtifactKey.EXTERNAL_RESULT: external_result.external_path,
        BacktestArtifactKey.EXTERNAL_REPORT: external_result.report_path,
        BacktestArtifactKey.PORTFOLIO_COMPARISON: portfolio_comparison_result.comparison_path,
        BacktestArtifactKey.PORTFOLIO_COMPARISON_REPORT: portfolio_comparison_result.report_path,
        BacktestArtifactKey.METRIC_EXTENSION: metric_extension_result.metric_extension_path,
        BacktestArtifactKey.METRIC_EXTENSION_REPORT: metric_extension_result.report_path,
        BacktestArtifactKey.RETURNS_SERIES: metric_extension_result.returns_series_path,
        BacktestArtifactKey.REPORT_EXTENSION: report_extension_result.report_extension_path,
        BacktestArtifactKey.REPORT_EXTENSION_REPORT: report_extension_result.report_path,
        BacktestArtifactKey.REPORT_RETURNS_SERIES: report_extension_result.returns_series_path,
        BacktestArtifactKey.STRESS: stress_result.stress_path,
        BacktestArtifactKey.STRESS_REPORT: stress_result.report_path,
        BacktestArtifactKey.REGIME_SPLIT: regime_split_result.regime_split_path,
        BacktestArtifactKey.REGIME_SPLIT_REPORT: regime_split_result.report_path,
        BacktestArtifactKey.ROLLING_STABILITY: rolling_stability_result.rolling_stability_path,
        BacktestArtifactKey.ROLLING_STABILITY_REPORT: rolling_stability_result.report_path,
        BacktestArtifactKey.BENCHMARK_RELATIVE: benchmark_relative_result.benchmark_relative_path,
        BacktestArtifactKey.BENCHMARK_RELATIVE_REPORT: benchmark_relative_result.report_path,
        BacktestArtifactKey.DATA_AVAILABILITY: data_availability_result.ledger_path,
        BacktestArtifactKey.DATA_AVAILABILITY_REPORT: data_availability_result.report_path,
        BacktestArtifactKey.BASELINE_COMPARISON: baseline_comparison_result.comparison_path,
        BacktestArtifactKey.BASELINE_COMPARISON_REPORT: baseline_comparison_result.report_path,
        BacktestArtifactKey.NO_LOOKAHEAD_DIFF: no_lookahead_result.diff_path,
        BacktestArtifactKey.NO_LOOKAHEAD_DIFF_REPORT: no_lookahead_result.report_path,
        BacktestArtifactKey.EXECUTION_SIMULATION: execution_simulation_result.simulation_path,
        BacktestArtifactKey.EXECUTION_SIMULATION_REPORT: execution_simulation_result.report_path,
        BacktestArtifactKey.ASSUMPTION_LEDGER: assumption_ledger_result.ledger_path,
        BacktestArtifactKey.ASSUMPTION_LEDGER_REPORT: assumption_ledger_result.report_path,
        BacktestArtifactKey.TRIAL_LEDGER: trial_ledger_result.ledger_path,
        BacktestArtifactKey.TRIAL_LEDGER_REPORT: trial_ledger_result.report_path,
        BacktestArtifactKey.COMPARISON: comparison_result.comparison_path,
        BacktestArtifactKey.COMPARISON_REPORT: comparison_result.report_path,
    }
    _assert_manifest_artifact_keys(manifest_artifacts)
    pack_result = write_strategy_backtest_pack_outputs(
        spec_path=inputs.spec_path,
        suite_path=inputs.suite_path,
        artifacts=manifest_artifacts,
        suite_payload=suite_payload,
        external_payload=external_result.payload,
        comparison_payload=comparison_result.payload,
        out_dir=inputs.out_dir,
        reports_dir=inputs.reports_dir,
    )
    validation_result = validate_strategy_backtest_pack(
        pack_path=pack_result.pack_path,
        out_dir=inputs.out_dir,
        reports_dir=inputs.reports_dir,
    )
    return StrategyBacktestPackRunResult(
        pack_path=pack_result.pack_path,
        pack_report_path=pack_result.report_path,
        validation_path=validation_result.validation_path,
        validation_report_path=validation_result.report_path,
        validation_decision=str(validation_result.payload["decision"]),
        comparison_path=comparison_result.comparison_path,
        framework_run_path=framework_run_result.run_path,
        portfolio_comparison_path=portfolio_comparison_result.comparison_path,
        metric_extension_path=metric_extension_result.metric_extension_path,
        report_extension_path=report_extension_result.report_extension_path,
        stress_path=stress_result.stress_path,
        regime_split_path=regime_split_result.regime_split_path,
        rolling_stability_path=rolling_stability_result.rolling_stability_path,
        benchmark_relative_path=benchmark_relative_result.benchmark_relative_path,
        data_availability_path=data_availability_result.ledger_path,
        baseline_comparison_path=baseline_comparison_result.comparison_path,
        no_lookahead_path=no_lookahead_result.diff_path,
        execution_simulation_path=execution_simulation_result.simulation_path,
        assumption_ledger_path=assumption_ledger_result.ledger_path,
        trial_ledger_path=trial_ledger_result.ledger_path,
        suite_result_path=suite_artifacts["suite_result"],
    )


def _resolve_spec_data_path(raw_path: str, data_dir: Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else data_dir.parent / path


def _assert_manifest_artifact_keys(artifacts: dict[str, Path]) -> None:
    if set(artifacts) == set(PACK_MANIFEST_ARTIFACT_KEYS):
        return
    missing = sorted(set(PACK_MANIFEST_ARTIFACT_KEYS) - set(artifacts))
    extra = sorted(set(artifacts) - set(PACK_MANIFEST_ARTIFACT_KEYS))
    raise ValueError(f"pack manifest artifact keys mismatch: missing={missing} extra={extra}")
