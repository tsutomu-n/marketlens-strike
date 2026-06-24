from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from pydantic import ValidationError
import typer

from sis.research.ndx.diagnostics import build_ndx_diagnostics
from sis.research.ndx.feature_panel import build_ndx_feature_panel
from sis.research.ndx.operator_promotion import run_operator_promotion
from sis.research.ndx.paper_observation_gate import run_paper_observation_gate
from sis.research.ndx.paper_observation_review import run_paper_observation_review
from sis.research.ndx.residual_model import build_open_gap_residuals
from sis.research.ndx.residual_validation import run_residual_validation_gate
from sis.research.ndx.source_resolution import build_source_resolution
from sis.research.ndx.start_conditions import Layer23StartConditionError
from sis.research.ndx.strategy_lab_export import export_ndx_strategy_lab_research_artifact
from sis.settings import get_settings


def register_research_ndx_commands(app: typer.Typer) -> None:
    @app.command("research-ndx-source-resolve")
    def research_ndx_source_resolve_cmd(
        root: Path = typer.Option(
            Path("configs/research_layer_2_2/ndx"),
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 NDX config root used for start-condition verification.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Layer 2.2 NDX artifact directory.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX Layer 2.3 artifacts.",
        ),
    ) -> None:
        try:
            result = build_source_resolution(root=root, artifact_dir=artifact_dir, out_dir=out)
        except (Layer23StartConditionError, FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"data_source_resolution={result.artifact_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"resolved_count={result.resolved_count}")
        typer.echo(f"deferred_count={result.deferred_count}")

    @app.command("research-ndx-feature-panel")
    def research_ndx_feature_panel_cmd(
        root: Path = typer.Option(
            Path("configs/research_layer_2_2/ndx"),
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 NDX config root used for start-condition verification.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Layer 2.2 NDX artifact directory.",
        ),
        input_root: Path = typer.Option(
            ...,
            "--input-root",
            exists=True,
            file_okay=False,
            help="Directory containing fixture-first NDX source CSV files.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX feature panel artifacts.",
        ),
    ) -> None:
        try:
            result = build_ndx_feature_panel(
                root=root,
                artifact_dir=artifact_dir,
                input_root=input_root,
                out_dir=out,
            )
        except (Layer23StartConditionError, FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"feature_panel={result.panel_path}")
        typer.echo(f"feature_manifest={result.manifest_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"row_count={result.row_count}")

    @app.command("research-ndx-residual")
    def research_ndx_residual_cmd(
        feature_panel: Path = typer.Option(
            ...,
            "--feature-panel",
            exists=True,
            dir_okay=False,
            help="NDX feature panel parquet path.",
        ),
        feature_manifest: Path = typer.Option(
            Path("data/research/ndx/ndx_feature_manifest.json"),
            "--feature-manifest",
            exists=True,
            dir_okay=False,
            help="NDX feature manifest JSON path.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX residual artifacts.",
        ),
        min_window: int = typer.Option(
            6,
            "--min-window",
            min=6,
            help="Minimum strictly prior rows for rolling OLS.",
        ),
    ) -> None:
        try:
            result = build_open_gap_residuals(
                feature_panel_path=feature_panel,
                feature_manifest_path=feature_manifest,
                out_dir=out,
                min_window=min_window,
            )
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"open_gap_residuals={result.residuals_path}")
        typer.echo(f"residual_manifest={result.manifest_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"row_count={result.row_count}")

    @app.command("research-ndx-diagnostics")
    def research_ndx_diagnostics_cmd(
        residuals: Path = typer.Option(
            ...,
            "--residuals",
            exists=True,
            dir_okay=False,
            help="NDX open gap residual parquet path.",
        ),
        residual_manifest: Path = typer.Option(
            Path("data/research/ndx/open_gap_residual_manifest.json"),
            "--residual-manifest",
            exists=True,
            dir_okay=False,
            help="NDX open gap residual manifest JSON path.",
        ),
        out: Path = typer.Option(
            Path("data/reports"),
            "--out",
            file_okay=False,
            help="Output directory for NDX diagnostics and pre-reports.",
        ),
    ) -> None:
        try:
            result = build_ndx_diagnostics(
                residuals_path=residuals,
                residual_manifest_path=residual_manifest,
                out_dir=out,
            )
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"diagnostics={result.diagnostics_path}")
        typer.echo(f"neutralized_residuals={result.neutralized_path}")
        typer.echo(f"neutralization_report={result.neutralization_report_path}")
        typer.echo(f"refutation_report={result.refutation_report_path}")
        typer.echo(f"row_count={result.row_count}")

    @app.command("research-ndx-residual-validate")
    def research_ndx_residual_validate_cmd(
        root: Path = typer.Option(
            Path("configs/research_layer_2_2/ndx"),
            "--root",
            exists=True,
            file_okay=False,
            help="Layer 2.2 NDX config root used for start-condition verification.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="Layer 2.3 NDX artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Directory containing Layer 2.3 NDX diagnostic reports.",
        ),
        out: Path = typer.Option(
            Path("data/research/ndx"),
            "--out",
            file_okay=False,
            help="Output directory for NDX Layer 2.4 residual validation artifacts.",
        ),
    ) -> None:
        try:
            result = run_residual_validation_gate(
                root=root,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                out_dir=out,
            )
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"reason_codes={','.join(result.reason_codes)}")
        typer.echo(f"residual_validation_summary={result.summary_path}")
        typer.echo(f"residual_validation_decision={result.decision_path}")
        typer.echo(f"report={result.report_path}")
        typer.echo(f"counter_dag_refutation_report={result.counter_dag_report_path}")

    @app.command("research-ndx-strategy-lab-export")
    def research_ndx_strategy_lab_export_cmd(
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="NDX Layer 2.3/2.4 artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Directory containing NDX residual diagnostic reports.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing",
            help="Overwrite existing Strategy Lab signal artifacts and record previous hashes.",
        ),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = export_ndx_strategy_lab_research_artifact(
                data_dir=effective_data_dir,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                replace_existing=replace_existing,
            )
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"export_id={result.export_id}")
        typer.echo(f"signal_count={result.signal_count}")
        typer.echo(f"strategy_signals={result.signals_path}")
        typer.echo(f"strategy_signal_manifest={result.signal_manifest_path}")
        typer.echo(f"export_manifest={result.export_manifest_path}")
        typer.echo(f"report={result.report_path}")

    @app.command("research-ndx-paper-observation-gate")
    def research_ndx_paper_observation_gate_cmd(
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="NDX Layer 2.5 artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
        quotes_path: Path = typer.Option(
            Path("data/normalized/quotes.parquet"),
            "--quotes-path",
            dir_okay=False,
            help="Local normalized quote parquet for paper revalidation evidence.",
        ),
        min_era_count: int = typer.Option(3, "--min-era-count", min=1),
        min_signal_count: int = typer.Option(30, "--min-signal-count", min=1),
        max_tested_variant_count: int = typer.Option(1, "--max-tested-variant-count", min=1),
        fixture_evidence_policy: str = typer.Option("warn", "--fixture-evidence-policy"),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_paper_observation_gate(
                data_dir=effective_data_dir,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                quotes_path=quotes_path,
                min_era_count=min_era_count,
                min_signal_count=min_signal_count,
                max_tested_variant_count=max_tested_variant_count,
                fixture_evidence_policy=fixture_evidence_policy,
            )
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"decision_id={result.decision_id}")
        typer.echo(f"paper_observation_gate_decision={result.decision_path}")
        typer.echo(f"report={result.report_path}")

    @app.command("research-ndx-operator-promotion")
    def research_ndx_operator_promotion_cmd(
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="NDX Layer 2.6 artifact directory.",
        ),
        decision: str = typer.Option("hold", "--decision"),
        reviewer: str | None = typer.Option(None, "--reviewer"),
        approval_reason: list[str] | None = typer.Option(None, "--approval-reason"),
        rejection_reason: list[str] | None = typer.Option(None, "--rejection-reason"),
    ) -> None:
        if decision not in {"promote_to_paper_observation", "hold", "reject"}:
            typer.echo("decision must be one of: promote_to_paper_observation, hold, reject")
            raise typer.Exit(2)
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_operator_promotion(
                data_dir=effective_data_dir,
                artifact_dir=artifact_dir,
                decision=cast(Literal["promote_to_paper_observation", "hold", "reject"], decision),
                reviewer=reviewer,
                approval_reasons=list(approval_reason or []),
                rejection_reasons=list(rejection_reason or []),
            )
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"promotion_id={result.promotion_id}")
        typer.echo(f"operator_promotion_decision={result.promotion_path}")
        typer.echo(f"report={result.report_path}")

    @app.command("research-ndx-paper-observation-review")
    def research_ndx_paper_observation_review_cmd(
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        artifact_dir: Path = typer.Option(
            Path("data/research/ndx"),
            "--artifact-dir",
            file_okay=False,
            help="NDX Layer 2.7 artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
        ledger_path: Path | None = typer.Option(
            None,
            "--ledger-path",
            dir_okay=False,
            help="Optional paper observation ledger path. Defaults to data/paper/paper_observation_ledger.jsonl.",
        ),
        session_manifest_path: Path | None = typer.Option(
            None,
            "--session-manifest",
            dir_okay=False,
            help="Optional paper observation session manifest path.",
        ),
        min_fills_for_pass: int = typer.Option(20, "--min-fills-for-pass", min=1),
        min_trading_days_for_pass: int = typer.Option(10, "--min-trading-days-for-pass", min=1),
        max_blocked_rate: float = typer.Option(0.5, "--max-blocked-rate", min=0.0, max=1.0),
        max_consecutive_blocked: int = typer.Option(3, "--max-consecutive-blocked", min=1),
        max_open_position_age_hours: float = typer.Option(
            0.0, "--max-open-position-age-hours", min=0.0
        ),
        paper_notional_usd: float = typer.Option(1000.0, "--paper-notional-usd", min=0.01),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_paper_observation_review(
                data_dir=effective_data_dir,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                ledger_path=ledger_path,
                session_manifest_path=session_manifest_path,
                min_fills_for_pass=min_fills_for_pass,
                min_trading_days_for_pass=min_trading_days_for_pass,
                max_blocked_rate=max_blocked_rate,
                max_consecutive_blocked=max_consecutive_blocked,
                max_open_position_age_hours=max_open_position_age_hours,
                paper_notional_usd=paper_notional_usd,
            )
        except (
            FileNotFoundError,
            ValueError,
            TypeError,
            ValidationError,
            json.JSONDecodeError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"review_id={result.review_id}")
        typer.echo(f"paper_observation_review_decision={result.decision_path}")
        typer.echo(f"report={result.report_path}")
