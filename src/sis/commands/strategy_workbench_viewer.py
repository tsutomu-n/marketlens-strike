from __future__ import annotations

from pathlib import Path

import typer

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_workbench_viewer.service import (
    StrategyWorkbenchViewerError,
    StrategyWorkbenchViewerOutputExistsError,
    build_strategy_workbench_viewer,
)


def register_strategy_workbench_viewer_commands(app: typer.Typer) -> None:
    @app.command("strategy-workbench-viewer-build")
    def strategy_workbench_viewer_build_cmd(
        artifact: list[Path] | None = typer.Option(
            None,
            "--artifact",
            dir_okay=False,
            help="Artifact path to include. Repeat for multiple JSON/Markdown/Text artifacts.",
        ),
        data_dir: Path = typer.Option(
            Path("data"),
            "--data-dir",
            help="Data directory to scan when --artifact is omitted.",
        ),
        out: Path = typer.Option(
            Path("data/reports/strategy_workbench_viewer"),
            "--out",
            help="Output directory for static viewer artifacts.",
        ),
        viewer_id: str = typer.Option(
            "strategy-workbench-viewer",
            "--viewer-id",
            help="Viewer manifest id.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing viewer artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            resolved_artifacts = (
                [_resolve_workspace_path(path, settings.data_dir) for path in artifact]
                if artifact
                else None
            )
            result = build_strategy_workbench_viewer(
                artifacts=resolved_artifacts,
                data_dir=_resolve_workspace_path(data_dir, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                viewer_id=viewer_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyWorkbenchViewerOutputExistsError,
            StrategyWorkbenchViewerError,
            FileNotFoundError,
            ValueError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"artifact_count={result.manifest.artifact_count}")
        typer.echo(f"boundary_violation_count={result.manifest.boundary_violation_count}")
        typer.echo(f"html_path={result.html_path.as_posix()}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")
