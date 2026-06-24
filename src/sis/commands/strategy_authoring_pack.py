from __future__ import annotations

import json
from pathlib import Path

import typer

from sis.backtest.artifact_summary import build_strategy_backtest_artifact_summary
from sis.backtest.benchmark_relative import DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN
from sis.backtest.pack import validate_strategy_backtest_pack
from sis.backtest.pack_runner import (
    StrategyBacktestPackRunInputs,
    run_strategy_backtest_pack,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_pack_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-pack")
    def strategy_backtest_pack_cmd(
        spec: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml"),
            "--spec",
            help="Strategy Authoring spec used for the canonical single backtest metrics.",
        ),
        suite: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/backtest_suite.yaml"),
            "--suite",
            help="Strategy Backtest Suite YAML used for multi-method backtests.",
        ),
        bundle: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml"),
            "--bundle",
            help="Strategy Authoring bundle YAML used for portfolio allocation comparison.",
        ),
        label_horizon_minutes: int = typer.Option(
            240,
            "--label-horizon-minutes",
            help="Holding horizon used to build optional external framework exits.",
        ),
        benchmark_series_path: Path | None = typer.Option(
            None,
            "--benchmark-series-path",
            help="Optional local benchmark return series file passed to benchmark-relative artifact generation.",
        ),
        benchmark_series_return_column: str = typer.Option(
            DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
            "--benchmark-series-return-column",
            help="Benchmark return column in --benchmark-series-path.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_pack"),
            "--out",
            help="Output directory for the pack manifest.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_spec = _resolve_workspace_path(spec, settings.data_dir)
        selected_suite = _resolve_workspace_path(suite, settings.data_dir)
        selected_bundle = _resolve_workspace_path(bundle, settings.data_dir)
        selected_benchmark_series_path = (
            _resolve_workspace_path(benchmark_series_path, settings.data_dir)
            if benchmark_series_path is not None
            else None
        )
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            run_result = run_strategy_backtest_pack(
                StrategyBacktestPackRunInputs(
                    spec_path=selected_spec,
                    suite_path=selected_suite,
                    bundle_path=selected_bundle,
                    label_horizon_minutes=label_horizon_minutes,
                    benchmark_series_path=selected_benchmark_series_path,
                    benchmark_series_return_column=benchmark_series_return_column,
                    out_dir=selected_out,
                    reports_dir=selected_reports,
                    data_dir=settings.data_dir,
                )
            )
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_pack={run_result.pack_path}")
        typer.echo(f"backtest_pack_report={run_result.pack_report_path}")
        typer.echo(f"backtest_pack_validation={run_result.validation_path}")
        typer.echo(f"backtest_pack_validation_report={run_result.validation_report_path}")
        typer.echo(f"backtest_comparison={run_result.comparison_path}")
        typer.echo(f"backtest_framework_run={run_result.framework_run_path}")
        typer.echo(f"backtest_portfolio_comparison={run_result.portfolio_comparison_path}")
        typer.echo(f"backtest_metric_extension={run_result.metric_extension_path}")
        typer.echo(f"backtest_report_extension={run_result.report_extension_path}")
        typer.echo(f"backtest_stress={run_result.stress_path}")
        typer.echo(f"backtest_regime_split={run_result.regime_split_path}")
        typer.echo(f"backtest_rolling_stability={run_result.rolling_stability_path}")
        typer.echo(f"backtest_benchmark_relative={run_result.benchmark_relative_path}")
        typer.echo(f"backtest_data_availability={run_result.data_availability_path}")
        typer.echo(f"backtest_baseline_comparison={run_result.baseline_comparison_path}")
        typer.echo(f"backtest_no_lookahead_diff={run_result.no_lookahead_path}")
        typer.echo(f"backtest_execution_simulation={run_result.execution_simulation_path}")
        typer.echo(f"backtest_assumption_ledger={run_result.assumption_ledger_path}")
        typer.echo(f"backtest_trial_ledger={run_result.trial_ledger_path}")
        typer.echo(f"backtest_suite_result={run_result.suite_result_path}")
        if run_result.validation_decision != "PASS":
            raise typer.Exit(2)

    @app.command("strategy-backtest-pack-validate")
    def strategy_backtest_pack_validate_cmd(
        pack_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack.json"),
            "--pack-path",
            help="Strategy backtest pack manifest JSON.",
        ),
        min_suite_method_count: int = typer.Option(
            5,
            "--min-suite-method-count",
            help="Minimum required suite method count.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_pack"),
            "--out",
            help="Output directory for the validation artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_pack_path = _resolve_workspace_path(pack_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = validate_strategy_backtest_pack(
                pack_path=selected_pack_path,
                out_dir=selected_out,
                reports_dir=selected_reports,
                min_suite_method_count=min_suite_method_count,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_pack_validation={result.validation_path}")
        typer.echo(f"backtest_pack_validation_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")
        if result.payload["decision"] != "PASS":
            raise typer.Exit(2)

    @app.command("strategy-backtest-artifact-summary")
    def strategy_backtest_artifact_summary_cmd(
        pack_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack.json"),
            "--pack-path",
            help="Strategy backtest pack manifest JSON.",
        ),
        validation_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack_validation.json"),
            "--validation-path",
            help="Strategy backtest pack validation JSON.",
        ),
        benchmark_relative_path: Path = typer.Option(
            Path(
                "data/research/backtest_benchmark_relative/"
                "strategy_backtest_benchmark_relative.json"
            ),
            "--benchmark-relative-path",
            help="Strategy backtest benchmark-relative JSON.",
        ),
        metric_extension_path: Path = typer.Option(
            Path("data/research/backtest_metric_extension/strategy_backtest_metric_extension.json"),
            "--metric-extension-path",
            help="Strategy backtest metric extension JSON.",
        ),
        report_extension_path: Path = typer.Option(
            Path("data/research/backtest_report_extension/strategy_backtest_report_extension.json"),
            "--report-extension-path",
            help="Strategy backtest report extension JSON.",
        ),
        stress_path: Path = typer.Option(
            Path("data/research/backtest_stress/strategy_backtest_stress.json"),
            "--stress-path",
            help="Strategy backtest stress JSON.",
        ),
        regime_split_path: Path = typer.Option(
            Path("data/research/backtest_regime_split/strategy_backtest_regime_split.json"),
            "--regime-split-path",
            help="Strategy backtest regime split JSON.",
        ),
        rolling_stability_path: Path = typer.Option(
            Path(
                "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
            ),
            "--rolling-stability-path",
            help="Strategy backtest rolling stability JSON.",
        ),
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Backtest data availability ledger JSON.",
        ),
        baseline_comparison_path: Path = typer.Option(
            Path(
                "data/research/backtest_baseline_comparison/"
                "strategy_backtest_baseline_comparison.json"
            ),
            "--baseline-comparison-path",
            help="Strategy backtest baseline comparison JSON.",
        ),
        trial_ledger_path: Path = typer.Option(
            Path("data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json"),
            "--trial-ledger-path",
            help="Strategy backtest trial ledger JSON.",
        ),
        assumption_ledger_path: Path = typer.Option(
            Path(
                "data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json"
            ),
            "--assumption-ledger-path",
            help="Strategy backtest assumption ledger JSON.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Strategy backtest no-lookahead diff JSON.",
        ),
        execution_simulation_path: Path = typer.Option(
            Path(
                "data/research/backtest_execution_simulation/"
                "strategy_backtest_execution_simulation.json"
            ),
            "--execution-simulation-path",
            help="Strategy backtest execution simulation JSON.",
        ),
        comparison_path: Path = typer.Option(
            Path("data/research/backtest_compare/strategy_backtest_comparison.json"),
            "--comparison-path",
            help="Strategy backtest comparison JSON.",
        ),
    ) -> None:
        settings = get_settings()
        selected_pack_path = _resolve_workspace_path(pack_path, settings.data_dir)
        selected_validation_path = _resolve_workspace_path(validation_path, settings.data_dir)
        selected_benchmark_relative_path = _resolve_workspace_path(
            benchmark_relative_path, settings.data_dir
        )
        selected_metric_extension_path = _resolve_workspace_path(
            metric_extension_path, settings.data_dir
        )
        selected_report_extension_path = _resolve_workspace_path(
            report_extension_path, settings.data_dir
        )
        selected_stress_path = _resolve_workspace_path(stress_path, settings.data_dir)
        selected_regime_split_path = _resolve_workspace_path(regime_split_path, settings.data_dir)
        selected_rolling_stability_path = _resolve_workspace_path(
            rolling_stability_path, settings.data_dir
        )
        selected_data_availability_path = _resolve_workspace_path(
            data_availability_path, settings.data_dir
        )
        selected_baseline_comparison_path = _resolve_workspace_path(
            baseline_comparison_path, settings.data_dir
        )
        selected_trial_ledger_path = _resolve_workspace_path(trial_ledger_path, settings.data_dir)
        selected_assumption_ledger_path = _resolve_workspace_path(
            assumption_ledger_path, settings.data_dir
        )
        selected_no_lookahead_path = _resolve_workspace_path(no_lookahead_path, settings.data_dir)
        selected_execution_simulation_path = _resolve_workspace_path(
            execution_simulation_path, settings.data_dir
        )
        selected_comparison_path = _resolve_workspace_path(comparison_path, settings.data_dir)
        try:
            result = build_strategy_backtest_artifact_summary(
                pack_path=selected_pack_path,
                validation_path=selected_validation_path,
                benchmark_relative_path=selected_benchmark_relative_path,
                metric_extension_path=selected_metric_extension_path,
                report_extension_path=selected_report_extension_path,
                stress_path=selected_stress_path,
                regime_split_path=selected_regime_split_path,
                rolling_stability_path=selected_rolling_stability_path,
                data_availability_path=selected_data_availability_path,
                baseline_comparison_path=selected_baseline_comparison_path,
                trial_ledger_path=selected_trial_ledger_path,
                assumption_ledger_path=selected_assumption_ledger_path,
                no_lookahead_path=selected_no_lookahead_path,
                execution_simulation_path=selected_execution_simulation_path,
                comparison_path=selected_comparison_path,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(json.dumps(result.payload, ensure_ascii=False, sort_keys=True))
