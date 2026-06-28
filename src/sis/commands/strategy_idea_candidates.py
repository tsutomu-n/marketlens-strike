from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_idea_candidates.ai import (
    StrategyIdeaCandidateAIError,
    StrategyIdeaCandidateAIOutputExistsError,
    build_ai_candidate_packet,
    import_ai_candidate_response,
)
from sis.strategy_idea_candidates.authoring_preflight import (
    StrategyIdeaCandidateAuthoringPreflightOutputExistsError,
    build_strategy_idea_candidate_authoring_preflight,
    write_strategy_idea_candidate_authoring_preflight,
)
from sis.strategy_idea_candidates.authoring_bridge import (
    StrategyIdeaCandidateAuthoringBridgeOutputExistsError,
    build_strategy_idea_candidate_authoring_bridge,
)
from sis.strategy_idea_candidates.export import (
    StrategyIdeaCandidateExportError,
    StrategyIdeaCandidateExportResult,
    StrategyIdeaCandidateExportOutputExistsError,
    export_shortlisted_strategy_ideas,
)
from sis.strategy_idea_candidates.generator import (
    StrategyIdeaCandidateGeneratorConfig,
    StrategyIdeaCandidateGeneratorError,
    StrategyIdeaCandidateProfile,
    build_deterministic_candidate_set_from_input_evidence,
    default_family_ids_for_profile,
)
from sis.strategy_idea_candidates.ledger import (
    StrategyIdeaCandidateLedgerOutputExistsError,
    write_strategy_idea_candidate_search_ledger,
)
from sis.strategy_idea_candidates.operator_review import (
    StrategyIdeaCandidateOperatorReviewOutputExistsError,
    write_strategy_idea_candidate_operator_review,
)
from sis.strategy_idea_candidates.perp_bridge import (
    StrategyIdeaCandidatePerpEstimateBridgeOutputExistsError,
    build_and_write_candidate_perp_estimate_bridge,
)
from sis.strategy_idea_candidates.perp_costs import (
    StrategyIdeaCandidatePerpCostEstimateOutputExistsError,
    apply_perp_cost_estimates,
    write_strategy_idea_candidate_perp_cost_estimate_report,
)
from sis.strategy_idea_candidates.policies import (
    StrategyIdeaCandidatePolicyValidationResult,
    validate_perp_shortlist_constraints,
    validate_split_and_leakage_policy,
)
from sis.strategy_idea_candidates.review_packet import (
    StrategyIdeaCandidateReviewPacketOutputExistsError,
    build_strategy_idea_candidate_review_packet,
    write_strategy_idea_candidate_review_packet,
)
from sis.strategy_idea_candidates.selection_metrics import (
    StrategyIdeaCandidateSelectionMetricsOutputExistsError,
    apply_selection_adjusted_metrics,
    write_strategy_idea_candidate_selection_metrics_report,
)
from sis.strategy_idea_candidates.service import (
    StrategyIdeaCandidateSetError,
    StrategyIdeaCandidateSetOutputExistsError,
    write_strategy_idea_candidate_set,
)
from sis.strategy_idea_candidates.splits import (
    StrategyIdeaCandidateSplitMaterializationOutputExistsError,
    materialize_candidate_splits,
    write_strategy_idea_candidate_split_materialization,
)
from sis.strategy_inputs.io import StrategyInputIOError, read_mapping_file
from sis.strategy_inputs.models import (
    ProducerInfo,
    StrategyInputContract,
    StrategyInputContractValidation,
)
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet


def register_strategy_idea_candidate_commands(app: typer.Typer) -> None:
    @app.command("strategy-idea-candidates-build")
    def strategy_idea_candidates_build_cmd(
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
        profile: StrategyIdeaCandidateProfile = typer.Option(
            StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER,
            "--profile",
            help="Candidate generation profile. Supported: crypto-perp-risk-taker.",
        ),
        candidate_cap: int = typer.Option(250, "--candidate-cap", min=1),
        shortlist_count: int = typer.Option(10, "--shortlist-count", min=1),
        out: Path = typer.Option(
            Path("data/strategy_idea_candidates"),
            "--out",
            help="Output directory for candidate set artifacts.",
        ),
        candidate_set_id: str | None = typer.Option(
            None,
            "--candidate-set-id",
            help="Candidate set id. Defaults to contract id plus profile.",
        ),
        export_shortlist: bool = typer.Option(
            True,
            "--export-shortlist/--no-export-shortlist",
            help="Export shortlisted candidates as strategy_idea.v1 drafts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            contract_path = _resolve_workspace_path(contract, settings.data_dir)
            validation_path = _resolve_workspace_path(validation, settings.data_dir)
            out_dir = _resolve_workspace_path(out, settings.data_dir)
            contract_model = StrategyInputContract.model_validate(read_mapping_file(contract_path))
            validation_model = StrategyInputContractValidation.model_validate(
                read_mapping_file(validation_path)
            )
            config = _build_config(
                contract=contract_model,
                validation=validation_model,
                profile=profile,
                candidate_cap=candidate_cap,
                shortlist_count=shortlist_count,
                candidate_set_id=candidate_set_id,
            )
            candidate_set = build_deterministic_candidate_set_from_input_evidence(
                contract=contract_model,
                validation=validation_model,
                validation_path=validation_path,
                config=config,
            ).model_copy(
                update={"producer": ProducerInfo(command="strategy-idea-candidates-build")}
            )
            candidate_set, perp_cost_report = apply_perp_cost_estimates(
                candidate_set,
                generated_at=validation_model.validated_at,
            )
            candidate_set, selection_metrics_report = apply_selection_adjusted_metrics(
                candidate_set,
                generated_at=validation_model.validated_at,
            )
            split_validation = validate_split_and_leakage_policy(candidate_set)
            perp_validation = validate_perp_shortlist_constraints(candidate_set)
            policy_validation = _combine_policy_validations(
                split_validation,
                perp_validation,
            )
            write_result = write_strategy_idea_candidate_set(
                candidate_set=candidate_set,
                out_dir=out_dir,
                replace_existing=replace_existing,
            )
            ledger_result = write_strategy_idea_candidate_search_ledger(
                candidate_set=candidate_set,
                out_dir=out_dir,
                replace_existing=replace_existing,
            )
            selection_metrics_result = write_strategy_idea_candidate_selection_metrics_report(
                report=selection_metrics_report,
                out_dir=out_dir,
                replace_existing=replace_existing,
            )
            perp_cost_result = write_strategy_idea_candidate_perp_cost_estimate_report(
                report=perp_cost_report,
                out_dir=out_dir,
                replace_existing=replace_existing,
            )
            split_materialization = materialize_candidate_splits(
                candidate_set,
                generated_at=validation_model.validated_at,
            )
            split_result = write_strategy_idea_candidate_split_materialization(
                materialization=split_materialization,
                out_dir=out_dir,
                replace_existing=replace_existing,
            )
            review_result = write_strategy_idea_candidate_operator_review(
                candidate_set=candidate_set,
                out_dir=out_dir / "review",
                policy_validation=policy_validation,
                replace_existing=replace_existing,
            )
            export_manifest_path: Path | None = None
            export_result: StrategyIdeaCandidateExportResult | None = None
            if export_shortlist:
                export_result = export_shortlisted_strategy_ideas(
                    candidate_set=candidate_set,
                    candidate_set_path=write_result.candidate_set_path,
                    out_dir=out_dir / "exported_strategy_ideas",
                    replace_existing=replace_existing,
                    created_at=validation_model.validated_at,
                )
                export_manifest_path = export_result.manifest_path
            authoring_preflight = build_strategy_idea_candidate_authoring_preflight(
                candidate_set=candidate_set,
                export_manifest=export_result.manifest if export_result is not None else None,
                generated_at=validation_model.validated_at,
            )
            authoring_preflight_result = write_strategy_idea_candidate_authoring_preflight(
                preflight=authoring_preflight,
                out_dir=out_dir,
                replace_existing=replace_existing,
            )
            review_packet = build_strategy_idea_candidate_review_packet(
                candidate_set=candidate_set,
                selection_metrics=selection_metrics_report,
                perp_cost_estimates=perp_cost_report,
                split_materialization=split_materialization,
                policy_validation=policy_validation,
                generated_at=validation_model.validated_at,
            )
            review_packet_result = write_strategy_idea_candidate_review_packet(
                packet=review_packet,
                out_dir=out_dir / "review",
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            StrategyIdeaCandidateGeneratorError,
            StrategyIdeaCandidateSetError,
            StrategyIdeaCandidateSetOutputExistsError,
            StrategyIdeaCandidateLedgerOutputExistsError,
            StrategyIdeaCandidateOperatorReviewOutputExistsError,
            StrategyIdeaCandidateSelectionMetricsOutputExistsError,
            StrategyIdeaCandidatePerpCostEstimateOutputExistsError,
            StrategyIdeaCandidateSplitMaterializationOutputExistsError,
            StrategyIdeaCandidateReviewPacketOutputExistsError,
            StrategyIdeaCandidateAuthoringPreflightOutputExistsError,
            StrategyIdeaCandidateExportError,
            StrategyIdeaCandidateExportOutputExistsError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        summary = candidate_set.search_ledger_summary
        typer.echo("status=pass")
        typer.echo(f"profile={profile.value}")
        typer.echo(f"candidate_set_id={candidate_set.candidate_set_id}")
        typer.echo(f"candidate_count_total={summary.candidate_count_total}")
        typer.echo(f"candidate_count_shortlisted={summary.candidate_count_shortlisted}")
        typer.echo(f"candidate_count_rejected={summary.candidate_count_rejected}")
        typer.echo(f"candidate_set_path={write_result.candidate_set_path.as_posix()}")
        typer.echo(f"report_path={write_result.report_path.as_posix()}")
        typer.echo(f"operator_review_path={review_result.report_path.as_posix()}")
        typer.echo(f"search_ledger_path={ledger_result.ledger_path.as_posix()}")
        typer.echo(
            f"selection_metrics_path={selection_metrics_result.report_path.as_posix()}"
        )
        typer.echo(f"perp_cost_estimates_path={perp_cost_result.report_path.as_posix()}")
        typer.echo(f"split_materialization_path={split_result.materialization_path.as_posix()}")
        typer.echo(f"review_packet_path={review_packet_result.packet_path.as_posix()}")
        typer.echo(
            f"authoring_preflight_path={authoring_preflight_result.preflight_path.as_posix()}"
        )
        if export_manifest_path is not None:
            typer.echo(f"export_manifest_path={export_manifest_path.as_posix()}")

    @app.command("strategy-idea-candidates-ai-packet-build")
    def strategy_idea_candidates_ai_packet_build_cmd(
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="strategy_idea_candidate_set.v1 JSON.",
        ),
        ledger: Path = typer.Option(
            ...,
            "--ledger",
            dir_okay=False,
            help="Candidate search ledger JSONL.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_idea_candidates/ai_packet"),
            "--out",
            help="Output directory for manual AI packet artifacts.",
        ),
        packet_id: str = typer.Option(
            "strategy-idea-candidates-ai-packet",
            "--packet-id",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_ai_candidate_packet(
                candidate_set_path=_resolve_workspace_path(candidate_set, settings.data_dir),
                ledger_path=_resolve_workspace_path(ledger, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                packet_id=packet_id,
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyIdeaCandidateAIError,
            StrategyIdeaCandidateAIOutputExistsError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        typer.echo("status=pass")
        typer.echo(f"packet_id={result.packet['packet_id']}")
        typer.echo(f"ai_input_hash={result.packet['ai_input_hash']}")
        typer.echo(f"packet_path={result.packet_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("strategy-idea-candidates-ai-import")
    def strategy_idea_candidates_ai_import_cmd(
        packet: Path = typer.Option(
            ...,
            "--packet",
            dir_okay=False,
            help="AI candidate packet JSON.",
        ),
        response: Path = typer.Option(
            ...,
            "--response",
            dir_okay=False,
            help="Manual AI response JSON.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_idea_candidates/ai_import"),
            "--out",
            help="Output directory for imported candidate set artifacts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = import_ai_candidate_response(
                packet_path=_resolve_workspace_path(packet, settings.data_dir),
                response_path=_resolve_workspace_path(response, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyIdeaCandidateAIError,
            StrategyIdeaCandidateAIOutputExistsError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        summary = result.candidate_set.search_ledger_summary
        typer.echo("status=pass")
        typer.echo(f"candidate_set_id={result.candidate_set.candidate_set_id}")
        typer.echo(f"candidate_count_total={summary.candidate_count_total}")
        typer.echo(f"candidate_count_rejected={summary.candidate_count_rejected}")
        typer.echo(f"candidate_set_path={result.candidate_set_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        typer.echo(f"search_ledger_path={result.ledger_path.as_posix()}")

    @app.command("strategy-idea-candidates-perp-estimate")
    def strategy_idea_candidates_perp_estimate_cmd(
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="strategy_idea_candidate_set.v1 JSON.",
        ),
        outcome: list[Path] = typer.Option(
            ...,
            "--outcome",
            help="One or more crypto_perp_outcome.v1 JSON artifacts.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_idea_candidates/perp_estimate_bridge"),
            "--out",
            help="Output directory for candidate-scoped crypto_perp_tournament_rows.v2 estimates.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            candidate_set_path = _resolve_workspace_path(candidate_set, settings.data_dir)
            candidate_set_model = StrategyIdeaCandidateSet.model_validate(
                read_mapping_file(candidate_set_path)
            )
            result = build_and_write_candidate_perp_estimate_bridge(
                candidate_set=candidate_set_model,
                candidate_set_path=candidate_set_path,
                outcome_paths=[
                    _resolve_workspace_path(path, settings.data_dir) for path in outcome
                ],
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
                created_at=datetime.now(timezone.utc).replace(microsecond=0),
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            StrategyIdeaCandidatePerpEstimateBridgeOutputExistsError,
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
        typer.echo(f"candidate_set_id={result.manifest.candidate_set_id}")
        typer.echo(f"row_set_count={len(result.row_set_paths)}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")

    @app.command("strategy-idea-candidates-authoring-bridge")
    def strategy_idea_candidates_authoring_bridge_cmd(
        candidate_set: Path = typer.Option(
            ...,
            "--candidate-set",
            dir_okay=False,
            help="strategy_idea_candidate_set.v1 JSON.",
        ),
        export_manifest: Path = typer.Option(
            ...,
            "--export-manifest",
            dir_okay=False,
            help="strategy_idea_candidate_export_manifest.v1 JSON.",
        ),
        ledger: Path = typer.Option(
            ...,
            "--ledger",
            dir_okay=False,
            help="Candidate search ledger JSONL.",
        ),
        prep_watchdeck_root: Path = typer.Option(
            ...,
            "--prep-watchdeck-root",
            file_okay=False,
            help="Local prep-watchdeck repository root. Read-only.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_idea_candidates/authoring_bridge"),
            "--out",
            help="Output directory for candidate-scoped authoring bridge artifacts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing output artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_idea_candidate_authoring_bridge(
                candidate_set_path=_resolve_workspace_path(candidate_set, settings.data_dir),
                export_manifest_path=_resolve_workspace_path(
                    export_manifest,
                    settings.data_dir,
                ),
                ledger_path=_resolve_workspace_path(ledger, settings.data_dir),
                prep_watchdeck_root=_resolve_workspace_path(
                    prep_watchdeck_root,
                    settings.data_dir,
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                replace_existing=replace_existing,
            )
        except (
            FileNotFoundError,
            StrategyInputIOError,
            StrategyIdeaCandidateAuthoringBridgeOutputExistsError,
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
        typer.echo(f"candidate_set_id={result.manifest.candidate_set_id}")
        typer.echo(f"bridged_count={result.manifest.summary['bridged_count']}")
        typer.echo(f"blocked_count={result.manifest.summary['blocked_count']}")
        typer.echo(f"manifest_path={result.manifest_path.as_posix()}")


def _build_config(
    *,
    contract: StrategyInputContract,
    validation: StrategyInputContractValidation,
    profile: StrategyIdeaCandidateProfile,
    candidate_cap: int,
    shortlist_count: int,
    candidate_set_id: str | None,
) -> StrategyIdeaCandidateGeneratorConfig:
    max_observed = _max_observed_timestamp(validation)
    generated_at = validation.validated_at
    train_start = max_observed - timedelta(days=365)
    train_end = max_observed - timedelta(days=180)
    validation_start = train_end + timedelta(seconds=1)
    validation_end = max_observed
    sealed_start = generated_at
    if sealed_start <= validation_end:
        sealed_start = validation_end + timedelta(seconds=1)
    return StrategyIdeaCandidateGeneratorConfig(
        candidate_set_id=(
            candidate_set_id or f"{contract.contract_id}-{profile.value.replace('-', '_')}"
        ),
        profile=profile,
        family_ids=default_family_ids_for_profile(profile),
        candidate_cap=candidate_cap,
        shortlist_count=shortlist_count,
        target_definition="next_window_cost_adjusted_return_estimate",
        prediction_horizon="quick_validation_window",
        timeframe=contract.strategy_scope.timeframe,
        label_window={"start": validation_end, "end": validation_end},
        feature_observation_window={"start": train_start, "end": validation_end},
        train_window={"start": train_start, "end": train_end},
        validation_window={"start": validation_start, "end": validation_end},
        sealed_test_window={"start": sealed_start, "end": sealed_start},
        generated_at=generated_at,
        available_at_policy=(
            "perp features, funding, fees, slippage, and liquidation buffer must be "
            "known before selection"
        ),
        purge_policy="policy_record_only:not_implemented_for_quick_perp_hypothesis",
        embargo_policy="policy_record_only:not_implemented_for_quick_perp_hypothesis",
    )


def _max_observed_timestamp(validation: StrategyInputContractValidation) -> datetime:
    observed = [
        result.max_observed_timestamp
        for result in validation.source_results
        if result.max_observed_timestamp is not None
    ]
    if not observed:
        return validation.validated_at - timedelta(days=1)
    values = [
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        for value in observed
    ]
    latest = max(values)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return latest.astimezone(timezone.utc)


def _combine_policy_validations(
    *results: StrategyIdeaCandidatePolicyValidationResult,
) -> StrategyIdeaCandidatePolicyValidationResult:
    failures: list[str] = []
    for result in results:
        failures.extend(result.failures)
    return StrategyIdeaCandidatePolicyValidationResult(
        candidate_set_id=results[0].candidate_set_id if results else "",
        passed=not failures,
        failures=failures,
    )
