from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.edge_candidates.factory import (
    EdgeCandidateFactoryError,
    EdgeCandidateFactoryOutputExistsError,
    run_edge_candidate_factory,
)
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

    @app.command("edge-candidate-factory-run")
    def edge_candidate_factory_run_cmd(
        protocol: Path = typer.Option(
            ...,
            "--protocol",
            dir_okay=False,
            help="candidate_protocol_manifest.v1 YAML/JSON.",
        ),
        contract: Path = typer.Option(
            ...,
            "--contract",
            dir_okay=False,
            help="strategy_input_contract.v1 YAML/JSON.",
        ),
        validation: Path = typer.Option(
            ...,
            "--validation",
            dir_okay=False,
            help="strategy_input_contract_validation.v1 YAML/JSON.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidates/factory"),
            "--out",
            help="Output directory for Edge Candidate Factory artifacts.",
        ),
        candidate_set_id: str | None = typer.Option(
            None,
            "--candidate-set-id",
            help="Candidate set id. Defaults to contract id plus protocol id.",
        ),
        shortlist_count: int = typer.Option(1, "--shortlist-count", min=1),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = run_edge_candidate_factory(
                protocol_path=_resolve_workspace_path(protocol, settings.data_dir),
                contract_path=_resolve_workspace_path(contract, settings.data_dir),
                validation_path=_resolve_workspace_path(validation, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                candidate_set_id=candidate_set_id,
                shortlist_count=shortlist_count,
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            EdgeCandidateFactoryError,
            EdgeCandidateFactoryOutputExistsError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        summary = result.summary
        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"protocol_id={summary['protocol_ref']['protocol_id']}")
        typer.echo(f"candidate_set_id={result.candidate_set.candidate_set_id}")
        typer.echo(f"candidate_count_total={summary['candidate_count_total']}")
        typer.echo(f"candidate_count_shortlisted={summary['candidate_count_shortlisted']}")
        typer.echo(f"candidate_count_rejected={summary['candidate_count_rejected']}")
        typer.echo(f"unexecutable_reason_count={summary['unexecutable_reason_count']}")
        typer.echo(f"candidate_set_path={result.candidate_set_path.as_posix()}")
        typer.echo(f"search_ledger_path={result.search_ledger_path.as_posix()}")
        typer.echo(f"rejection_ledger_path={result.rejection_ledger_path.as_posix()}")
        typer.echo(f"account_path={result.multiplicity_account_path.as_posix()}")
        typer.echo(f"summary_path={result.summary_path.as_posix()}")
