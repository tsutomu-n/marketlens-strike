from __future__ import annotations

from pathlib import Path

import typer

from sis.backtest.portfolio_comparison import build_strategy_backtest_portfolio_comparison
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_portfolio_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-portfolio-compare")
    def strategy_backtest_portfolio_compare_cmd(
        bundle_path: Path = typer.Option(
            Path("data/research/strategy_authoring_bundle_result.json"),
            "--bundle-path",
            help="Strategy Authoring bundle result JSON.",
        ),
        price_frame_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--price-frame-path",
            help="Quotes or price frame parquet used by the optional bt adapter.",
        ),
        allocation_rule_id: str = typer.Option(
            "fixed_weight",
            "--allocation-rule-id",
            help="Allocation rule label recorded in the portfolio comparison artifact.",
        ),
        rebalance_cadence: str = typer.Option(
            "initial_only",
            "--rebalance-cadence",
            help="Rebalance cadence label recorded in the portfolio comparison artifact.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_portfolio"),
            "--out",
            help="Output directory for portfolio comparison artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_bundle_path = _resolve_workspace_path(bundle_path, settings.data_dir)
        selected_price_frame_path = _resolve_workspace_path(price_frame_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_portfolio_comparison(
                bundle_path=selected_bundle_path,
                price_frame_path=selected_price_frame_path,
                allocation_rule_id=allocation_rule_id,
                rebalance_cadence=rebalance_cadence,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_portfolio_comparison={result.comparison_path}")
        typer.echo(f"backtest_portfolio_comparison_report={result.report_path}")
