from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError
import typer

from sis.research.strategy_lifecycle.backtest_acceptance import run_backtest_acceptance
from sis.research.strategy_lifecycle.paper_observation_cycle import (
    run_strategy_paper_observation_append,
    run_strategy_paper_observation_cycle,
)
from sis.research.strategy_lifecycle.paper_observation_status import (
    run_strategy_paper_observation_status,
)
from sis.research.strategy_lifecycle.review import run_strategy_lifecycle_review
from sis.settings import get_settings


def register_research_strategy_lifecycle_commands(app: typer.Typer) -> None:
    @app.command("strategy-backtest-acceptance")
    def strategy_backtest_acceptance_cmd(
        metrics_path: Path = typer.Option(
            Path("data/research/strategy_backtest_metrics.json"),
            "--metrics-path",
            dir_okay=False,
            help="Strategy Authoring backtest metrics JSON.",
        ),
        out_dir: Path = typer.Option(
            Path("data/research/strategy_lifecycle"),
            "--out",
            file_okay=False,
            help="Output strategy lifecycle artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
    ) -> None:
        try:
            result = run_backtest_acceptance(
                metrics_path=metrics_path,
                out_dir=out_dir,
                reports_dir=reports_dir,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"acceptance_id={result.acceptance_id}")
        typer.echo(f"backtest_acceptance_decision={result.decision_path}")
        typer.echo(f"report={result.report_path}")

    @app.command("strategy-lifecycle-review")
    def strategy_lifecycle_review_cmd(
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        backtest_decision_path: Path | None = typer.Option(
            None,
            "--backtest-decision-path",
            dir_okay=False,
            help="Optional strategy backtest acceptance decision path.",
        ),
        paper_review_path: Path | None = typer.Option(
            None,
            "--paper-review-path",
            dir_okay=False,
            help="Optional paper observation review decision path.",
        ),
        phase_gate_path: Path | None = typer.Option(
            None,
            "--phase-gate-path",
            dir_okay=False,
            help="Optional phase gate summary path.",
        ),
        out_dir: Path = typer.Option(
            Path("data/research/strategy_lifecycle"),
            "--out",
            file_okay=False,
            help="Output strategy lifecycle artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_strategy_lifecycle_review(
                data_dir=effective_data_dir,
                out_dir=out_dir,
                reports_dir=reports_dir,
                backtest_decision_path=backtest_decision_path,
                paper_review_path=paper_review_path,
                phase_gate_path=phase_gate_path,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"decision={result.decision}")
        typer.echo(f"review_id={result.review_id}")
        typer.echo(f"strategy_lifecycle_review={result.decision_path}")
        typer.echo(f"report={result.report_path}")

    @app.command("strategy-paper-observation-cycle")
    def strategy_paper_observation_cycle_cmd(
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
            help="NDX paper observation artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
        session_id: str | None = typer.Option(None, "--session-id"),
        backtest_acceptance_path: Path | None = typer.Option(
            None,
            "--backtest-acceptance-path",
            dir_okay=False,
            help="Optional strategy backtest acceptance decision path.",
        ),
        source_pack_path: Path | None = typer.Option(
            None,
            "--source-pack",
            dir_okay=False,
            help="Optional PaperCandidatePack path.",
        ),
        promotion_decision_path: Path | None = typer.Option(
            None,
            "--promotion-decision",
            dir_okay=False,
            help="Optional PromotionDecision path.",
        ),
        operator_promotion_path: Path | None = typer.Option(
            None,
            "--operator-promotion-path",
            dir_okay=False,
            help="Optional NDX operator promotion decision path.",
        ),
        min_fills_for_pass: int | None = typer.Option(None, "--min-fills-for-pass", min=1),
        min_trading_days_for_pass: int | None = typer.Option(
            None, "--min-trading-days-for-pass", min=1
        ),
        max_blocked_rate: float = typer.Option(0.5, "--max-blocked-rate", min=0.0, max=1.0),
        max_consecutive_blocked: int = typer.Option(3, "--max-consecutive-blocked", min=1),
        max_open_position_age_hours: float = typer.Option(
            0.0, "--max-open-position-age-hours", min=0.0
        ),
        paper_notional_usd: float = typer.Option(1000.0, "--paper-notional-usd", min=0.01),
        smoke: bool = typer.Option(
            False,
            "--smoke",
            help="Use smoke thresholds for local verification; not production paper pass evidence.",
        ),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_strategy_paper_observation_cycle(
                data_dir=effective_data_dir,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                session_id=session_id,
                backtest_acceptance_path=backtest_acceptance_path,
                source_pack_path=source_pack_path,
                promotion_decision_path=promotion_decision_path,
                operator_promotion_path=operator_promotion_path,
                min_fills_for_pass=min_fills_for_pass,
                min_trading_days_for_pass=min_trading_days_for_pass,
                max_blocked_rate=max_blocked_rate,
                max_consecutive_blocked=max_consecutive_blocked,
                max_open_position_age_hours=max_open_position_age_hours,
                paper_notional_usd=paper_notional_usd,
                smoke=smoke,
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
        typer.echo(f"session_id={result.session.session_id}")
        typer.echo(f"session_manifest={result.session.manifest_path}")
        typer.echo(f"observation_ledger={result.session.observation_ledger_path}")
        typer.echo(f"paper_review_decision={result.paper_review.decision}")
        typer.echo(f"lifecycle_decision={result.lifecycle_review.decision}")
        typer.echo(f"report={result.report_path}")

    @app.command("strategy-paper-observation-append")
    def strategy_paper_observation_append_cmd(
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
            help="NDX paper observation artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
        session_manifest_path: Path = typer.Option(
            ...,
            "--session-manifest",
            dir_okay=False,
            help="Existing paper observation session manifest path.",
        ),
        state_path: Path | None = typer.Option(
            None,
            "--state-path",
            dir_okay=False,
            help="Optional sqlite state path. Defaults to data/state/marketlens.sqlite.",
        ),
        paper_notional_usd: float = typer.Option(1000.0, "--paper-notional-usd", min=0.01),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_strategy_paper_observation_append(
                data_dir=effective_data_dir,
                artifact_dir=artifact_dir,
                reports_dir=reports_dir,
                session_manifest_path=session_manifest_path,
                state_path=state_path,
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
        typer.echo(f"session_id={result.session_id}")
        typer.echo(f"session_manifest={result.session_manifest_path}")
        typer.echo(f"observation_ledger={result.observation_ledger_path}")
        typer.echo(f"appended_ledger_entries={result.appended_ledger_entries}")
        typer.echo(f"ledger_entry_count={result.ledger_entry_count}")
        typer.echo(f"paper_review_decision={result.paper_review.decision}")
        typer.echo(f"lifecycle_decision={result.lifecycle_review.decision}")
        typer.echo(f"observation_state={result.status.observation_state}")
        typer.echo(f"next_action={result.status.next_action}")
        typer.echo(f"report={result.report_path}")

    @app.command("strategy-paper-observation-status")
    def strategy_paper_observation_status_cmd(
        data_dir: Path | None = typer.Option(
            None,
            "--data-dir",
            file_okay=False,
            help="Runtime data root. Defaults to SIS_DATA_DIR/settings data_dir.",
        ),
        canonical_review_path: Path | None = typer.Option(
            None,
            "--canonical-review-path",
            dir_okay=False,
            help="Optional canonical NDX paper observation review decision path.",
        ),
        lifecycle_review_path: Path | None = typer.Option(
            None,
            "--lifecycle-review-path",
            dir_okay=False,
            help="Optional strategy lifecycle review path.",
        ),
        sessions_root: Path | None = typer.Option(
            None,
            "--sessions-root",
            file_okay=False,
            help="Optional paper observation sessions root.",
        ),
        out_dir: Path = typer.Option(
            Path("data/research/strategy_lifecycle"),
            "--out",
            file_okay=False,
            help="Output strategy lifecycle artifact directory.",
        ),
        reports_dir: Path = typer.Option(
            Path("data/reports"),
            "--reports-dir",
            file_okay=False,
            help="Output report directory.",
        ),
    ) -> None:
        settings = get_settings()
        effective_data_dir = data_dir or settings.data_dir
        try:
            result = run_strategy_paper_observation_status(
                data_dir=effective_data_dir,
                out_dir=out_dir,
                reports_dir=reports_dir,
                canonical_review_path=canonical_review_path,
                lifecycle_review_path=lifecycle_review_path,
                sessions_root=sessions_root,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc
        typer.echo("status=pass")
        typer.echo(f"observation_state={result.observation_state}")
        typer.echo(f"next_action={result.next_action}")
        typer.echo(f"status_id={result.status_id}")
        typer.echo(f"paper_observation_status={result.status_path}")
        typer.echo(f"report={result.report_path}")
