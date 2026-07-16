from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import typer

from sis.strategy_idea_seeds.common.errors import StrategyIdeaSeedError
from sis.strategy_idea_seeds.service import build_technical_seeds


def register_strategy_idea_seed_commands(app: typer.Typer) -> None:
    @app.command("strategy-idea-seeds-technical-build")
    def strategy_idea_seeds_technical_build_cmd(
        source_root: Path = typer.Option(
            ...,
            "--source-root",
            file_okay=False,
            help="Existing Source Root containing data/candles_5m and related artifacts.",
        ),
        mechanism_pack: Path = typer.Option(
            ...,
            "--mechanism-pack",
            dir_okay=False,
            help="Technical profit mechanism pack YAML.",
        ),
        operator_catalog: Path = typer.Option(
            ...,
            "--operator-catalog",
            dir_okay=False,
            help="Technical operator catalog YAML.",
        ),
        out: Path = typer.Option(
            ...,
            "--out",
            file_okay=False,
            help="New output directory for Seed Foundry A1 artifacts.",
        ),
    ) -> None:
        try:
            result = build_technical_seeds(
                source_root=source_root.resolve(),
                mechanism_pack_path=mechanism_pack.resolve(),
                operator_catalog_path=operator_catalog.resolve(),
                out_dir=out.resolve(),
            )
        except (
            StrategyIdeaSeedError,
            FileNotFoundError,
            OSError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"attempt_count={result.manifest.attempt_count}")
        typer.echo(f"seed_count={result.manifest.seed_count}")
        typer.echo(f"data_required_count={result.manifest.data_required_count}")
        typer.echo(f"seed_set_path={result.seed_set_path.as_posix()}")
        typer.echo(f"ledger_path={result.attempts_path.as_posix()}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")
