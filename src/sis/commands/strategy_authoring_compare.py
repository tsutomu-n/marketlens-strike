from __future__ import annotations

from pathlib import Path

import typer

from sis.backtest.compare import build_strategy_backtest_comparison
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def _existing_path_or_none(path: Path) -> Path | None:
    return path if path.exists() else None


def register_strategy_authoring_compare_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-compare")
    def strategy_backtest_compare_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        suite_result_path: Path = typer.Option(
            Path("data/research/backtest_suite/strategy_backtest_suite_result.json"),
            "--suite-result-path",
            help="Optional Strategy Backtest Suite result JSON. Used when the file exists.",
        ),
        adapter_spike_path: Path = typer.Option(
            Path("data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"),
            "--adapter-spike-path",
            help="Optional Strategy Backtest Adapter Spike JSON. Used when the file exists.",
        ),
        external_result_path: Path = typer.Option(
            Path("data/research/backtest_external/strategy_backtest_external_result.json"),
            "--external-result-path",
            help="Optional Strategy Backtest External Result JSON. Used when the file exists.",
        ),
        portfolio_comparison_path: Path = typer.Option(
            Path("data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json"),
            "--portfolio-comparison-path",
            help="Optional Strategy Backtest Portfolio Comparison JSON. Used when the file exists.",
        ),
        metric_extension_path: Path = typer.Option(
            Path("data/research/backtest_metric_extension/strategy_backtest_metric_extension.json"),
            "--metric-extension-path",
            help="Optional Strategy Backtest Metric Extension JSON. Used when the file exists.",
        ),
        report_extension_path: Path = typer.Option(
            Path("data/research/backtest_report_extension/strategy_backtest_report_extension.json"),
            "--report-extension-path",
            help="Optional Strategy Backtest Report Extension JSON. Used when the file exists.",
        ),
        stress_path: Path = typer.Option(
            Path("data/research/backtest_stress/strategy_backtest_stress.json"),
            "--stress-path",
            help="Optional Strategy Backtest Stress JSON. Used when the file exists.",
        ),
        regime_split_path: Path = typer.Option(
            Path("data/research/backtest_regime_split/strategy_backtest_regime_split.json"),
            "--regime-split-path",
            help="Optional Strategy Backtest Regime Split JSON. Used when the file exists.",
        ),
        rolling_stability_path: Path = typer.Option(
            Path(
                "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
            ),
            "--rolling-stability-path",
            help="Optional Strategy Backtest Rolling Stability JSON. Used when the file exists.",
        ),
        benchmark_relative_path: Path = typer.Option(
            Path(
                "data/research/backtest_benchmark_relative/"
                "strategy_backtest_benchmark_relative.json"
            ),
            "--benchmark-relative-path",
            help="Optional Strategy Backtest Benchmark Relative JSON. Used when the file exists.",
        ),
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Optional Backtest Data Availability Ledger JSON. Used when the file exists.",
        ),
        baseline_comparison_path: Path = typer.Option(
            Path(
                "data/research/backtest_baseline_comparison/"
                "strategy_backtest_baseline_comparison.json"
            ),
            "--baseline-comparison-path",
            help="Optional Strategy Backtest Baseline Comparison JSON. Used when the file exists.",
        ),
        trial_ledger_path: Path = typer.Option(
            Path("data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json"),
            "--trial-ledger-path",
            help="Optional Strategy Backtest Trial Ledger JSON. Used when the file exists.",
        ),
        assumption_ledger_path: Path = typer.Option(
            Path(
                "data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json"
            ),
            "--assumption-ledger-path",
            help="Optional Strategy Backtest Assumption Ledger JSON. Used when the file exists.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Optional Strategy Backtest No-Lookahead Diff JSON. Used when the file exists.",
        ),
        execution_simulation_path: Path = typer.Option(
            Path(
                "data/research/backtest_execution_simulation/"
                "strategy_backtest_execution_simulation.json"
            ),
            "--execution-simulation-path",
            help="Optional Strategy Backtest Execution Simulation JSON. Used when the file exists.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_compare"),
            "--out",
            help="Output directory for comparison artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_suite_result_path = _resolve_workspace_path(suite_result_path, settings.data_dir)
        selected_adapter_spike_path = _resolve_workspace_path(adapter_spike_path, settings.data_dir)
        selected_external_result_path = _resolve_workspace_path(
            external_result_path, settings.data_dir
        )
        selected_portfolio_comparison_path = _resolve_workspace_path(
            portfolio_comparison_path, settings.data_dir
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
        selected_benchmark_relative_path = _resolve_workspace_path(
            benchmark_relative_path, settings.data_dir
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
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_comparison(
                metrics_path=selected_metrics_path,
                suite_result_path=_existing_path_or_none(selected_suite_result_path),
                adapter_spike_path=_existing_path_or_none(selected_adapter_spike_path),
                external_result_path=_existing_path_or_none(selected_external_result_path),
                portfolio_comparison_path=_existing_path_or_none(
                    selected_portfolio_comparison_path
                ),
                metric_extension_path=_existing_path_or_none(selected_metric_extension_path),
                report_extension_path=_existing_path_or_none(selected_report_extension_path),
                stress_path=_existing_path_or_none(selected_stress_path),
                regime_split_path=_existing_path_or_none(selected_regime_split_path),
                rolling_stability_path=_existing_path_or_none(selected_rolling_stability_path),
                benchmark_relative_path=_existing_path_or_none(selected_benchmark_relative_path),
                data_availability_path=_existing_path_or_none(selected_data_availability_path),
                baseline_comparison_path=_existing_path_or_none(selected_baseline_comparison_path),
                trial_ledger_path=_existing_path_or_none(selected_trial_ledger_path),
                assumption_ledger_path=_existing_path_or_none(selected_assumption_ledger_path),
                no_lookahead_path=_existing_path_or_none(selected_no_lookahead_path),
                execution_simulation_path=_existing_path_or_none(
                    selected_execution_simulation_path
                ),
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_comparison={result.comparison_path}")
        typer.echo(f"backtest_comparison_report={result.report_path}")
