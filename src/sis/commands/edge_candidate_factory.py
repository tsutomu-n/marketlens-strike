from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.edge_candidate_factory.generator import (
    EdgeCandidateFactoryConfig,
    EdgeCandidateFactoryError,
    EdgeCandidateFactoryOutputExistsError,
    build_edge_candidate_factory_run,
    write_edge_candidate_factory_run,
)
from sis.settings import get_settings
from sis.strategy_review.provenance import repo_relative_path


def _echo_safe_stdout_prefix() -> None:
    typer.echo("network_attempted=false")
    typer.echo("credentials_used=false")
    typer.echo("exchange_write_used=false")
    typer.echo("production_exchange_write_used=false")
    typer.echo("live_order_submitted=false")
    typer.echo("permits_live_order=false")


def register_edge_candidate_factory_commands(app: typer.Typer) -> None:
    @app.command("edge-candidate-factory-build")
    def edge_candidate_factory_build_cmd(
        source_root: Path = typer.Option(
            ...,
            "--source-root",
            file_okay=False,
            help="Local source root to record. T4 records this path without scanning it.",
        ),
        symbol: list[str] = typer.Option(
            ...,
            "--symbol",
            help="Symbol such as BTCUSDT. Repeat for multiple symbols.",
        ),
        product_type: str = typer.Option(
            "USDT-FUTURES",
            "--product-type",
            help="Product type recorded in the generated config.",
        ),
        timeframe: str = typer.Option(
            "5m",
            "--timeframe",
            help="Candidate timeframe recorded in the generated config.",
        ),
        family: list[str] | None = typer.Option(
            None,
            "--family",
            help="Smart prior family id. Repeat to select multiple families.",
        ),
        candidate_cap: int = typer.Option(10, "--candidate-cap", min=1),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory"),
            "--out",
            help="Output directory for edge candidate factory artifacts.",
        ),
        run_id: str | None = typer.Option(
            None,
            "--run-id",
            help="Run id. Defaults to edge-candidate-YYYYmmddTHHMMSSZ.",
        ),
        venue_id: str = typer.Option("bitget", "--venue-id"),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_source_root = _resolve_workspace_path(source_root, settings.data_dir)
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        generated_at = datetime.now(timezone.utc).replace(microsecond=0)
        resolved_run_id = run_id or f"edge-candidate-{generated_at:%Y%m%dT%H%M%SZ}"
        try:
            config = EdgeCandidateFactoryConfig(
                run_id=resolved_run_id,
                generated_at=generated_at,
                source_root=repo_relative_path(resolved_source_root),
                symbols=symbol,
                product_type=product_type,
                timeframe=timeframe,
                families=family or [],
                candidate_cap=candidate_cap,
                venue_id=venue_id,
            )
            run = build_edge_candidate_factory_run(config)
            result = write_edge_candidate_factory_run(
                run=run,
                out_dir=resolved_out,
                replace_existing=replace_existing,
            )
        except (
            EdgeCandidateFactoryError,
            EdgeCandidateFactoryOutputExistsError,
            ValueError,
            ValidationError,
        ) as exc:
            _echo_safe_stdout_prefix()
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        _echo_safe_stdout_prefix()
        typer.echo("status=pass")
        typer.echo(f"run_id={run.report.report_id}")
        typer.echo(f"candidate_count_total={run.report.candidate_count_total}")
        typer.echo(f"search_row_count={len(run.search_ledger_rows)}")
        typer.echo(f"rejection_row_count={len(run.rejection_rows)}")
        typer.echo(f"artifact_path={result.report_path.as_posix()}")
        typer.echo(f"smart_candidate_prior_report_path={result.report_path.as_posix()}")
        typer.echo(f"report_path={result.report_markdown_path.as_posix()}")
        typer.echo(f"search_ledger_path={result.search_ledger_path.as_posix()}")
        typer.echo(f"trial_multiplicity_account_path={result.multiplicity_account_path.as_posix()}")
        typer.echo(f"candidate_rejections_path={result.rejection_ledger_path.as_posix()}")
        typer.echo(f"known_gap_count={len(run.report.known_gaps)}")
