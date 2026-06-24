from __future__ import annotations

from pathlib import Path

import typer

from sis.backtest.benchmark_relative import (
    DEFAULT_BENCHMARK_RETURN_COLUMN,
    DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
    DEFAULT_HORIZON_MINUTES,
    DEFAULT_PRICE_COLUMN,
    build_strategy_backtest_benchmark_relative,
)
from sis.backtest.regime_split import (
    DEFAULT_DIMENSION_CSV,
    build_strategy_backtest_regime_split,
)
from sis.backtest.rolling_stability import (
    DEFAULT_WINDOW_CSV,
    build_strategy_backtest_rolling_stability,
)
from sis.backtest.stress import DEFAULT_SCENARIO_CSV, build_strategy_backtest_stress
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_quality_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-stress")
    def strategy_backtest_stress_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        scenario_csv: str = typer.Option(
            DEFAULT_SCENARIO_CSV,
            "--scenario-csv",
            help="Comma-separated stress scenarios as id:additional_cost_bps:additional_slippage_bps.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_stress"),
            "--out",
            help="Output directory for stress artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_stress(
                metrics_path=selected_metrics_path,
                scenario_csv=scenario_csv,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_stress={result.stress_path}")
        typer.echo(f"backtest_stress_report={result.report_path}")

    @app.command("strategy-backtest-regime-split")
    def strategy_backtest_regime_split_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        dimension_csv: str = typer.Option(
            DEFAULT_DIMENSION_CSV,
            "--dimension-csv",
            help="Comma-separated dimensions. Supports row fields plus ts_date, ts_weekday, and ts_hour.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_regime_split"),
            "--out",
            help="Output directory for regime split artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_regime_split(
                metrics_path=selected_metrics_path,
                dimension_csv=dimension_csv,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_regime_split={result.regime_split_path}")
        typer.echo(f"backtest_regime_split_report={result.report_path}")

    @app.command("strategy-backtest-rolling-stability")
    def strategy_backtest_rolling_stability_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        window_csv: str = typer.Option(
            DEFAULT_WINDOW_CSV,
            "--window-csv",
            help="Comma-separated positive integer rolling return window sizes.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_rolling_stability"),
            "--out",
            help="Output directory for rolling stability artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_rolling_stability(
                metrics_path=selected_metrics_path,
                window_csv=window_csv,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_rolling_stability={result.rolling_stability_path}")
        typer.echo(f"backtest_rolling_stability_report={result.report_path}")

    @app.command("strategy-backtest-benchmark-relative")
    def strategy_backtest_benchmark_relative_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Optional quote parquet used to derive benchmark returns.",
        ),
        benchmark_series_path: Path | None = typer.Option(
            None,
            "--benchmark-series-path",
            help="Optional local benchmark return series file. Supports parquet, csv, jsonl, ndjson, and json.",
        ),
        benchmark_return_column: str = typer.Option(
            DEFAULT_BENCHMARK_RETURN_COLUMN,
            "--benchmark-return-column",
            help="Executed signal result column used when row-level benchmark returns exist.",
        ),
        benchmark_series_return_column: str = typer.Option(
            DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
            "--benchmark-series-return-column",
            help="Benchmark return column in --benchmark-series-path.",
        ),
        price_column: str = typer.Option(
            DEFAULT_PRICE_COLUMN,
            "--price-column",
            help="Quote price column used to derive benchmark returns.",
        ),
        horizon_minutes: int = typer.Option(
            DEFAULT_HORIZON_MINUTES,
            "--horizon-minutes",
            help="Benchmark return horizon in minutes when using quote data.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_benchmark_relative"),
            "--out",
            help="Output directory for benchmark-relative artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_quotes_path = _resolve_workspace_path(quotes_path, settings.data_dir)
        selected_benchmark_series_path = (
            _resolve_workspace_path(benchmark_series_path, settings.data_dir)
            if benchmark_series_path is not None
            else None
        )
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_benchmark_relative(
                metrics_path=selected_metrics_path,
                quotes_path=selected_quotes_path if selected_quotes_path.exists() else None,
                benchmark_series_path=selected_benchmark_series_path,
                benchmark_return_column=benchmark_return_column,
                benchmark_series_return_column=benchmark_series_return_column,
                price_column=price_column,
                horizon_minutes=horizon_minutes,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_benchmark_relative={result.benchmark_relative_path}")
        typer.echo(f"backtest_benchmark_relative_report={result.report_path}")
