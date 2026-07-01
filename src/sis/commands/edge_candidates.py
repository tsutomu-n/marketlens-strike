from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.edge_candidates.actual_cash_readiness import (
    ActualCashReadinessPacketError,
    ActualCashReadinessPacketOutputExistsError,
    ProfitCoreActualCashReadinessStatus,
    build_and_write_actual_cash_readiness_packet,
)
from sis.edge_candidates.adversarial_review import (
    ProfitCoreAdversarialReviewError,
    ProfitCoreAdversarialReviewOutputExistsError,
    build_and_write_profit_core_adversarial_review,
)
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
from sis.edge_candidates.risk_taker_sprint_isolation import (
    RiskTakerSprintIsolationError,
    RiskTakerSprintIsolationOutputExistsError,
    build_and_write_risk_taker_sprint_isolation,
)
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

    @app.command("edge-candidate-adversarial-review-record")
    def edge_candidate_adversarial_review_record_cmd(
        evidence_packet: Path = typer.Option(
            ...,
            "--evidence-packet",
            dir_okay=False,
            help="profit_core_evidence_packet.v1 JSON.",
        ),
        manual_review: Path | None = typer.Option(
            None,
            "--manual-review",
            dir_okay=False,
            help="Optional JSON/YAML file containing manual adversarial findings.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidates/adversarial_review"),
            "--out",
            help="Output directory for profit_core_adversarial_review.json.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_and_write_profit_core_adversarial_review(
                evidence_packet_path=_resolve_workspace_path(
                    evidence_packet,
                    settings.data_dir,
                ),
                manual_review_path=(
                    _resolve_workspace_path(manual_review, settings.data_dir)
                    if manual_review is not None
                    else None
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            ProfitCoreAdversarialReviewOutputExistsError,
            ProfitCoreAdversarialReviewError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        boundary = result.review.boundary
        typer.echo("network_attempted=false")
        typer.echo(f"llm_api_used={str(boundary['llm_api_used']).lower()}")
        typer.echo(f"external_send_performed={str(boundary['external_send_performed']).lower()}")
        typer.echo(f"approval_allowed={str(result.review.approval_allowed).lower()}")
        typer.echo(f"permission_allowed={str(result.review.permission_allowed).lower()}")
        typer.echo("status=pass")
        typer.echo(f"candidate_id={result.review.candidate_id}")
        typer.echo(f"review_status={result.review.review_status.value}")
        typer.echo(f"finding_count={len(result.review.findings)}")
        typer.echo(f"hard_blocker_count={result.review.hard_blocker_count}")
        typer.echo(f"review_path={result.review_path.as_posix()}")

    @app.command("edge-candidate-actual-cash-readiness-packet-build")
    def edge_candidate_actual_cash_readiness_packet_build_cmd(
        evidence_packet: Path = typer.Option(
            ...,
            "--evidence-packet",
            dir_okay=False,
            help="profit_core_evidence_packet.v1 JSON.",
        ),
        adversarial_review: Path = typer.Option(
            ...,
            "--adversarial-review",
            dir_okay=False,
            help="profit_core_adversarial_review.v1 JSON.",
        ),
        readiness_plan: Path = typer.Option(
            ...,
            "--readiness-plan",
            dir_okay=False,
            help="Local JSON/YAML actual-cash readiness plan.",
        ),
        risk_sprint_isolation: Path | None = typer.Option(
            None,
            "--risk-sprint-isolation",
            dir_okay=False,
            help="Optional profit_core_risk_taker_sprint_isolation.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidates/actual_cash_readiness"),
            "--out",
            help="Output directory for profit_core_actual_cash_readiness_packet.json.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_and_write_actual_cash_readiness_packet(
                evidence_packet_path=_resolve_workspace_path(
                    evidence_packet,
                    settings.data_dir,
                ),
                adversarial_review_path=_resolve_workspace_path(
                    adversarial_review,
                    settings.data_dir,
                ),
                readiness_plan_path=_resolve_workspace_path(
                    readiness_plan,
                    settings.data_dir,
                ),
                risk_sprint_isolation_path=(
                    _resolve_workspace_path(risk_sprint_isolation, settings.data_dir)
                    if risk_sprint_isolation is not None
                    else None
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            ActualCashReadinessPacketOutputExistsError,
            ActualCashReadinessPacketError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        packet = result.packet
        typer.echo("network_attempted=false")
        typer.echo(f"credential_used={str(packet.credential_used).lower()}")
        typer.echo(f"exchange_write_used={str(packet.exchange_write_used).lower()}")
        typer.echo(f"exchange_write_allowed={str(packet.exchange_write_allowed).lower()}")
        typer.echo(
            f"actual_cash_execution_allowed={str(packet.actual_cash_execution_allowed).lower()}"
        )
        typer.echo(f"live_order_submitted={str(packet.live_order_submitted).lower()}")
        typer.echo(
            "status=pass"
            if packet.readiness_status
            is ProfitCoreActualCashReadinessStatus.PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL
            else "status=blocked"
        )
        typer.echo(f"candidate_id={packet.candidate_id}")
        typer.echo(f"readiness_status={packet.readiness_status.value}")
        typer.echo(f"blocker_count={len(packet.blockers)}")
        typer.echo(f"packet_path={result.packet_path.as_posix()}")

    @app.command("edge-candidate-risk-taker-sprint-isolation-record")
    def edge_candidate_risk_taker_sprint_isolation_record_cmd(
        protocol: Path = typer.Option(
            ...,
            "--protocol",
            dir_okay=False,
            help="risk_taker_sprint candidate_protocol_manifest.v1 YAML/JSON.",
        ),
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="risk_taker_sprint strategy_idea_candidate_set.v1 JSON.",
        ),
        search_ledger: Path = typer.Option(
            ...,
            "--search-ledger",
            dir_okay=False,
            help="risk_taker_sprint search ledger JSONL.",
        ),
        multiplicity_account: Path = typer.Option(
            ...,
            "--multiplicity-account",
            dir_okay=False,
            help="risk_taker_sprint trial_multiplicity_account.v1 JSON.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidates/risk_taker_sprint_isolation"),
            "--out",
            help="Output directory for profit_core_risk_taker_sprint_isolation.json.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_and_write_risk_taker_sprint_isolation(
                protocol_path=_resolve_workspace_path(protocol, settings.data_dir),
                candidate_set_path=_resolve_workspace_path(candidate_set, settings.data_dir),
                search_ledger_path=_resolve_workspace_path(search_ledger, settings.data_dir),
                multiplicity_account_path=_resolve_workspace_path(
                    multiplicity_account,
                    settings.data_dir,
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            RiskTakerSprintIsolationOutputExistsError,
            RiskTakerSprintIsolationError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        isolation = result.isolation
        typer.echo("network_attempted=false")
        typer.echo("status=pass")
        typer.echo(f"mode={isolation.mode}")
        typer.echo(f"output_label={isolation.output_label}")
        typer.echo(
            "default_aggregate_inclusion_allowed="
            f"{str(isolation.default_aggregate_inclusion_allowed).lower()}"
        )
        typer.echo(
            "actual_cash_direct_promotion_allowed="
            f"{str(isolation.actual_cash_direct_promotion_allowed).lower()}"
        )
        typer.echo(f"promotion_debt_count={len(isolation.promotion_debt)}")
        typer.echo(f"isolation_path={result.isolation_path.as_posix()}")
