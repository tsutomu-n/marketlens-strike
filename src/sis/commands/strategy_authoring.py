from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import typer

from sis.backtest.adapter_spike import build_backtest_adapter_spike
from sis.backtest.adapter_contract import build_backtest_adapter_contract
from sis.backtest.adapter_selection import build_backtest_adapter_selection
from sis.backtest.compare import build_strategy_backtest_comparison
from sis.backtest.external import build_strategy_backtest_external_result
from sis.backtest.framework_smoke import build_backtest_framework_smoke
from sis.backtest.pack import (
    validate_strategy_backtest_pack,
    write_strategy_backtest_pack_outputs,
)
from sis.research.strategy_lab.authoring.backtest import (
    run_authoring_backtest,
    write_authoring_backtest_outputs,
)
from sis.research.strategy_lab.authoring.bundle import (
    run_authoring_bundle,
    write_authoring_bundle_outputs,
)
from sis.research.strategy_lab.authoring.backtest_suite import (
    run_backtest_suite,
    write_backtest_suite_outputs,
)
from sis.research.strategy_lab.authoring.compiler.artifacts import (
    write_authoring_signal_artifacts,
)
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.compiler.paper_preview import (
    write_authoring_paper_preview_outputs,
    write_authoring_run_summary,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    VALID_THROUGH,
    StrategyAuthoringValidationError,
)
from sis.research.strategy_lab.authoring.explain import explain_authoring_spec
from sis.research.strategy_lab.authoring.io import (
    load_backtest_suite_spec,
    load_authoring_bundle_spec,
    load_authoring_spec,
    write_template,
)
from sis.research.strategy_lab.authoring.model_score import (
    train_authoring_linear_model_score,
    write_authoring_model_score_outputs,
)
from sis.research.strategy_lab.authoring.validation import validate_authoring_inputs
from sis.settings import get_settings


def _load_spec_or_exit(path: Path):
    try:
        return load_authoring_spec(path)
    except Exception as exc:
        typer.echo(f"invalid strategy authoring spec: {exc}")
        raise typer.Exit(2) from exc


def _load_bundle_or_exit(path: Path):
    try:
        return load_authoring_bundle_spec(path)
    except Exception as exc:
        typer.echo(f"invalid strategy authoring bundle: {exc}")
        raise typer.Exit(2) from exc


def _load_backtest_suite_or_exit(path: Path):
    try:
        return load_backtest_suite_spec(path)
    except Exception as exc:
        typer.echo(f"invalid strategy backtest suite: {exc}")
        raise typer.Exit(2) from exc


def _resolve_workspace_path(path: Path, data_dir: Path) -> Path:
    return path if path.is_absolute() else data_dir.parent / path


def _resolve_spec_data_path(raw_path: str, data_dir: Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else data_dir.parent / path


def register_strategy_authoring_commands(app: typer.Typer) -> None:
    @app.command("strategy-author-init")
    def strategy_author_init_cmd(
        out: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml"),
            "--out",
            help="Path to write the starter YAML spec.",
        ),
        template: str = typer.Option(
            "trend_pullback",
            "--template",
            help="Template ID. v1 supports trend_pullback.",
        ),
    ) -> None:
        if template != "trend_pullback":
            typer.echo("template must be trend_pullback")
            raise typer.Exit(2)
        path = write_template(out)
        typer.echo(f"strategy_authoring_spec={path}")

    @app.command("strategy-author-validate")
    def strategy_author_validate_cmd(spec: Path = typer.Option(..., "--spec")) -> None:
        settings = get_settings()
        parsed = _load_spec_or_exit(spec)
        errors = validate_authoring_inputs(parsed, data_dir=settings.data_dir)
        if errors:
            for error in errors:
                typer.echo(error)
            raise typer.Exit(2)
        typer.echo("strategy_authoring_spec=valid")

    @app.command("strategy-author-explain")
    def strategy_author_explain_cmd(
        spec: Path = typer.Option(..., "--spec"),
        out: Path | None = typer.Option(None, "--out"),
    ) -> None:
        settings = get_settings()
        parsed = _load_spec_or_exit(spec)
        report = explain_authoring_spec(parsed, data_dir=settings.data_dir)
        report_path = out or (settings.data_dir / "reports/strategy_authoring_explain.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        typer.echo(f"report_path={report_path}")

    @app.command("strategy-author-run")
    def strategy_author_run_cmd(
        spec: Path = typer.Option(..., "--spec"),
        through: str = typer.Option("signals", "--through"),
    ) -> None:
        if through not in VALID_THROUGH:
            typer.echo("through must be one of: signals, backtest, paper-preview")
            raise typer.Exit(2)
        settings = get_settings()
        parsed = _load_spec_or_exit(spec)
        try:
            frame, manifest = build_authoring_signals(parsed, data_dir=settings.data_dir)
            artifacts = write_authoring_signal_artifacts(
                frame, manifest, data_dir=settings.data_dir
            )
            summary = None
            if through in {"backtest", "paper-preview"}:
                metrics, summary = run_authoring_backtest(parsed, frame, data_dir=settings.data_dir)
                artifacts.update(
                    write_authoring_backtest_outputs(
                        parsed, metrics, summary, data_dir=settings.data_dir
                    )
                )
            if through == "paper-preview":
                if summary is None:
                    summary = {}
                artifacts.update(
                    write_authoring_paper_preview_outputs(
                        parsed, frame, summary, data_dir=settings.data_dir
                    )
                )
            run_summary = write_authoring_run_summary(
                parsed,
                data_dir=settings.data_dir,
                through=through,
                artifacts=artifacts,
                signal_count=frame.height,
            )
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"strategy_signals={artifacts['signals_parquet']}")
        if "metrics" in artifacts:
            typer.echo(f"backtest_metrics={artifacts['metrics']}")
        typer.echo(f"run_summary={run_summary}")

    @app.command("strategy-author-bundle-run")
    def strategy_author_bundle_run_cmd(bundle: Path = typer.Option(..., "--bundle")) -> None:
        settings = get_settings()
        parsed = _load_bundle_or_exit(bundle)
        try:
            payload = run_authoring_bundle(parsed, bundle_path=bundle, data_dir=settings.data_dir)
            artifacts = write_authoring_bundle_outputs(payload, data_dir=settings.data_dir)
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"bundle_result={artifacts['bundle_result']}")
        typer.echo(f"bundle_report={artifacts['bundle_report']}")

    @app.command("strategy-backtest-suite")
    def strategy_backtest_suite_cmd(suite: Path = typer.Option(..., "--suite")) -> None:
        settings = get_settings()
        parsed = _load_backtest_suite_or_exit(suite)
        try:
            payload = run_backtest_suite(parsed, suite_path=suite, data_dir=settings.data_dir)
            artifacts = write_backtest_suite_outputs(payload, data_dir=settings.data_dir)
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_suite_result={artifacts['suite_result']}")
        typer.echo(f"backtest_suite_report={artifacts['suite_report']}")

    @app.command("strategy-backtest-compare")
    def strategy_backtest_compare_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        suite_result_path: Path = typer.Option(
            Path("data/research/backtest_suite/strategy_backtest_suite_result.json"),
            "--suite-result-path",
            help="Optional Strategy Backtest Suite result JSON. Used when the file exists.",
        ),
        adapter_spike_path: Path = typer.Option(
            Path("data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"),
            "--adapter-spike-path",
            help="Optional Strategy Backtest Adapter Spike JSON. Used when the file exists.",
        ),
        external_result_path: Path = typer.Option(
            Path("data/research/backtest_external/strategy_backtest_external_result.json"),
            "--external-result-path",
            help="Optional Strategy Backtest External Result JSON. Used when the file exists.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_compare"),
            "--out",
            help="Output directory for comparison artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = (
            metrics_path if metrics_path.is_absolute() else settings.data_dir.parent / metrics_path
        )
        selected_suite_result_path = (
            suite_result_path
            if suite_result_path.is_absolute()
            else settings.data_dir.parent / suite_result_path
        )
        selected_adapter_spike_path = (
            adapter_spike_path
            if adapter_spike_path.is_absolute()
            else settings.data_dir.parent / adapter_spike_path
        )
        selected_external_result_path = (
            external_result_path
            if external_result_path.is_absolute()
            else settings.data_dir.parent / external_result_path
        )
        selected_out = out if out.is_absolute() else settings.data_dir.parent / out
        selected_reports = (
            reports_dir if reports_dir.is_absolute() else settings.data_dir.parent / reports_dir
        )
        try:
            result = build_strategy_backtest_comparison(
                metrics_path=selected_metrics_path,
                suite_result_path=selected_suite_result_path
                if selected_suite_result_path.exists()
                else None,
                adapter_spike_path=selected_adapter_spike_path
                if selected_adapter_spike_path.exists()
                else None,
                external_result_path=selected_external_result_path
                if selected_external_result_path.exists()
                else None,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_comparison={result.comparison_path}")
        typer.echo(f"backtest_comparison_report={result.report_path}")

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
        selected_out = out if out.is_absolute() else settings.data_dir.parent / out
        selected_reports = (
            reports_dir if reports_dir.is_absolute() else settings.data_dir.parent / reports_dir
        )
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
        selected_metrics_path = (
            metrics_path if metrics_path.is_absolute() else settings.data_dir.parent / metrics_path
        )
        selected_signals_path = (
            signals_path if signals_path.is_absolute() else settings.data_dir.parent / signals_path
        )
        selected_quotes_path = (
            quotes_path if quotes_path.is_absolute() else settings.data_dir.parent / quotes_path
        )
        selected_out = out if out.is_absolute() else settings.data_dir.parent / out
        selected_reports = (
            reports_dir if reports_dir.is_absolute() else settings.data_dir.parent / reports_dir
        )
        try:
            result = build_strategy_backtest_external_result(
                metrics_path=selected_metrics_path,
                signals_path=selected_signals_path,
                quotes_path=selected_quotes_path,
                label_horizon_minutes=label_horizon_minutes,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_external_result={result.external_path}")
        typer.echo(f"backtest_external_report={result.report_path}")

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

    @app.command("strategy-backtest-pack")
    def strategy_backtest_pack_cmd(
        spec: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml"),
            "--spec",
            help="Strategy Authoring spec used for the canonical single backtest metrics.",
        ),
        suite: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/backtest_suite.yaml"),
            "--suite",
            help="Strategy Backtest Suite YAML used for multi-method backtests.",
        ),
        label_horizon_minutes: int = typer.Option(
            240,
            "--label-horizon-minutes",
            help="Holding horizon used to build optional external framework exits.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_pack"),
            "--out",
            help="Output directory for the pack manifest.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_spec = _resolve_workspace_path(spec, settings.data_dir)
        selected_suite = _resolve_workspace_path(suite, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        parsed_spec = _load_spec_or_exit(selected_spec)
        parsed_suite = _load_backtest_suite_or_exit(selected_suite)
        try:
            frame, manifest = build_authoring_signals(parsed_spec, data_dir=settings.data_dir)
            signal_artifacts = write_authoring_signal_artifacts(
                frame, manifest, data_dir=settings.data_dir
            )
            metrics, summary = run_authoring_backtest(
                parsed_spec, frame, data_dir=settings.data_dir
            )
            backtest_artifacts = write_authoring_backtest_outputs(
                parsed_spec, metrics, summary, data_dir=settings.data_dir
            )
            suite_payload = run_backtest_suite(
                parsed_suite, suite_path=selected_suite, data_dir=settings.data_dir
            )
            suite_artifacts = write_backtest_suite_outputs(
                suite_payload, data_dir=settings.data_dir
            )
            adapter_result = build_backtest_adapter_spike(
                out_dir=settings.data_dir / "research/backtest_adapter_spike",
                reports_dir=selected_reports,
            )
            external_result = build_strategy_backtest_external_result(
                metrics_path=backtest_artifacts["metrics"],
                signals_path=signal_artifacts["signals_parquet"],
                quotes_path=_resolve_spec_data_path(
                    parsed_spec.data.quote_data_path, settings.data_dir
                ),
                label_horizon_minutes=label_horizon_minutes,
                out_dir=settings.data_dir / "research/backtest_external",
                reports_dir=selected_reports,
            )
            comparison_result = build_strategy_backtest_comparison(
                metrics_path=backtest_artifacts["metrics"],
                suite_result_path=suite_artifacts["suite_result"],
                adapter_spike_path=adapter_result.spike_path,
                external_result_path=external_result.external_path,
                out_dir=settings.data_dir / "research/backtest_compare",
                reports_dir=selected_reports,
            )
            pack_result = write_strategy_backtest_pack_outputs(
                spec_path=selected_spec,
                suite_path=selected_suite,
                artifacts={
                    "signals_parquet": signal_artifacts["signals_parquet"],
                    "signals_jsonl": signal_artifacts["signals_jsonl"],
                    "signal_manifest": signal_artifacts["manifest"],
                    "backtest_metrics": backtest_artifacts["metrics"],
                    "backtest_report": backtest_artifacts["report"],
                    "suite_result": suite_artifacts["suite_result"],
                    "suite_report": suite_artifacts["suite_report"],
                    "adapter_spike": adapter_result.spike_path,
                    "adapter_spike_report": adapter_result.report_path,
                    "external_result": external_result.external_path,
                    "external_report": external_result.report_path,
                    "comparison": comparison_result.comparison_path,
                    "comparison_report": comparison_result.report_path,
                },
                suite_payload=suite_payload,
                external_payload=external_result.payload,
                comparison_payload=comparison_result.payload,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
            validation_result = validate_strategy_backtest_pack(
                pack_path=pack_result.pack_path,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_pack={pack_result.pack_path}")
        typer.echo(f"backtest_pack_report={pack_result.report_path}")
        typer.echo(f"backtest_pack_validation={validation_result.validation_path}")
        typer.echo(f"backtest_pack_validation_report={validation_result.report_path}")
        typer.echo(f"backtest_comparison={comparison_result.comparison_path}")
        typer.echo(f"backtest_suite_result={suite_artifacts['suite_result']}")
        if validation_result.payload["decision"] != "PASS":
            raise typer.Exit(2)

    @app.command("strategy-backtest-pack-validate")
    def strategy_backtest_pack_validate_cmd(
        pack_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack.json"),
            "--pack-path",
            help="Strategy backtest pack manifest JSON.",
        ),
        min_suite_method_count: int = typer.Option(
            5,
            "--min-suite-method-count",
            help="Minimum required suite method count.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_pack"),
            "--out",
            help="Output directory for the validation artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_pack_path = _resolve_workspace_path(pack_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = validate_strategy_backtest_pack(
                pack_path=selected_pack_path,
                out_dir=selected_out,
                reports_dir=selected_reports,
                min_suite_method_count=min_suite_method_count,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_pack_validation={result.validation_path}")
        typer.echo(f"backtest_pack_validation_report={result.report_path}")
        typer.echo(f"decision={result.payload['decision']}")
        if result.payload["decision"] != "PASS":
            raise typer.Exit(2)

    @app.command("strategy-author-train-model")
    def strategy_author_train_model_cmd(
        spec: Path = typer.Option(..., "--spec"),
        target_column: str = typer.Option(..., "--target-column"),
        feature_column: list[str] = typer.Option(..., "--feature-column"),
        ridge_lambda: float = typer.Option(1e-6, "--ridge-lambda"),
        activation: str = typer.Option("identity", "--activation"),
        missing_value: float | None = typer.Option(None, "--missing-value"),
        out_spec: Path | None = typer.Option(None, "--out-spec"),
    ) -> None:
        if activation not in {"identity", "sigmoid", "tanh", "clamp_0_1"}:
            typer.echo("activation must be one of: identity, sigmoid, tanh, clamp_0_1")
            raise typer.Exit(2)
        settings = get_settings()
        parsed = _load_spec_or_exit(spec)
        try:
            payload = train_authoring_linear_model_score(
                parsed,
                data_dir=settings.data_dir,
                target_column=target_column,
                feature_columns=feature_column,
                ridge_lambda=ridge_lambda,
                activation=cast(Literal["identity", "sigmoid", "tanh", "clamp_0_1"], activation),
                missing_value=missing_value,
            )
            artifacts = write_authoring_model_score_outputs(
                parsed,
                payload,
                data_dir=settings.data_dir,
                out_spec=out_spec,
            )
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"model_score={artifacts['model_score']}")
        if "spec" in artifacts:
            typer.echo(f"model_spec={artifacts['spec']}")
