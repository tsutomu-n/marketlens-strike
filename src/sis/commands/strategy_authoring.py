from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import typer

from sis.research.strategy_lab.authoring.backtest import (
    run_authoring_backtest,
    write_authoring_backtest_outputs,
)
from sis.research.strategy_lab.authoring.bundle import (
    run_authoring_bundle,
    write_authoring_bundle_outputs,
)
from sis.research.strategy_lab.authoring.compiler import (
    build_authoring_signals,
    write_authoring_paper_preview_outputs,
    write_authoring_run_summary,
    write_authoring_signal_artifacts,
)
from sis.research.strategy_lab.authoring.contracts import (
    VALID_THROUGH,
    StrategyAuthoringValidationError,
)
from sis.research.strategy_lab.authoring.explain import explain_authoring_spec
from sis.research.strategy_lab.authoring.io import (
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
