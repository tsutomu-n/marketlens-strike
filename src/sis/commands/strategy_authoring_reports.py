from __future__ import annotations

from pathlib import Path

import typer

from sis.backtest.html_report import build_strategy_backtest_html_report
from sis.backtest.metric_extension import build_strategy_backtest_metric_extension
from sis.backtest.report_extension import build_strategy_backtest_report_extension
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_report_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-metric-extension")
    def strategy_backtest_metric_extension_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        frequency: str = typer.Option(
            "daily",
            "--frequency",
            help="Return frequency label for empyrical metrics: daily, weekly, monthly, or signal.",
        ),
        risk_free_rate: float = typer.Option(
            0.0,
            "--risk-free-rate",
            help="Risk-free rate passed to optional empyrical metrics.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_metric_extension"),
            "--out",
            help="Output directory for metric extension artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        if frequency not in {"daily", "weekly", "monthly", "signal"}:
            typer.echo("frequency must be one of: daily, weekly, monthly, signal")
            raise typer.Exit(2)
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_metric_extension(
                metrics_path=selected_metrics_path,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_metric_extension={result.metric_extension_path}")
        typer.echo(f"backtest_returns_series={result.returns_series_path}")
        typer.echo(f"backtest_metric_extension_report={result.report_path}")

    @app.command("strategy-backtest-report-extension")
    def strategy_backtest_report_extension_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        frequency: str = typer.Option(
            "daily",
            "--frequency",
            help="Return frequency label for quantstats report: daily, weekly, monthly, or signal.",
        ),
        risk_free_rate: float = typer.Option(
            0.0,
            "--risk-free-rate",
            help="Risk-free rate passed to optional quantstats report generation.",
        ),
        show_framework_warnings: bool = typer.Option(
            False,
            "--show-framework-warnings",
            help="Show warnings emitted by optional quantstats report generation.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_report_extension"),
            "--out",
            help="Output directory for report extension artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        if frequency not in {"daily", "weekly", "monthly", "signal"}:
            typer.echo("frequency must be one of: daily, weekly, monthly, signal")
            raise typer.Exit(2)
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_report_extension(
                metrics_path=selected_metrics_path,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                suppress_framework_warnings=not show_framework_warnings,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_report_extension={result.report_extension_path}")
        typer.echo(f"backtest_report_returns_series={result.returns_series_path}")
        if result.quantstats_html_path is not None:
            typer.echo(f"backtest_quantstats_html={result.quantstats_html_path}")
        typer.echo(f"backtest_report_extension_report={result.report_path}")

    @app.command("strategy-backtest-html-report")
    def strategy_backtest_html_report_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
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
        stress_path: Path = typer.Option(
            Path("data/research/backtest_stress/strategy_backtest_stress.json"),
            "--stress-path",
            help="Strategy backtest stress JSON.",
        ),
        rolling_stability_path: Path = typer.Option(
            Path(
                "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
            ),
            "--rolling-stability-path",
            help="Strategy backtest rolling stability JSON.",
        ),
        regime_split_path: Path = typer.Option(
            Path("data/research/backtest_regime_split/strategy_backtest_regime_split.json"),
            "--regime-split-path",
            help="Strategy backtest regime split JSON.",
        ),
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Backtest data availability ledger JSON.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Strategy backtest no-lookahead diff JSON.",
        ),
        comparison_path: Path = typer.Option(
            Path("data/research/backtest_compare/strategy_backtest_comparison.json"),
            "--comparison-path",
            help="Strategy backtest comparison JSON.",
        ),
        min_trade_count_for_candidate: int = typer.Option(
            30,
            "--min-trade-count-for-candidate",
            min=1,
            help="Minimum trade count before the HTML report may label a result paper-observation candidate.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_html_report"),
            "--out",
            help="Output directory for HTML report manifest artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_validation_path = _resolve_workspace_path(validation_path, settings.data_dir)
        selected_benchmark_relative_path = _resolve_workspace_path(
            benchmark_relative_path, settings.data_dir
        )
        selected_stress_path = _resolve_workspace_path(stress_path, settings.data_dir)
        selected_rolling_stability_path = _resolve_workspace_path(
            rolling_stability_path, settings.data_dir
        )
        selected_regime_split_path = _resolve_workspace_path(regime_split_path, settings.data_dir)
        selected_data_availability_path = _resolve_workspace_path(
            data_availability_path, settings.data_dir
        )
        selected_no_lookahead_path = _resolve_workspace_path(no_lookahead_path, settings.data_dir)
        selected_comparison_path = _resolve_workspace_path(comparison_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_html_report(
                metrics_path=selected_metrics_path,
                validation_path=selected_validation_path,
                benchmark_relative_path=selected_benchmark_relative_path,
                stress_path=selected_stress_path,
                rolling_stability_path=selected_rolling_stability_path,
                regime_split_path=selected_regime_split_path,
                data_availability_path=selected_data_availability_path,
                no_lookahead_path=selected_no_lookahead_path,
                comparison_path=selected_comparison_path,
                out_dir=selected_out,
                reports_dir=selected_reports,
                min_trade_count_for_candidate=min_trade_count_for_candidate,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_html_report={result.html_report_path}")
        typer.echo(f"backtest_html_report_manifest={result.manifest_path}")
        typer.echo(f"result_label={result.payload['result_label']['label']}")
