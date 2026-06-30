from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.edge_candidates.protocol import CandidateProtocolManifest
from sis.settings import get_settings
from sis.strategy_inputs.io import StrategyInputIOError, read_mapping_file


def register_edge_candidate_commands(app: typer.Typer) -> None:
    @app.command("edge-candidate-protocol-validate")
    def edge_candidate_protocol_validate_cmd(
        protocol: Path = typer.Option(
            ...,
            "--protocol",
            dir_okay=False,
            help="candidate_protocol_manifest.v1 YAML/JSON.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            protocol_path = _resolve_workspace_path(protocol, settings.data_dir)
            manifest = CandidateProtocolManifest.model_validate(read_mapping_file(protocol_path))
        except (FileNotFoundError, StrategyInputIOError, ValidationError, ValueError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"protocol_id={manifest.protocol_id}")
        typer.echo(f"mode={manifest.mode.value}")
        typer.echo(f"family_count={len(manifest.families)}")
        typer.echo(f"permits_actual_cash={str(manifest.permits_actual_cash).lower()}")
        typer.echo(f"permits_live_order={str(manifest.permits_live_order).lower()}")
