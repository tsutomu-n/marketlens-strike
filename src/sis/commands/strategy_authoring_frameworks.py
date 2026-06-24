from __future__ import annotations

from pathlib import Path

import typer

from sis.backtest.adapter_contract import build_backtest_adapter_contract
from sis.backtest.adapter_selection import build_backtest_adapter_selection
from sis.backtest.adapter_spike import build_backtest_adapter_spike
from sis.backtest.constraint_breaker import build_strategy_backtest_constraint_breaker_decision
from sis.backtest.external import build_strategy_backtest_external_result
from sis.backtest.framework_run import build_strategy_backtest_framework_run
from sis.backtest.framework_smoke import build_backtest_framework_smoke
from sis.backtest.microstructure_readiness import (
    build_strategy_backtest_microstructure_readiness,
)
from sis.backtest.portfolio_validation_contract import (
    build_strategy_backtest_portfolio_validation_contract,
)
from sis.backtest.pybroker_contract import build_strategy_backtest_pybroker_contract
from sis.backtest.qstrader_contract import build_strategy_backtest_qstrader_contract
from sis.settings import get_settings


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_framework_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-adapter-spike")
    def strategy_backtest_adapter_spike_cmd(
        out: Path = typer.Option(
            Path("data/research/backtest_adapter_spike"),
            "--out",
            help="Output directory for adapter spike artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        result = build_backtest_adapter_spike(out_dir=selected_out, reports_dir=selected_reports)
        typer.echo(f"backtest_adapter_spike={result.spike_path}")
        typer.echo(f"backtest_adapter_spike_report={result.report_path}")

    @app.command("strategy-backtest-external-run")
    def strategy_backtest_external_run_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy signals parquet used by optional external framework runners.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Quotes parquet used by optional external framework runners.",
        ),
        label_horizon_minutes: int = typer.Option(
            240,
            "--label-horizon-minutes",
            help="Holding horizon used to build external framework exits.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_external"),
            "--out",
            help="Output directory for external framework result artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_external_result(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                label_horizon_minutes=label_horizon_minutes,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_external_result={result.external_path}")
        typer.echo(f"backtest_external_report={result.report_path}")

    @app.command("strategy-backtest-framework-run")
    def strategy_backtest_framework_run_cmd(
        framework: list[str] = typer.Option(
            ...,
            "--framework",
            help=(
                "Framework ID to run. Repeat this option. Supported: vectorbt, bt, "
                "empyrical_reloaded, quantstats."
            ),
        ),
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        bundle_path: Path = typer.Option(
            Path("data/research/strategy_authoring_bundle_result.json"),
            "--bundle-path",
            help="Strategy Authoring bundle result JSON for bt portfolio comparison.",
        ),
        price_frame_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--price-frame-path",
            help="Quotes or price frame parquet used by optional framework runners.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy signals parquet used by optional external framework runners.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Quotes parquet used by optional external framework runners.",
        ),
        label_horizon_minutes: int = typer.Option(
            240,
            "--label-horizon-minutes",
            help="Holding horizon used to build optional external framework exits.",
        ),
        frequency: str = typer.Option(
            "daily",
            "--frequency",
            help="Return frequency label for metrics/report frameworks.",
        ),
        risk_free_rate: float = typer.Option(
            0.0,
            "--risk-free-rate",
            help="Risk-free rate passed to optional metrics/report frameworks.",
        ),
        show_framework_warnings: bool = typer.Option(
            False,
            "--show-framework-warnings",
            help="Show warnings emitted by optional report framework generation.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_framework_run"),
            "--out",
            help="Output directory for selected framework run manifest.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        if frequency not in {"daily", "weekly", "monthly", "signal"}:
            typer.echo("frequency must be one of: daily, weekly, monthly, signal")
            raise typer.Exit(2)
        settings = get_settings()
        try:
            result = build_strategy_backtest_framework_run(
                frameworks=framework,
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                bundle_path=_resolve_workspace_path(bundle_path, settings.data_dir),
                price_frame_path=_resolve_workspace_path(price_frame_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                label_horizon_minutes=label_horizon_minutes,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                suppress_framework_warnings=not show_framework_warnings,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_framework_run={result.run_path}")
        typer.echo(f"backtest_framework_run_report={result.report_path}")
        typer.echo(f"framework_count={result.payload['summary']['framework_count']}")
        typer.echo(f"executed_count={result.payload['summary']['executed_count']}")

    @app.command("strategy-backtest-microstructure-readiness")
    def strategy_backtest_microstructure_readiness_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Quotes parquet used by the backtest.",
        ),
        data_availability_path: Path | None = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Optional data availability ledger JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_microstructure_readiness"),
            "--out",
            help="Output directory for microstructure readiness artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_microstructure_readiness(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                data_availability_path=_resolve_workspace_path(
                    data_availability_path, settings.data_dir
                )
                if data_availability_path is not None
                else None,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_microstructure_readiness={result.readiness_path}")
        typer.echo(f"backtest_microstructure_readiness_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")

    @app.command("strategy-backtest-qstrader-contract")
    def strategy_backtest_qstrader_contract_cmd(
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Quotes parquet used by the backtest.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_qstrader_contract"),
            "--out",
            help="Output directory for qstrader contract artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        result = build_strategy_backtest_qstrader_contract(
            signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
            quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
            out_dir=_resolve_workspace_path(out, settings.data_dir),
            reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
        )
        typer.echo(f"backtest_qstrader_contract={result.contract_path}")
        typer.echo(f"backtest_qstrader_contract_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")

    @app.command("strategy-backtest-portfolio-validation-contract")
    def strategy_backtest_portfolio_validation_contract_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_portfolio_validation_contract"),
            "--out",
            help="Output directory for portfolio validation contract artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_portfolio_validation_contract(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_portfolio_validation_contract={result.contract_path}")
        typer.echo(f"backtest_portfolio_validation_contract_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")

    @app.command("strategy-backtest-pybroker-contract")
    def strategy_backtest_pybroker_contract_cmd(
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Quotes parquet used by the backtest.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_pybroker_contract"),
            "--out",
            help="Output directory for PyBroker contract artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        result = build_strategy_backtest_pybroker_contract(
            signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
            quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
            out_dir=_resolve_workspace_path(out, settings.data_dir),
            reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
        )
        typer.echo(f"backtest_pybroker_contract={result.contract_path}")
        typer.echo(f"backtest_pybroker_contract_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")

    @app.command("strategy-backtest-constraint-breaker-decision")
    def strategy_backtest_constraint_breaker_decision_cmd(
        candidate_id: str = typer.Option(..., "--candidate-id"),
        constraint_to_break: str = typer.Option(..., "--constraint-to-break"),
        capability_gap: str = typer.Option(..., "--capability-gap"),
        expected_failure_mode_reduction: str = typer.Option(
            ..., "--expected-failure-mode-reduction"
        ),
        proof_fixture_status: str = typer.Option(..., "--proof-fixture-status"),
        license_terms_status: str = typer.Option(..., "--license-terms-status"),
        external_data_status: str = typer.Option(..., "--external-data-status"),
        ci_cost_status: str = typer.Option(..., "--ci-cost-status"),
        rollback_complexity: str = typer.Option(..., "--rollback-complexity"),
        owner_approval_ref: str | None = typer.Option(None, "--owner-approval-ref"),
        evidence_path: Path | None = typer.Option(None, "--evidence-path"),
        out: Path = typer.Option(
            Path("data/research/backtest_constraint_breaker"),
            "--out",
            help="Output directory for constraint breaker decision artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        result = build_strategy_backtest_constraint_breaker_decision(
            candidate_id=candidate_id,
            constraint_to_break=constraint_to_break,
            capability_gap=capability_gap,
            expected_failure_mode_reduction=expected_failure_mode_reduction,
            proof_fixture_status=proof_fixture_status,
            license_terms_status=license_terms_status,
            external_data_status=external_data_status,
            ci_cost_status=ci_cost_status,
            rollback_complexity=rollback_complexity,
            owner_approval_ref=owner_approval_ref,
            evidence_path=_resolve_workspace_path(evidence_path, settings.data_dir)
            if evidence_path is not None
            else None,
            out_dir=_resolve_workspace_path(out, settings.data_dir),
            reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
        )
        typer.echo(f"backtest_constraint_breaker_decision={result.decision_path}")
        typer.echo(f"backtest_constraint_breaker_decision_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")

    @app.command("strategy-backtest-framework-smoke")
    def strategy_backtest_framework_smoke_cmd(
        framework: list[str] | None = typer.Option(
            None,
            "--framework",
            help="Framework ID to smoke. Repeat this option; defaults to Phase B targets.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_framework_smoke"),
            "--out",
            help="Output directory for framework smoke artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_backtest_framework_smoke(
                out_dir=selected_out,
                reports_dir=selected_reports,
                target_frameworks=framework,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_framework_smoke={result.smoke_path}")
        typer.echo(f"backtest_framework_smoke_report={result.report_path}")

    @app.command("strategy-backtest-adapter-selection")
    def strategy_backtest_adapter_selection_cmd(
        adapter_spike_path: Path = typer.Option(
            Path("data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"),
            "--adapter-spike-path",
            help="Strategy Backtest Adapter Spike JSON.",
        ),
        framework_smoke_path: Path = typer.Option(
            Path("data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json"),
            "--framework-smoke-path",
            help="Strategy Backtest Framework Smoke JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_adapter_selection"),
            "--out",
            help="Output directory for adapter selection artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_adapter_spike_path = _resolve_workspace_path(adapter_spike_path, settings.data_dir)
        selected_framework_smoke_path = _resolve_workspace_path(
            framework_smoke_path, settings.data_dir
        )
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_backtest_adapter_selection(
                adapter_spike_path=selected_adapter_spike_path,
                framework_smoke_path=selected_framework_smoke_path,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_adapter_selection={result.selection_path}")
        typer.echo(f"backtest_adapter_selection_report={result.report_path}")

    @app.command("strategy-backtest-adapter-contract")
    def strategy_backtest_adapter_contract_cmd(
        adapter_selection_path: Path = typer.Option(
            Path(
                "data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json"
            ),
            "--adapter-selection-path",
            help="Strategy Backtest Adapter Selection JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_adapter_contract"),
            "--out",
            help="Output directory for adapter contract artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_adapter_selection_path = _resolve_workspace_path(
            adapter_selection_path, settings.data_dir
        )
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_backtest_adapter_contract(
                adapter_selection_path=selected_adapter_selection_path,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_adapter_contract={result.contract_path}")
        typer.echo(f"backtest_adapter_contract_report={result.report_path}")
