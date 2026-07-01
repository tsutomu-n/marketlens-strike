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
from sis.edge_candidates.evidence_packet import (
    ProfitCoreEvidencePacketError,
    ProfitCoreEvidencePacketOutputExistsError,
    build_and_write_profit_core_evidence_packet,
)
from sis.edge_candidates.protocol import CandidateProtocolManifest
from sis.edge_candidates.virtual_execution_gate import (
    VirtualExecutionGateError,
    VirtualExecutionGateOutputExistsError,
    build_and_write_virtual_execution_gate,
)
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

    @app.command("edge-candidate-virtual-gate-run")
    def edge_candidate_virtual_gate_run_cmd(
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="strategy_idea_candidate_set.v1 JSON.",
        ),
        factory_summary: Path = typer.Option(
            ...,
            "--factory-summary",
            dir_okay=False,
            help="edge_candidate_factory_summary.v1 JSON.",
        ),
        multiplicity_account: Path = typer.Option(
            ...,
            "--multiplicity-account",
            dir_okay=False,
            help="trial_multiplicity_account.v1 JSON.",
        ),
        backtest_kill_gate: Path = typer.Option(
            ...,
            "--backtest-kill-gate",
            dir_okay=False,
            help="candidate-scoped backtest_kill_gate.v1 JSON.",
        ),
        candidate_id: str = typer.Option(..., "--candidate-id"),
        out: Path = typer.Option(
            Path("data/edge_candidates/virtual_gate"),
            "--out",
            help="Output directory for virtual_execution_gate.json.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_and_write_virtual_execution_gate(
                candidate_set_path=_resolve_workspace_path(candidate_set, settings.data_dir),
                factory_summary_path=_resolve_workspace_path(factory_summary, settings.data_dir),
                multiplicity_account_path=_resolve_workspace_path(
                    multiplicity_account, settings.data_dir
                ),
                backtest_kill_gate_path=_resolve_workspace_path(
                    backtest_kill_gate, settings.data_dir
                ),
                candidate_id=candidate_id,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            VirtualExecutionGateError,
            VirtualExecutionGateOutputExistsError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("network_attempted=false")
        typer.echo("exchange_write_used=false")
        typer.echo("live_order_submitted=false")
        typer.echo("status=pass")
        typer.echo(f"candidate_id={result.gate.candidate_id}")
        typer.echo(f"gate_state={result.gate.gate_state.value}")
        typer.echo(f"blocker_count={len(result.gate.blocker_codes)}")
        typer.echo(f"gate_path={result.gate_path.as_posix()}")

    @app.command("edge-candidate-evidence-packet-build")
    def edge_candidate_evidence_packet_build_cmd(
        protocol: Path = typer.Option(
            ...,
            "--protocol",
            dir_okay=False,
            help="candidate_protocol_manifest.v1 YAML/JSON.",
        ),
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="strategy_idea_candidate_set.v1 JSON.",
        ),
        bridge_manifest: Path = typer.Option(
            ...,
            "--bridge-manifest",
            dir_okay=False,
            help="strategy_idea_candidate_authoring_bridge.v1 JSON.",
        ),
        multiplicity_account: Path = typer.Option(
            ...,
            "--multiplicity-account",
            dir_okay=False,
            help="trial_multiplicity_account.v1 JSON.",
        ),
        backtest_kill_gate: Path = typer.Option(
            ...,
            "--backtest-kill-gate",
            dir_okay=False,
            help="candidate-scoped backtest_kill_gate.v1 JSON.",
        ),
        virtual_gate: Path = typer.Option(
            ...,
            "--virtual-gate",
            dir_okay=False,
            help="candidate-scoped virtual_execution_gate.v1 JSON.",
        ),
        claims: Path | None = typer.Option(
            None,
            "--claims",
            dir_okay=False,
            help="Optional JSON/YAML file containing a claims list.",
        ),
        risk_review_source: list[Path] | None = typer.Option(
            None,
            "--risk-review-source",
            dir_okay=False,
            help="Optional risk review source artifact. Repeat for multiple sources.",
        ),
        candidate_id: str = typer.Option(..., "--candidate-id"),
        out: Path = typer.Option(
            Path("data/edge_candidates/evidence_packet"),
            "--out",
            help="Output directory for profit_core_evidence_packet.json.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_and_write_profit_core_evidence_packet(
                protocol_path=_resolve_workspace_path(protocol, settings.data_dir),
                candidate_set_path=_resolve_workspace_path(candidate_set, settings.data_dir),
                bridge_manifest_path=_resolve_workspace_path(
                    bridge_manifest,
                    settings.data_dir,
                ),
                multiplicity_account_path=_resolve_workspace_path(
                    multiplicity_account,
                    settings.data_dir,
                ),
                backtest_kill_gate_path=_resolve_workspace_path(
                    backtest_kill_gate,
                    settings.data_dir,
                ),
                virtual_gate_path=_resolve_workspace_path(virtual_gate, settings.data_dir),
                claims_path=(
                    _resolve_workspace_path(claims, settings.data_dir)
                    if claims is not None
                    else None
                ),
                risk_review_source_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (risk_review_source or [])
                ],
                candidate_id=candidate_id,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            ProfitCoreEvidencePacketOutputExistsError,
            ProfitCoreEvidencePacketError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        boundary = result.packet.boundary
        typer.echo("network_attempted=false")
        typer.echo(f"llm_api_used={str(boundary['llm_api_used']).lower()}")
        typer.echo(f"actual_cash={str(boundary['actual_cash']).lower()}")
        typer.echo(f"exchange_write_used={str(boundary['production_exchange_write_used']).lower()}")
        typer.echo(f"live_order_submitted={str(boundary['live_order_submitted']).lower()}")
        typer.echo("status=pass")
        typer.echo(f"candidate_id={result.packet.candidate_id}")
        typer.echo(f"finding_count={len(result.packet.claim_findings)}")
        typer.echo(f"packet_path={result.packet_path.as_posix()}")
