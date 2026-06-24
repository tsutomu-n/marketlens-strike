from __future__ import annotations

from pathlib import Path

import typer

from sis.backtest.assumptions import build_strategy_backtest_assumption_ledger
from sis.backtest.baselines import build_strategy_backtest_baseline_comparison
from sis.backtest.data_availability import build_backtest_data_availability_ledger
from sis.backtest.execution_simulation import build_strategy_backtest_execution_simulation
from sis.backtest.no_lookahead import build_strategy_backtest_no_lookahead_diff
from sis.backtest.trial_ledger import build_strategy_backtest_trial_ledger
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_ledger_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-data-availability")
    def strategy_backtest_data_availability_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy Authoring signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Strategy Authoring quotes parquet.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_data_availability"),
            "--out",
            help="Output directory for data availability ledger.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_backtest_data_availability_ledger(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_data_availability={result.ledger_path}")
        typer.echo(f"backtest_data_availability_report={result.report_path}")

    @app.command("strategy-backtest-baseline-compare")
    def strategy_backtest_baseline_compare_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_baseline_comparison"),
            "--out",
            help="Output directory for baseline comparison artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_baseline_comparison(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_baseline_comparison={result.comparison_path}")
        typer.echo(f"backtest_baseline_comparison_report={result.report_path}")

    @app.command("strategy-backtest-no-lookahead-diff")
    def strategy_backtest_no_lookahead_diff_cmd(
        spec: Path | None = typer.Option(
            Path("docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml"),
            "--spec",
            help="Optional Strategy Authoring spec for runtime future-row mutation replay.",
        ),
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy Authoring signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Strategy Authoring quotes parquet.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_no_lookahead"),
            "--out",
            help="Output directory for no-lookahead diff artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_spec = (
            _resolve_workspace_path(spec, settings.data_dir) if spec is not None else None
        )
        try:
            result = build_strategy_backtest_no_lookahead_diff(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                spec_path=selected_spec,
                data_dir=settings.data_dir if selected_spec is not None else None,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_no_lookahead_diff={result.diff_path}")
        typer.echo(f"backtest_no_lookahead_diff_report={result.report_path}")

    @app.command("strategy-backtest-execution-sim")
    def strategy_backtest_execution_sim_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy Authoring signals parquet.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_execution_simulation"),
            "--out",
            help="Output directory for execution simulation artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_execution_simulation(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_execution_simulation={result.simulation_path}")
        typer.echo(f"backtest_execution_simulation_report={result.report_path}")

    @app.command("strategy-backtest-assumption-ledger")
    def strategy_backtest_assumption_ledger_cmd(
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Backtest Data Availability Ledger JSON.",
        ),
        baseline_comparison_path: Path = typer.Option(
            Path(
                "data/research/backtest_baseline_comparison/"
                "strategy_backtest_baseline_comparison.json"
            ),
            "--baseline-comparison-path",
            help="Strategy Backtest Baseline Comparison JSON.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Strategy Backtest No-Lookahead Diff JSON.",
        ),
        execution_simulation_path: Path = typer.Option(
            Path(
                "data/research/backtest_execution_simulation/"
                "strategy_backtest_execution_simulation.json"
            ),
            "--execution-simulation-path",
            help="Strategy Backtest Execution Simulation JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_assumption_ledger"),
            "--out",
            help="Output directory for assumption ledger artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_assumption_ledger(
                data_availability_path=_resolve_workspace_path(
                    data_availability_path, settings.data_dir
                ),
                baseline_comparison_path=_resolve_workspace_path(
                    baseline_comparison_path, settings.data_dir
                ),
                no_lookahead_path=_resolve_workspace_path(no_lookahead_path, settings.data_dir),
                execution_simulation_path=_resolve_workspace_path(
                    execution_simulation_path, settings.data_dir
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_assumption_ledger={result.ledger_path}")
        typer.echo(f"backtest_assumption_ledger_report={result.report_path}")

    @app.command("strategy-backtest-trial-ledger")
    def strategy_backtest_trial_ledger_cmd(
        out: Path = typer.Option(
            Path("data/research/backtest_trial_ledger"),
            "--out",
            help="Output directory for trial ledger artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        root = settings.data_dir.parent
        artifacts = {
            "backtest_metrics": root / "data/research/strategy_backtest_metrics.json",
            "suite_result": root
            / "data/research/backtest_suite/strategy_backtest_suite_result.json",
            "baseline_comparison": root
            / "data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json",
            "data_availability": root
            / "data/research/backtest_data_availability/backtest_data_availability_ledger.json",
            "no_lookahead_diff": root
            / "data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json",
            "execution_simulation": root
            / "data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json",
        }
        result = build_strategy_backtest_trial_ledger(
            artifacts=artifacts,
            out_dir=_resolve_workspace_path(out, settings.data_dir),
            reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
        )
        typer.echo(f"backtest_trial_ledger={result.ledger_path}")
        typer.echo(f"backtest_trial_ledger_report={result.report_path}")
