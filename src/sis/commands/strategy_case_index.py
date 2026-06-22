from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_case_index.service import (
    StrategyCaseIndexError,
    StrategyCaseIndexOutputExistsError,
    build_strategy_case_index,
)


def register_strategy_case_index_commands(app: typer.Typer) -> None:
    @app.command("strategy-case-index-build")
    def strategy_case_index_build_cmd(
        case: list[Path] | None = typer.Option(
            None,
            "--case",
            dir_okay=False,
            help="strategy_case_lite.v1 JSON. Repeatable.",
        ),
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Optional directory to scan recursively for strategy_case_lite.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_case_index"),
            "--out",
            help="Output directory for Strategy Case Index artifacts.",
        ),
        index_id: str | None = typer.Option(
            None,
            "--index-id",
            help="Optional index id. Defaults to latest case timestamp.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing index artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_case_index(
                case_paths=[
                    _resolve_workspace_path(path, settings.data_dir) for path in (case or [])
                ],
                data_dir=_resolve_workspace_path(data_dir, settings.data_dir)
                if data_dir is not None
                else None,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                index_id=index_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyCaseIndexOutputExistsError,
            StrategyCaseIndexError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        index = result.index
        typer.echo("status=pass")
        typer.echo(f"index_id={index.index_id}")
        typer.echo(f"case_count={index.case_count}")
        typer.echo(f"strategy_count={index.strategy_count}")
        typer.echo(f"paper_execution_allowed={str(index.paper_execution_allowed).lower()}")
        typer.echo(f"live_allowed={str(index.live_allowed).lower()}")
        typer.echo(
            f"db_persistence_allowed={str(index.index_boundary.db_persistence_allowed).lower()}"
        )
        typer.echo(f"index_path={result.index_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
