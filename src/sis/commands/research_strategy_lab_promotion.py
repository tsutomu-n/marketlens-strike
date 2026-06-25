from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal, cast

from pydantic import ValidationError
import typer

from sis.commands.research_strategy_lab_support import _scorecard_summary_from_trial_group
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import run_id_from_pack_id
from sis.research.strategy_lifecycle.paper_observation_cycle import (
    build_fresh_paper_intent_preview,
)
from sis.settings import get_settings


def register_research_strategy_lab_promotion_commands(app: typer.Typer) -> None:
    @app.command("promotion-decision")
    def promotion_decision_cmd(
        source_pack: Path | None = typer.Option(
            None,
            "--source-pack",
            help="PaperCandidatePack JSON path. Defaults to data/research/paper_candidate_pack.json.",
        ),
        decision: str = typer.Option(
            "hold",
            "--decision",
            help=(
                "Operator decision to record: hold, reject, or promote. "
                "Promote requires all required evidence and remains paper-only."
            ),
        ),
    ) -> None:
        settings = get_settings()
        if decision not in {"promote", "reject", "hold"}:
            typer.echo("decision must be one of: promote, reject, hold")
            raise typer.Exit(2)
        promotion_value = cast(Literal["promote", "reject", "hold"], decision)
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        required = ["trial_ledger", "paper_candidate_pack"]
        observed = ["paper_candidate_pack"] if pack_path.exists() else []
        if (settings.data_dir / "research/trial_ledger.jsonl").exists():
            observed.append("trial_ledger")
        if not pack_path.exists():
            typer.echo(f"PaperCandidatePack not found: {pack_path}")
            raise typer.Exit(2)
        pack = PaperCandidatePack.model_validate(json.loads(pack_path.read_text(encoding="utf-8")))
        source_pack_id = pack.pack_id
        promotion_run_id = run_id_from_pack_id(source_pack_id)
        scorecard_summary = (
            _scorecard_summary_from_trial_group(settings.data_dir, pack.trial_group_id)
            if pack.trial_group_id
            else {}
        )
        if scorecard_summary:
            required.append("strategy_scorecard")
            observed.append("strategy_scorecard")
        promotion = PromotionDecision(
            schema_version="promotion_decision.v1",
            promotion_id=f"promotion-{promotion_run_id}",
            generated_at=datetime.now(timezone.utc),
            source_pack_id=source_pack_id,
            reviewer=None,
            from_stage="strategy_lab",
            to_stage="paper_observation",
            decision=promotion_value,
            required_evidence=required,
            observed_evidence=observed,
            approval_reasons=["operator_promoted"] if promotion_value == "promote" else [],
            rejection_reasons=[] if promotion_value == "promote" else ["not_promoted"],
            scorecard_summary=scorecard_summary,
        )
        out = settings.data_dir / "research/promotion_decision.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(promotion.model_dump_json(indent=2), encoding="utf-8")
        report_path = settings.data_dir / "reports/promotion_decision.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f"# Promotion Decision\n\n- decision: {promotion.decision}\n", encoding="utf-8"
        )
        typer.echo(f"promotion_decision={out}")

    @app.command("build-paper-intent-preview")
    def build_paper_intent_preview_cmd(
        source_pack: Path | None = typer.Option(
            None,
            "--source-pack",
            help="PaperCandidatePack JSON path. Defaults to data/research/paper_candidate_pack.json.",
        ),
        promotion_decision: Path | None = typer.Option(
            None,
            "--promotion-decision",
            help="PromotionDecision JSON path. Defaults to data/research/promotion_decision.json.",
        ),
    ) -> None:
        settings = get_settings()
        pack_path = source_pack or (settings.data_dir / "research/paper_candidate_pack.json")
        decision_path = promotion_decision or (
            settings.data_dir / "research/promotion_decision.json"
        )
        try:
            result = build_fresh_paper_intent_preview(
                data_dir=settings.data_dir,
                source_pack_path=pack_path,
                promotion_decision_path=decision_path,
                reports_dir=settings.data_dir / "reports",
            )
        except (FileNotFoundError, ValueError, TypeError, ValidationError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(2) from exc
        typer.echo(f"paper_intent_preview={result.intents_path}")
