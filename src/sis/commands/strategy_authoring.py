from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

import typer

from sis.backtest.adapter_spike import build_backtest_adapter_spike
from sis.backtest.adapter_contract import build_backtest_adapter_contract
from sis.backtest.adapter_selection import build_backtest_adapter_selection
from sis.backtest.artifact_summary import build_strategy_backtest_artifact_summary
from sis.backtest.assumptions import build_strategy_backtest_assumption_ledger
from sis.backtest.baselines import build_strategy_backtest_baseline_comparison
from sis.backtest.benchmark_relative import (
    DEFAULT_BENCHMARK_RETURN_COLUMN,
    DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
    DEFAULT_HORIZON_MINUTES,
    DEFAULT_PRICE_COLUMN,
    build_strategy_backtest_benchmark_relative,
)
from sis.backtest.compare import build_strategy_backtest_comparison
from sis.backtest.data_availability import build_backtest_data_availability_ledger
from sis.backtest.execution_simulation import build_strategy_backtest_execution_simulation
from sis.backtest.external import build_strategy_backtest_external_result
from sis.backtest.framework_run import build_strategy_backtest_framework_run
from sis.backtest.framework_smoke import build_backtest_framework_smoke
from sis.backtest.metric_extension import build_strategy_backtest_metric_extension
from sis.backtest.no_lookahead import build_strategy_backtest_no_lookahead_diff
from sis.backtest.pack import validate_strategy_backtest_pack
from sis.backtest.pack_runner import (
    StrategyBacktestPackRunInputs,
    run_strategy_backtest_pack,
)
from sis.backtest.portfolio_comparison import build_strategy_backtest_portfolio_comparison
from sis.backtest.regime_split import (
    DEFAULT_DIMENSION_CSV,
    build_strategy_backtest_regime_split,
)
from sis.backtest.report_extension import build_strategy_backtest_report_extension
from sis.backtest.rolling_stability import (
    DEFAULT_WINDOW_CSV,
    build_strategy_backtest_rolling_stability,
)
from sis.backtest.stress import DEFAULT_SCENARIO_CSV, build_strategy_backtest_stress
from sis.backtest.trial_ledger import build_strategy_backtest_trial_ledger
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
from sis.research.strategy_lab.authoring.evaluation_window import (
    apply_evaluation_window,
    manifest_for_evaluation_frame,
)
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
            artifact_frame = frame
            artifact_manifest = manifest
            if through in {"backtest", "paper-preview"}:
                artifact_frame = apply_evaluation_window(parsed, frame)
                artifact_manifest = manifest_for_evaluation_frame(
                    parsed, frame, artifact_frame, manifest
                )
            artifacts = write_authoring_signal_artifacts(
                artifact_frame, artifact_manifest, data_dir=settings.data_dir
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
                        parsed, artifact_frame, summary, data_dir=settings.data_dir
                    )
                )
            run_summary = write_authoring_run_summary(
                parsed,
                data_dir=settings.data_dir,
                through=through,
                artifacts=artifacts,
                signal_count=artifact_frame.height,
                source_signal_count=frame.height,
                evaluation_signal_count=artifact_frame.height,
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
        portfolio_comparison_path: Path = typer.Option(
            Path("data/research/backtest_portfolio/strategy_backtest_portfolio_comparison.json"),
            "--portfolio-comparison-path",
            help="Optional Strategy Backtest Portfolio Comparison JSON. Used when the file exists.",
        ),
        metric_extension_path: Path = typer.Option(
            Path("data/research/backtest_metric_extension/strategy_backtest_metric_extension.json"),
            "--metric-extension-path",
            help="Optional Strategy Backtest Metric Extension JSON. Used when the file exists.",
        ),
        report_extension_path: Path = typer.Option(
            Path("data/research/backtest_report_extension/strategy_backtest_report_extension.json"),
            "--report-extension-path",
            help="Optional Strategy Backtest Report Extension JSON. Used when the file exists.",
        ),
        stress_path: Path = typer.Option(
            Path("data/research/backtest_stress/strategy_backtest_stress.json"),
            "--stress-path",
            help="Optional Strategy Backtest Stress JSON. Used when the file exists.",
        ),
        regime_split_path: Path = typer.Option(
            Path("data/research/backtest_regime_split/strategy_backtest_regime_split.json"),
            "--regime-split-path",
            help="Optional Strategy Backtest Regime Split JSON. Used when the file exists.",
        ),
        rolling_stability_path: Path = typer.Option(
            Path(
                "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
            ),
            "--rolling-stability-path",
            help="Optional Strategy Backtest Rolling Stability JSON. Used when the file exists.",
        ),
        benchmark_relative_path: Path = typer.Option(
            Path(
                "data/research/backtest_benchmark_relative/"
                "strategy_backtest_benchmark_relative.json"
            ),
            "--benchmark-relative-path",
            help="Optional Strategy Backtest Benchmark Relative JSON. Used when the file exists.",
        ),
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Optional Backtest Data Availability Ledger JSON. Used when the file exists.",
        ),
        baseline_comparison_path: Path = typer.Option(
            Path(
                "data/research/backtest_baseline_comparison/"
                "strategy_backtest_baseline_comparison.json"
            ),
            "--baseline-comparison-path",
            help="Optional Strategy Backtest Baseline Comparison JSON. Used when the file exists.",
        ),
        trial_ledger_path: Path = typer.Option(
            Path("data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json"),
            "--trial-ledger-path",
            help="Optional Strategy Backtest Trial Ledger JSON. Used when the file exists.",
        ),
        assumption_ledger_path: Path = typer.Option(
            Path(
                "data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json"
            ),
            "--assumption-ledger-path",
            help="Optional Strategy Backtest Assumption Ledger JSON. Used when the file exists.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Optional Strategy Backtest No-Lookahead Diff JSON. Used when the file exists.",
        ),
        execution_simulation_path: Path = typer.Option(
            Path(
                "data/research/backtest_execution_simulation/"
                "strategy_backtest_execution_simulation.json"
            ),
            "--execution-simulation-path",
            help="Optional Strategy Backtest Execution Simulation JSON. Used when the file exists.",
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
        selected_portfolio_comparison_path = (
            portfolio_comparison_path
            if portfolio_comparison_path.is_absolute()
            else settings.data_dir.parent / portfolio_comparison_path
        )
        selected_metric_extension_path = (
            metric_extension_path
            if metric_extension_path.is_absolute()
            else settings.data_dir.parent / metric_extension_path
        )
        selected_report_extension_path = (
            report_extension_path
            if report_extension_path.is_absolute()
            else settings.data_dir.parent / report_extension_path
        )
        selected_stress_path = (
            stress_path if stress_path.is_absolute() else settings.data_dir.parent / stress_path
        )
        selected_regime_split_path = (
            regime_split_path
            if regime_split_path.is_absolute()
            else settings.data_dir.parent / regime_split_path
        )
        selected_rolling_stability_path = (
            rolling_stability_path
            if rolling_stability_path.is_absolute()
            else settings.data_dir.parent / rolling_stability_path
        )
        selected_benchmark_relative_path = (
            benchmark_relative_path
            if benchmark_relative_path.is_absolute()
            else settings.data_dir.parent / benchmark_relative_path
        )
        selected_data_availability_path = (
            data_availability_path
            if data_availability_path.is_absolute()
            else settings.data_dir.parent / data_availability_path
        )
        selected_baseline_comparison_path = (
            baseline_comparison_path
            if baseline_comparison_path.is_absolute()
            else settings.data_dir.parent / baseline_comparison_path
        )
        selected_trial_ledger_path = (
            trial_ledger_path
            if trial_ledger_path.is_absolute()
            else settings.data_dir.parent / trial_ledger_path
        )
        selected_assumption_ledger_path = (
            assumption_ledger_path
            if assumption_ledger_path.is_absolute()
            else settings.data_dir.parent / assumption_ledger_path
        )
        selected_no_lookahead_path = (
            no_lookahead_path
            if no_lookahead_path.is_absolute()
            else settings.data_dir.parent / no_lookahead_path
        )
        selected_execution_simulation_path = (
            execution_simulation_path
            if execution_simulation_path.is_absolute()
            else settings.data_dir.parent / execution_simulation_path
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
                portfolio_comparison_path=selected_portfolio_comparison_path
                if selected_portfolio_comparison_path.exists()
                else None,
                metric_extension_path=selected_metric_extension_path
                if selected_metric_extension_path.exists()
                else None,
                report_extension_path=selected_report_extension_path
                if selected_report_extension_path.exists()
                else None,
                stress_path=selected_stress_path if selected_stress_path.exists() else None,
                regime_split_path=selected_regime_split_path
                if selected_regime_split_path.exists()
                else None,
                rolling_stability_path=selected_rolling_stability_path
                if selected_rolling_stability_path.exists()
                else None,
                benchmark_relative_path=selected_benchmark_relative_path
                if selected_benchmark_relative_path.exists()
                else None,
                data_availability_path=selected_data_availability_path
                if selected_data_availability_path.exists()
                else None,
                baseline_comparison_path=selected_baseline_comparison_path
                if selected_baseline_comparison_path.exists()
                else None,
                trial_ledger_path=selected_trial_ledger_path
                if selected_trial_ledger_path.exists()
                else None,
                assumption_ledger_path=selected_assumption_ledger_path
                if selected_assumption_ledger_path.exists()
                else None,
                no_lookahead_path=selected_no_lookahead_path
                if selected_no_lookahead_path.exists()
                else None,
                execution_simulation_path=selected_execution_simulation_path
                if selected_execution_simulation_path.exists()
                else None,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_comparison={result.comparison_path}")
        typer.echo(f"backtest_comparison_report={result.report_path}")

    @app.command("strategy-backtest-data-availability")
    def strategy_backtest_data_availability_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy Authoring signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Strategy Authoring quotes parquet.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_data_availability"),
            "--out",
            help="Output directory for data availability ledger.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_backtest_data_availability_ledger(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_data_availability={result.ledger_path}")
        typer.echo(f"backtest_data_availability_report={result.report_path}")

    @app.command("strategy-backtest-baseline-compare")
    def strategy_backtest_baseline_compare_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_baseline_comparison"),
            "--out",
            help="Output directory for baseline comparison artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_baseline_comparison(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_baseline_comparison={result.comparison_path}")
        typer.echo(f"backtest_baseline_comparison_report={result.report_path}")

    @app.command("strategy-backtest-no-lookahead-diff")
    def strategy_backtest_no_lookahead_diff_cmd(
        spec: Path | None = typer.Option(
            Path("docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml"),
            "--spec",
            help="Optional Strategy Authoring spec for runtime future-row mutation replay.",
        ),
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy Authoring signals parquet.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Strategy Authoring quotes parquet.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_no_lookahead"),
            "--out",
            help="Output directory for no-lookahead diff artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_spec = (
            _resolve_workspace_path(spec, settings.data_dir) if spec is not None else None
        )
        try:
            result = build_strategy_backtest_no_lookahead_diff(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                quotes_path=_resolve_workspace_path(quotes_path, settings.data_dir),
                spec_path=selected_spec,
                data_dir=settings.data_dir if selected_spec is not None else None,
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_no_lookahead_diff={result.diff_path}")
        typer.echo(f"backtest_no_lookahead_diff_report={result.report_path}")

    @app.command("strategy-backtest-execution-sim")
    def strategy_backtest_execution_sim_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        signals_path: Path = typer.Option(
            Path("data/research/strategy_signals.parquet"),
            "--signals-path",
            help="Strategy Authoring signals parquet.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_execution_simulation"),
            "--out",
            help="Output directory for execution simulation artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_execution_simulation(
                metrics_path=_resolve_workspace_path(metrics_path, settings.data_dir),
                signals_path=_resolve_workspace_path(signals_path, settings.data_dir),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_execution_simulation={result.simulation_path}")
        typer.echo(f"backtest_execution_simulation_report={result.report_path}")

    @app.command("strategy-backtest-assumption-ledger")
    def strategy_backtest_assumption_ledger_cmd(
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Backtest Data Availability Ledger JSON.",
        ),
        baseline_comparison_path: Path = typer.Option(
            Path(
                "data/research/backtest_baseline_comparison/"
                "strategy_backtest_baseline_comparison.json"
            ),
            "--baseline-comparison-path",
            help="Strategy Backtest Baseline Comparison JSON.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Strategy Backtest No-Lookahead Diff JSON.",
        ),
        execution_simulation_path: Path = typer.Option(
            Path(
                "data/research/backtest_execution_simulation/"
                "strategy_backtest_execution_simulation.json"
            ),
            "--execution-simulation-path",
            help="Strategy Backtest Execution Simulation JSON.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_assumption_ledger"),
            "--out",
            help="Output directory for assumption ledger artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_strategy_backtest_assumption_ledger(
                data_availability_path=_resolve_workspace_path(
                    data_availability_path, settings.data_dir
                ),
                baseline_comparison_path=_resolve_workspace_path(
                    baseline_comparison_path, settings.data_dir
                ),
                no_lookahead_path=_resolve_workspace_path(no_lookahead_path, settings.data_dir),
                execution_simulation_path=_resolve_workspace_path(
                    execution_simulation_path, settings.data_dir
                ),
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_assumption_ledger={result.ledger_path}")
        typer.echo(f"backtest_assumption_ledger_report={result.report_path}")

    @app.command("strategy-backtest-trial-ledger")
    def strategy_backtest_trial_ledger_cmd(
        out: Path = typer.Option(
            Path("data/research/backtest_trial_ledger"),
            "--out",
            help="Output directory for trial ledger artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        root = settings.data_dir.parent
        artifacts = {
            "backtest_metrics": root / "data/research/strategy_backtest_metrics.json",
            "suite_result": root
            / "data/research/backtest_suite/strategy_backtest_suite_result.json",
            "baseline_comparison": root
            / "data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json",
            "data_availability": root
            / "data/research/backtest_data_availability/backtest_data_availability_ledger.json",
            "no_lookahead_diff": root
            / "data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json",
            "execution_simulation": root
            / "data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json",
        }
        result = build_strategy_backtest_trial_ledger(
            artifacts=artifacts,
            out_dir=_resolve_workspace_path(out, settings.data_dir),
            reports_dir=_resolve_workspace_path(reports_dir, settings.data_dir),
        )
        typer.echo(f"backtest_trial_ledger={result.ledger_path}")
        typer.echo(f"backtest_trial_ledger_report={result.report_path}")

    @app.command("strategy-backtest-portfolio-compare")
    def strategy_backtest_portfolio_compare_cmd(
        bundle_path: Path = typer.Option(
            Path("data/research/strategy_authoring_bundle_result.json"),
            "--bundle-path",
            help="Strategy Authoring bundle result JSON.",
        ),
        price_frame_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--price-frame-path",
            help="Quotes or price frame parquet used by the optional bt adapter.",
        ),
        allocation_rule_id: str = typer.Option(
            "fixed_weight",
            "--allocation-rule-id",
            help="Allocation rule label recorded in the portfolio comparison artifact.",
        ),
        rebalance_cadence: str = typer.Option(
            "initial_only",
            "--rebalance-cadence",
            help="Rebalance cadence label recorded in the portfolio comparison artifact.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_portfolio"),
            "--out",
            help="Output directory for portfolio comparison artifact.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_bundle_path = _resolve_workspace_path(bundle_path, settings.data_dir)
        selected_price_frame_path = _resolve_workspace_path(price_frame_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_portfolio_comparison(
                bundle_path=selected_bundle_path,
                price_frame_path=selected_price_frame_path,
                allocation_rule_id=allocation_rule_id,
                rebalance_cadence=rebalance_cadence,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_portfolio_comparison={result.comparison_path}")
        typer.echo(f"backtest_portfolio_comparison_report={result.report_path}")

    @app.command("strategy-backtest-metric-extension")
    def strategy_backtest_metric_extension_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        frequency: str = typer.Option(
            "daily",
            "--frequency",
            help="Return frequency label for empyrical metrics: daily, weekly, monthly, or signal.",
        ),
        risk_free_rate: float = typer.Option(
            0.0,
            "--risk-free-rate",
            help="Risk-free rate passed to optional empyrical metrics.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_metric_extension"),
            "--out",
            help="Output directory for metric extension artifacts.",
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
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_metric_extension(
                metrics_path=selected_metrics_path,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_metric_extension={result.metric_extension_path}")
        typer.echo(f"backtest_returns_series={result.returns_series_path}")
        typer.echo(f"backtest_metric_extension_report={result.report_path}")

    @app.command("strategy-backtest-report-extension")
    def strategy_backtest_report_extension_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        frequency: str = typer.Option(
            "daily",
            "--frequency",
            help="Return frequency label for quantstats report: daily, weekly, monthly, or signal.",
        ),
        risk_free_rate: float = typer.Option(
            0.0,
            "--risk-free-rate",
            help="Risk-free rate passed to optional quantstats report generation.",
        ),
        show_framework_warnings: bool = typer.Option(
            False,
            "--show-framework-warnings",
            help="Show warnings emitted by optional quantstats report generation.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_report_extension"),
            "--out",
            help="Output directory for report extension artifacts.",
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
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_report_extension(
                metrics_path=selected_metrics_path,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                suppress_framework_warnings=not show_framework_warnings,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_report_extension={result.report_extension_path}")
        typer.echo(f"backtest_report_returns_series={result.returns_series_path}")
        if result.quantstats_html_path is not None:
            typer.echo(f"backtest_quantstats_html={result.quantstats_html_path}")
        typer.echo(f"backtest_report_extension_report={result.report_path}")

    @app.command("strategy-backtest-stress")
    def strategy_backtest_stress_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        scenario_csv: str = typer.Option(
            DEFAULT_SCENARIO_CSV,
            "--scenario-csv",
            help="Comma-separated stress scenarios as id:additional_cost_bps:additional_slippage_bps.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_stress"),
            "--out",
            help="Output directory for stress artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_stress(
                metrics_path=selected_metrics_path,
                scenario_csv=scenario_csv,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_stress={result.stress_path}")
        typer.echo(f"backtest_stress_report={result.report_path}")

    @app.command("strategy-backtest-regime-split")
    def strategy_backtest_regime_split_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        dimension_csv: str = typer.Option(
            DEFAULT_DIMENSION_CSV,
            "--dimension-csv",
            help="Comma-separated dimensions. Supports row fields plus ts_date, ts_weekday, and ts_hour.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_regime_split"),
            "--out",
            help="Output directory for regime split artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_regime_split(
                metrics_path=selected_metrics_path,
                dimension_csv=dimension_csv,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_regime_split={result.regime_split_path}")
        typer.echo(f"backtest_regime_split_report={result.report_path}")

    @app.command("strategy-backtest-rolling-stability")
    def strategy_backtest_rolling_stability_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        window_csv: str = typer.Option(
            DEFAULT_WINDOW_CSV,
            "--window-csv",
            help="Comma-separated positive integer rolling return window sizes.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_rolling_stability"),
            "--out",
            help="Output directory for rolling stability artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_rolling_stability(
                metrics_path=selected_metrics_path,
                window_csv=window_csv,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_rolling_stability={result.rolling_stability_path}")
        typer.echo(f"backtest_rolling_stability_report={result.report_path}")

    @app.command("strategy-backtest-benchmark-relative")
    def strategy_backtest_benchmark_relative_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            help="Strategy Authoring backtest metrics JSON.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/research/strategy_authoring_baseline_quotes.parquet"),
            "--quotes-path",
            help="Optional quote parquet used to derive benchmark returns.",
        ),
        benchmark_series_path: Path | None = typer.Option(
            None,
            "--benchmark-series-path",
            help="Optional local benchmark return series file. Supports parquet, csv, jsonl, ndjson, and json.",
        ),
        benchmark_return_column: str = typer.Option(
            DEFAULT_BENCHMARK_RETURN_COLUMN,
            "--benchmark-return-column",
            help="Executed signal result column used when row-level benchmark returns exist.",
        ),
        benchmark_series_return_column: str = typer.Option(
            DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
            "--benchmark-series-return-column",
            help="Benchmark return column in --benchmark-series-path.",
        ),
        price_column: str = typer.Option(
            DEFAULT_PRICE_COLUMN,
            "--price-column",
            help="Quote price column used to derive benchmark returns.",
        ),
        horizon_minutes: int = typer.Option(
            DEFAULT_HORIZON_MINUTES,
            "--horizon-minutes",
            help="Benchmark return horizon in minutes when using quote data.",
        ),
        out: Path = typer.Option(
            Path("data/research/backtest_benchmark_relative"),
            "--out",
            help="Output directory for benchmark-relative artifacts.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_quotes_path = _resolve_workspace_path(quotes_path, settings.data_dir)
        selected_benchmark_series_path = (
            _resolve_workspace_path(benchmark_series_path, settings.data_dir)
            if benchmark_series_path is not None
            else None
        )
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_benchmark_relative(
                metrics_path=selected_metrics_path,
                quotes_path=selected_quotes_path if selected_quotes_path.exists() else None,
                benchmark_series_path=selected_benchmark_series_path,
                benchmark_return_column=benchmark_return_column,
                benchmark_series_return_column=benchmark_series_return_column,
                price_column=price_column,
                horizon_minutes=horizon_minutes,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_benchmark_relative={result.benchmark_relative_path}")
        typer.echo(f"backtest_benchmark_relative_report={result.report_path}")

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
        selected_metrics_path = _resolve_workspace_path(metrics_path, settings.data_dir)
        selected_bundle_path = _resolve_workspace_path(bundle_path, settings.data_dir)
        selected_price_frame_path = _resolve_workspace_path(price_frame_path, settings.data_dir)
        selected_signals_path = _resolve_workspace_path(signals_path, settings.data_dir)
        selected_quotes_path = _resolve_workspace_path(quotes_path, settings.data_dir)
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            result = build_strategy_backtest_framework_run(
                frameworks=framework,
                metrics_path=selected_metrics_path,
                bundle_path=selected_bundle_path,
                price_frame_path=selected_price_frame_path,
                signals_path=selected_signals_path,
                quotes_path=selected_quotes_path,
                label_horizon_minutes=label_horizon_minutes,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                suppress_framework_warnings=not show_framework_warnings,
                out_dir=selected_out,
                reports_dir=selected_reports,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_framework_run={result.run_path}")
        typer.echo(f"backtest_framework_run_report={result.report_path}")
        typer.echo(f"framework_count={result.payload['summary']['framework_count']}")
        typer.echo(f"executed_count={result.payload['summary']['executed_count']}")

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
        bundle: Path = typer.Option(
            Path("docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml"),
            "--bundle",
            help="Strategy Authoring bundle YAML used for portfolio allocation comparison.",
        ),
        label_horizon_minutes: int = typer.Option(
            240,
            "--label-horizon-minutes",
            help="Holding horizon used to build optional external framework exits.",
        ),
        benchmark_series_path: Path | None = typer.Option(
            None,
            "--benchmark-series-path",
            help="Optional local benchmark return series file passed to benchmark-relative artifact generation.",
        ),
        benchmark_series_return_column: str = typer.Option(
            DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
            "--benchmark-series-return-column",
            help="Benchmark return column in --benchmark-series-path.",
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
        selected_bundle = _resolve_workspace_path(bundle, settings.data_dir)
        selected_benchmark_series_path = (
            _resolve_workspace_path(benchmark_series_path, settings.data_dir)
            if benchmark_series_path is not None
            else None
        )
        selected_out = _resolve_workspace_path(out, settings.data_dir)
        selected_reports = _resolve_workspace_path(reports_dir, settings.data_dir)
        try:
            run_result = run_strategy_backtest_pack(
                StrategyBacktestPackRunInputs(
                    spec_path=selected_spec,
                    suite_path=selected_suite,
                    bundle_path=selected_bundle,
                    label_horizon_minutes=label_horizon_minutes,
                    benchmark_series_path=selected_benchmark_series_path,
                    benchmark_series_return_column=benchmark_series_return_column,
                    out_dir=selected_out,
                    reports_dir=selected_reports,
                    data_dir=settings.data_dir,
                )
            )
        except (FileNotFoundError, ValueError, StrategyAuthoringValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"backtest_pack={run_result.pack_path}")
        typer.echo(f"backtest_pack_report={run_result.pack_report_path}")
        typer.echo(f"backtest_pack_validation={run_result.validation_path}")
        typer.echo(f"backtest_pack_validation_report={run_result.validation_report_path}")
        typer.echo(f"backtest_comparison={run_result.comparison_path}")
        typer.echo(f"backtest_portfolio_comparison={run_result.portfolio_comparison_path}")
        typer.echo(f"backtest_metric_extension={run_result.metric_extension_path}")
        typer.echo(f"backtest_report_extension={run_result.report_extension_path}")
        typer.echo(f"backtest_stress={run_result.stress_path}")
        typer.echo(f"backtest_regime_split={run_result.regime_split_path}")
        typer.echo(f"backtest_rolling_stability={run_result.rolling_stability_path}")
        typer.echo(f"backtest_benchmark_relative={run_result.benchmark_relative_path}")
        typer.echo(f"backtest_data_availability={run_result.data_availability_path}")
        typer.echo(f"backtest_baseline_comparison={run_result.baseline_comparison_path}")
        typer.echo(f"backtest_no_lookahead_diff={run_result.no_lookahead_path}")
        typer.echo(f"backtest_execution_simulation={run_result.execution_simulation_path}")
        typer.echo(f"backtest_assumption_ledger={run_result.assumption_ledger_path}")
        typer.echo(f"backtest_trial_ledger={run_result.trial_ledger_path}")
        typer.echo(f"backtest_suite_result={run_result.suite_result_path}")
        if run_result.validation_decision != "PASS":
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

    @app.command("strategy-backtest-artifact-summary")
    def strategy_backtest_artifact_summary_cmd(
        pack_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack.json"),
            "--pack-path",
            help="Strategy backtest pack manifest JSON.",
        ),
        validation_path: Path = typer.Option(
            Path("data/research/backtest_pack/strategy_backtest_pack_validation.json"),
            "--validation-path",
            help="Strategy backtest pack validation JSON.",
        ),
        benchmark_relative_path: Path = typer.Option(
            Path(
                "data/research/backtest_benchmark_relative/"
                "strategy_backtest_benchmark_relative.json"
            ),
            "--benchmark-relative-path",
            help="Strategy backtest benchmark-relative JSON.",
        ),
        metric_extension_path: Path = typer.Option(
            Path("data/research/backtest_metric_extension/strategy_backtest_metric_extension.json"),
            "--metric-extension-path",
            help="Strategy backtest metric extension JSON.",
        ),
        report_extension_path: Path = typer.Option(
            Path("data/research/backtest_report_extension/strategy_backtest_report_extension.json"),
            "--report-extension-path",
            help="Strategy backtest report extension JSON.",
        ),
        stress_path: Path = typer.Option(
            Path("data/research/backtest_stress/strategy_backtest_stress.json"),
            "--stress-path",
            help="Strategy backtest stress JSON.",
        ),
        regime_split_path: Path = typer.Option(
            Path("data/research/backtest_regime_split/strategy_backtest_regime_split.json"),
            "--regime-split-path",
            help="Strategy backtest regime split JSON.",
        ),
        rolling_stability_path: Path = typer.Option(
            Path(
                "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
            ),
            "--rolling-stability-path",
            help="Strategy backtest rolling stability JSON.",
        ),
        data_availability_path: Path = typer.Option(
            Path("data/research/backtest_data_availability/backtest_data_availability_ledger.json"),
            "--data-availability-path",
            help="Backtest data availability ledger JSON.",
        ),
        baseline_comparison_path: Path = typer.Option(
            Path(
                "data/research/backtest_baseline_comparison/"
                "strategy_backtest_baseline_comparison.json"
            ),
            "--baseline-comparison-path",
            help="Strategy backtest baseline comparison JSON.",
        ),
        trial_ledger_path: Path = typer.Option(
            Path("data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json"),
            "--trial-ledger-path",
            help="Strategy backtest trial ledger JSON.",
        ),
        assumption_ledger_path: Path = typer.Option(
            Path(
                "data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json"
            ),
            "--assumption-ledger-path",
            help="Strategy backtest assumption ledger JSON.",
        ),
        no_lookahead_path: Path = typer.Option(
            Path("data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"),
            "--no-lookahead-path",
            help="Strategy backtest no-lookahead diff JSON.",
        ),
        execution_simulation_path: Path = typer.Option(
            Path(
                "data/research/backtest_execution_simulation/"
                "strategy_backtest_execution_simulation.json"
            ),
            "--execution-simulation-path",
            help="Strategy backtest execution simulation JSON.",
        ),
        comparison_path: Path = typer.Option(
            Path("data/research/backtest_compare/strategy_backtest_comparison.json"),
            "--comparison-path",
            help="Strategy backtest comparison JSON.",
        ),
    ) -> None:
        settings = get_settings()
        selected_pack_path = _resolve_workspace_path(pack_path, settings.data_dir)
        selected_validation_path = _resolve_workspace_path(validation_path, settings.data_dir)
        selected_benchmark_relative_path = _resolve_workspace_path(
            benchmark_relative_path, settings.data_dir
        )
        selected_metric_extension_path = _resolve_workspace_path(
            metric_extension_path, settings.data_dir
        )
        selected_report_extension_path = _resolve_workspace_path(
            report_extension_path, settings.data_dir
        )
        selected_stress_path = _resolve_workspace_path(stress_path, settings.data_dir)
        selected_regime_split_path = _resolve_workspace_path(regime_split_path, settings.data_dir)
        selected_rolling_stability_path = _resolve_workspace_path(
            rolling_stability_path, settings.data_dir
        )
        selected_data_availability_path = _resolve_workspace_path(
            data_availability_path, settings.data_dir
        )
        selected_baseline_comparison_path = _resolve_workspace_path(
            baseline_comparison_path, settings.data_dir
        )
        selected_trial_ledger_path = _resolve_workspace_path(trial_ledger_path, settings.data_dir)
        selected_assumption_ledger_path = _resolve_workspace_path(
            assumption_ledger_path, settings.data_dir
        )
        selected_no_lookahead_path = _resolve_workspace_path(no_lookahead_path, settings.data_dir)
        selected_execution_simulation_path = _resolve_workspace_path(
            execution_simulation_path, settings.data_dir
        )
        selected_comparison_path = _resolve_workspace_path(comparison_path, settings.data_dir)
        try:
            result = build_strategy_backtest_artifact_summary(
                pack_path=selected_pack_path,
                validation_path=selected_validation_path,
                benchmark_relative_path=selected_benchmark_relative_path,
                metric_extension_path=selected_metric_extension_path,
                report_extension_path=selected_report_extension_path,
                stress_path=selected_stress_path,
                regime_split_path=selected_regime_split_path,
                rolling_stability_path=selected_rolling_stability_path,
                data_availability_path=selected_data_availability_path,
                baseline_comparison_path=selected_baseline_comparison_path,
                trial_ledger_path=selected_trial_ledger_path,
                assumption_ledger_path=selected_assumption_ledger_path,
                no_lookahead_path=selected_no_lookahead_path,
                execution_simulation_path=selected_execution_simulation_path,
                comparison_path=selected_comparison_path,
            )
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(json.dumps(result.payload, ensure_ascii=False, sort_keys=True))

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
