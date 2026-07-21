from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.edge_candidate_factory.adversarial_review import (
    build_adversarial_packet,
    import_adversarial_review,
)
from sis.edge_candidate_factory.generator import (
    EdgeCandidateFactoryConfig,
    EdgeCandidateFactoryError,
    EdgeCandidateFactoryOutputExistsError,
    build_edge_candidate_factory_run,
    write_edge_candidate_factory_run,
)
from sis.edge_candidate_factory.backtest_inputs import extract_backtest_metrics
from sis.edge_candidate_factory.backtest_kill_gate import build_backtest_kill_gate
from sis.edge_candidate_factory.models import ArtifactRef, TrialMultiplicityAccount
from sis.edge_candidate_factory.risk_actual_cash_handoff import (
    build_risk_actual_cash_handoff,
)
from sis.edge_candidate_factory.summary import build_edge_candidate_artifact_summary
from sis.edge_candidate_factory.virtual_execution_gate import build_virtual_execution_gate
from sis.settings import get_settings
from sis.backtest.artifact_io import sha256_file
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_review.provenance import repo_relative_path


def _echo_safe_stdout_prefix() -> None:
    typer.echo("network_attempted=false")
    typer.echo("credentials_used=false")
    typer.echo("exchange_write_used=false")
    typer.echo("production_exchange_write_used=false")
    typer.echo("live_order_submitted=false")
    typer.echo("permits_live_order=false")


def _artifact_ref_from_file(*, ref_id: str, schema_version: str, path: Path) -> ArtifactRef:
    return ArtifactRef(
        ref_id=ref_id,
        schema_version=schema_version,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
    )


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

    @app.command("edge-candidate-backtest-kill-gate")
    def edge_candidate_backtest_kill_gate_cmd(
        candidate_id: str = typer.Option(..., "--candidate-id"),
        family_id: str = typer.Option(..., "--family-id"),
        multiplicity_account: Path = typer.Option(
            ...,
            "--multiplicity-account",
            dir_okay=False,
            help="trial_multiplicity_account.v1 JSON.",
        ),
        metrics: list[Path] | None = typer.Option(
            None,
            "--metrics",
            dir_okay=False,
            help="Backtest metric JSON artifact. Repeat to pass multiple artifacts.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory/backtest_kill_gate"),
            "--out",
            help="Output directory for backtest kill gate artifacts.",
        ),
        source_available: bool = typer.Option(
            True,
            "--source-available/--source-missing",
        ),
        bridge_technical_ready: bool = typer.Option(
            True,
            "--bridge-technical-ready/--bridge-technical-blocked",
        ),
        execution_precheck_passed: bool = typer.Option(
            True,
            "--execution-precheck-passed/--execution-precheck-blocked",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing gate artifact.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        resolved_multiplicity = _resolve_workspace_path(multiplicity_account, settings.data_dir)
        resolved_metrics = [
            _resolve_workspace_path(path, settings.data_dir) for path in (metrics or [])
        ]
        try:
            multiplicity = TrialMultiplicityAccount.model_validate(
                read_mapping_file(resolved_multiplicity)
            )
            metric_payloads = [read_mapping_file(path) for path in resolved_metrics]
            metric_refs = [
                ArtifactRef(
                    ref_id=f"metric-{index:03d}",
                    schema_version=str(payload.get("schema_version", "unknown.v1")),
                    path=repo_relative_path(path),
                    sha256=sha256_file(path),
                )
                for index, (path, payload) in enumerate(
                    zip(resolved_metrics, metric_payloads, strict=True),
                    start=1,
                )
            ]
            multiplicity_ref = ArtifactRef(
                ref_id="multiplicity-account",
                schema_version=multiplicity.schema_version,
                path=repo_relative_path(resolved_multiplicity),
                sha256=sha256_file(resolved_multiplicity),
            )
            gate = build_backtest_kill_gate(
                gate_id=f"{candidate_id}-backtest-kill-gate",
                created_at=datetime.now(timezone.utc).replace(microsecond=0),
                candidate_id=candidate_id,
                family_id=family_id,
                candidate_source_refs=multiplicity.source_refs,
                multiplicity_account=multiplicity,
                multiplicity_account_ref=multiplicity_ref,
                metrics=extract_backtest_metrics(metric_payloads),
                source_available=source_available,
                bridge_technical_ready=bridge_technical_ready,
                execution_precheck_passed=execution_precheck_passed,
                backtest_refs=metric_refs,
            )
            gate_path = resolved_out / f"{candidate_id}.json"
            if gate_path.exists() and not replace_existing:
                raise EdgeCandidateFactoryOutputExistsError(f"output already exists: {gate_path}")
            write_json_artifact(gate_path, gate.model_dump(mode="json"))
        except (
            EdgeCandidateFactoryError,
            EdgeCandidateFactoryOutputExistsError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            _echo_safe_stdout_prefix()
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        _echo_safe_stdout_prefix()
        typer.echo(f"status={gate.gate_status.value.lower()}")
        typer.echo(f"gate_status={gate.gate_status.value}")
        typer.echo(f"artifact_path={gate_path.as_posix()}")
        typer.echo(f"known_gap_count={len(gate.known_gaps)}")

    @app.command("edge-candidate-virtual-execution-gate")
    def edge_candidate_virtual_execution_gate_cmd(
        candidate_id: str = typer.Option(..., "--candidate-id"),
        venue_id: str = typer.Option("bitget", "--venue-id"),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory/virtual_execution_gate"),
            "--out",
            help="Output directory for virtual execution gate artifacts.",
        ),
        source_available: bool = typer.Option(
            True,
            "--source-available/--source-missing",
        ),
        execution_precheck_passed: bool = typer.Option(
            True,
            "--execution-precheck-passed/--execution-precheck-blocked",
        ),
        order_lifecycle_failure: bool = typer.Option(
            False,
            "--order-lifecycle-failure",
            help="Fixture mode: simulate an order lifecycle failure.",
        ),
        reconciliation_mismatch: bool = typer.Option(
            False,
            "--reconciliation-mismatch",
            help="Fixture mode: simulate a flat reconciliation mismatch.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing gate artifact.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        try:
            gate = build_virtual_execution_gate(
                gate_id=f"{candidate_id}-virtual-execution-gate",
                created_at=datetime.now(timezone.utc).replace(microsecond=0),
                candidate_id=candidate_id,
                venue_id=venue_id,
                source_available=source_available,
                execution_precheck_passed=execution_precheck_passed,
                partial_fill_handled=not order_lifecycle_failure,
                flat_reconciliation_passed=not reconciliation_mismatch,
            )
            gate_path = resolved_out / f"{candidate_id}.json"
            if gate_path.exists() and not replace_existing:
                raise EdgeCandidateFactoryOutputExistsError(f"output already exists: {gate_path}")
            write_json_artifact(gate_path, gate.model_dump(mode="json"))
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
        typer.echo(f"status={gate.gate_status.value.lower()}")
        typer.echo(f"gate_status={gate.gate_status.value}")
        typer.echo("actual_cash=false")
        typer.echo("cash_metric_basis=virtual_exchange")
        typer.echo(f"artifact_path={gate_path.as_posix()}")
        typer.echo(f"known_gap_count={len(gate.known_gaps)}")

    @app.command("edge-candidate-risk-actual-cash-handoff")
    def edge_candidate_risk_actual_cash_handoff_cmd(
        candidate_id: str = typer.Option(..., "--candidate-id"),
        candidate_report: Path = typer.Option(..., "--candidate-report", dir_okay=False),
        search_ledger: Path = typer.Option(..., "--search-ledger", dir_okay=False),
        multiplicity_account: Path = typer.Option(
            ...,
            "--multiplicity-account",
            dir_okay=False,
        ),
        backtest_kill_gate: Path = typer.Option(..., "--backtest-kill-gate", dir_okay=False),
        virtual_execution_gate: Path = typer.Option(
            ...,
            "--virtual-execution-gate",
            dir_okay=False,
        ),
        actual_cash_rows: Path | None = typer.Option(
            None,
            "--actual-cash-rows",
            dir_okay=False,
            help="Actual cash rows JSONL. If omitted, handoff remains blocked.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory/risk_actual_cash_handoff"),
            "--out",
            help="Output directory for risk/actual-cash handoff artifacts.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing handoff artifact.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        resolved_candidate_report = _resolve_workspace_path(candidate_report, settings.data_dir)
        resolved_search_ledger = _resolve_workspace_path(search_ledger, settings.data_dir)
        resolved_multiplicity = _resolve_workspace_path(multiplicity_account, settings.data_dir)
        resolved_backtest = _resolve_workspace_path(backtest_kill_gate, settings.data_dir)
        resolved_virtual = _resolve_workspace_path(virtual_execution_gate, settings.data_dir)
        resolved_actual_cash_rows = (
            _resolve_workspace_path(actual_cash_rows, settings.data_dir)
            if actual_cash_rows is not None
            else None
        )
        try:
            handoff = build_risk_actual_cash_handoff(
                handoff_id=f"{candidate_id}-risk-actual-cash-handoff",
                created_at=datetime.now(timezone.utc).replace(microsecond=0),
                candidate_id=candidate_id,
                candidate_report_ref=_artifact_ref_from_file(
                    ref_id="smart-prior-report",
                    schema_version="smart_candidate_prior_report.v1",
                    path=resolved_candidate_report,
                ),
                search_ledger_ref=_artifact_ref_from_file(
                    ref_id="search-ledger",
                    schema_version="edge_candidate_search_ledger.v1",
                    path=resolved_search_ledger,
                ),
                multiplicity_account_ref=_artifact_ref_from_file(
                    ref_id="multiplicity-account",
                    schema_version="trial_multiplicity_account.v1",
                    path=resolved_multiplicity,
                ),
                backtest_kill_gate_ref=_artifact_ref_from_file(
                    ref_id="backtest-kill-gate",
                    schema_version="backtest_kill_gate.v1",
                    path=resolved_backtest,
                ),
                virtual_execution_gate_ref=_artifact_ref_from_file(
                    ref_id="virtual-execution-gate",
                    schema_version="virtual_execution_gate.v1",
                    path=resolved_virtual,
                ),
                actual_cash_rows_ref=_artifact_ref_from_file(
                    ref_id="actual-cash-rows",
                    schema_version="crypto_perp_tournament_rows.v2",
                    path=resolved_actual_cash_rows,
                )
                if resolved_actual_cash_rows is not None
                else None,
            )
            handoff_path = resolved_out / f"{candidate_id}.json"
            if handoff_path.exists() and not replace_existing:
                raise EdgeCandidateFactoryOutputExistsError(
                    f"output already exists: {handoff_path}"
                )
            write_json_artifact(handoff_path, handoff.model_dump(mode="json"))
        except (
            EdgeCandidateFactoryError,
            EdgeCandidateFactoryOutputExistsError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            _echo_safe_stdout_prefix()
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        _echo_safe_stdout_prefix()
        status = handoff.actual_cash_report_gate_input_status.value.lower()
        typer.echo(f"status={status}")
        typer.echo(f"risk_taker_review_input_status={handoff.risk_taker_review_input_status.value}")
        typer.echo(
            "actual_cash_report_gate_input_status="
            f"{handoff.actual_cash_report_gate_input_status.value}"
        )
        typer.echo("actual_cash_rows_required=true")
        typer.echo("virtual_or_backtest_used_as_actual_cash=false")
        typer.echo(f"artifact_path={handoff_path.as_posix()}")
        typer.echo(f"known_gap_count={len(handoff.known_gaps)}")

    @app.command("edge-candidate-adversarial-packet-build")
    def edge_candidate_adversarial_packet_build_cmd(
        source: list[Path] | None = typer.Option(
            None,
            "--source",
            help="Source artifact path. Repeat to include multiple sources.",
        ),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory/adversarial_review"),
            "--out",
            help="Output directory for adversarial packet artifacts.",
        ),
        packet_id: str = typer.Option("edge-candidate-adversarial-packet", "--packet-id"),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing packet artifact.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        resolved_sources = [
            _resolve_workspace_path(path, settings.data_dir) for path in (source or [])
        ]
        try:
            if not resolved_sources:
                raise ValueError("at least one --source is required")
            packet_path = resolved_out / "adversarial_packet.json"
            if packet_path.exists() and not replace_existing:
                raise EdgeCandidateFactoryOutputExistsError(f"output already exists: {packet_path}")
            result = build_adversarial_packet(
                packet_id=packet_id,
                created_at=datetime.now(timezone.utc).replace(microsecond=0),
                source_paths=resolved_sources,
                out_dir=resolved_out,
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
        typer.echo("status=packet_built")
        typer.echo("llm_api_called=false")
        typer.echo(f"source_count={len(result.packet['sources'])}")
        typer.echo(
            "missing_source_count="
            f"{sum(1 for item in result.packet['sources'] if item.get('exists') is False)}"
        )
        typer.echo(f"artifact_path={result.packet_path.as_posix()}")
        typer.echo("known_gap_count=0")

    @app.command("edge-candidate-adversarial-import")
    def edge_candidate_adversarial_import_cmd(
        packet: Path = typer.Option(..., "--packet", dir_okay=False),
        response: Path = typer.Option(..., "--response", dir_okay=False),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory/adversarial_review"),
            "--out",
            help="Output directory for adversarial review artifacts.",
        ),
        review_id: str = typer.Option("edge-candidate-adversarial-review", "--review-id"),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing review artifact.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        resolved_packet = _resolve_workspace_path(packet, settings.data_dir)
        resolved_response = _resolve_workspace_path(response, settings.data_dir)
        try:
            review_path = resolved_out / "llm_adversarial_review.json"
            if review_path.exists() and not replace_existing:
                raise EdgeCandidateFactoryOutputExistsError(f"output already exists: {review_path}")
            result = import_adversarial_review(
                review_id=review_id,
                created_at=datetime.now(timezone.utc).replace(microsecond=0),
                packet_path=resolved_packet,
                response_path=resolved_response,
                out_dir=resolved_out,
            )
        except (
            EdgeCandidateFactoryError,
            EdgeCandidateFactoryOutputExistsError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            _echo_safe_stdout_prefix()
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        _echo_safe_stdout_prefix()
        typer.echo(f"status={result.review.review_status.value.lower()}")
        typer.echo("llm_approval_ignored=true")
        typer.echo("paper_execution_allowed=false")
        typer.echo("live_allowed=false")
        typer.echo("actual_cash_decision_allowed=false")
        typer.echo("gate_override_allowed=false")
        typer.echo(f"artifact_path={result.review_path.as_posix()}")
        typer.echo(f"known_gap_count={result.review.hard_blocker_count}")

    @app.command("edge-candidate-artifact-summary")
    def edge_candidate_artifact_summary_cmd(
        candidate_report: Path | None = typer.Option(
            None,
            "--candidate-report",
            dir_okay=False,
        ),
        backtest_kill_gate: list[Path] | None = typer.Option(
            None,
            "--backtest-kill-gate",
            dir_okay=False,
        ),
        virtual_execution_gate: list[Path] | None = typer.Option(
            None,
            "--virtual-execution-gate",
            dir_okay=False,
        ),
        risk_actual_cash_handoff: list[Path] | None = typer.Option(
            None,
            "--risk-actual-cash-handoff",
            dir_okay=False,
        ),
        adversarial_review: list[Path] | None = typer.Option(
            None,
            "--adversarial-review",
            dir_okay=False,
        ),
        out: Path = typer.Option(
            Path("data/edge_candidate_factory/artifact_summary"),
            "--out",
            help="Output directory for artifact summary.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing summary artifact.",
        ),
    ) -> None:
        settings = get_settings()
        resolved_out = _resolve_workspace_path(out, settings.data_dir)
        summary_path = resolved_out / "artifact_summary.json"
        try:
            if summary_path.exists() and not replace_existing:
                raise EdgeCandidateFactoryOutputExistsError(
                    f"output already exists: {summary_path}"
                )
            summary = build_edge_candidate_artifact_summary(
                candidate_report_path=_resolve_workspace_path(candidate_report, settings.data_dir)
                if candidate_report is not None
                else None,
                backtest_kill_gate_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (backtest_kill_gate or [])
                ],
                virtual_execution_gate_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (virtual_execution_gate or [])
                ],
                risk_actual_cash_handoff_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (risk_actual_cash_handoff or [])
                ],
                adversarial_review_paths=[
                    _resolve_workspace_path(path, settings.data_dir)
                    for path in (adversarial_review or [])
                ],
            )
            write_json_artifact(summary_path, summary)
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
        typer.echo(f"status={summary['core_status'].lower()}")
        typer.echo(f"core_status={summary['core_status']}")
        typer.echo(f"next_action={summary['next_action']}")
        typer.echo(f"candidate_count_total={summary['candidate_count_total']}")
        typer.echo(f"candidate_count_rejected={summary['candidate_count_rejected']}")
        typer.echo(f"shortlist_for_virtual_count={summary['shortlist_for_virtual_count']}")
        typer.echo(f"virtual_passed_count={summary['virtual_passed_count']}")
        typer.echo(f"actual_cash_ready_count={summary['actual_cash_ready_count']}")
        typer.echo(f"known_gap_count={summary['known_gap_count']}")
        typer.echo("production_exchange_write_used=false")
        typer.echo("live_order_allowed=false")
        typer.echo(f"artifact_path={summary_path.as_posix()}")
