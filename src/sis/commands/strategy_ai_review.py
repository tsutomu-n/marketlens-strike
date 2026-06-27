from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_ai_review.models import AIReviewModelReasoningEffort, AIReviewRecommendation
from sis.strategy_ai_review.service import (
    StrategyAIReviewError,
    StrategyAIReviewOutputExistsError,
    build_ai_review_packet,
    record_ai_review_note,
    record_structured_findings,
)


def register_strategy_ai_review_commands(app: typer.Typer) -> None:
    @app.command("strategy-ai-review-packet-build")
    def strategy_ai_review_packet_build_cmd(
        source: list[Path] | None = typer.Option(
            None,
            "--source",
            dir_okay=False,
            help="Source artifact JSON to summarize for AI review. Repeat for multiple artifacts.",
        ),
        out: Path = typer.Option(
            Path("data/strategy_ai_reviews"),
            "--out",
            help="Output directory for AI review packet artifacts.",
        ),
        packet_id: str = typer.Option(
            "ai-review-packet",
            "--packet-id",
            help="Packet id.",
        ),
        review_question: list[str] | None = typer.Option(
            None,
            "--review-question",
            help="Question to ask the AI reviewer. Repeat for multiple questions.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing packet artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = build_ai_review_packet(
                source_paths=[
                    _resolve_workspace_path(path, settings.data_dir) for path in (source or [])
                ],
                out_dir=_resolve_workspace_path(out, settings.data_dir),
                packet_id=packet_id,
                review_questions=review_question,
                replace_existing=replace_existing,
            )
        except (
            StrategyAIReviewOutputExistsError,
            StrategyAIReviewError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        packet = result.packet
        typer.echo("status=pass")
        typer.echo(f"packet_status={packet.packet_status.value}")
        typer.echo(f"source_count={len(packet.source_summaries)}")
        typer.echo(f"context_section_count={len(packet.context_sections)}")
        typer.echo(f"sensitive_source_count={packet.sensitive_source_count}")
        typer.echo(f"packet_path={result.packet_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        if packet.packet_status.value != "READY_FOR_AI_REVIEW":
            raise typer.Exit(2)

    @app.command("strategy-ai-review-findings-structure")
    def strategy_ai_review_findings_structure_cmd(
        note: Path = typer.Option(
            ...,
            "--note",
            dir_okay=False,
            help="strategy_ai_review_note.v1 JSON.",
        ),
        structured_finding_json: Path = typer.Option(
            ...,
            "--structured-finding-json",
            dir_okay=False,
            help="JSON array of manually structured finding inputs.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            help="Output directory. Defaults to note directory.",
        ),
        finding_set_id: str = typer.Option(
            "ai-review-structured-findings",
            "--finding-set-id",
            help="Structured finding set id.",
        ),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing structured finding artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            structured_input_path = _resolve_workspace_path(
                structured_finding_json, settings.data_dir
            )
            raw_input: Any = json.loads(structured_input_path.read_text(encoding="utf-8"))
            if not isinstance(raw_input, list) or not all(
                isinstance(item, dict) for item in raw_input
            ):
                raise StrategyAIReviewError(
                    "--structured-finding-json must contain a JSON array of objects"
                )
            result = record_structured_findings(
                note_path=_resolve_workspace_path(note, settings.data_dir),
                structured_findings=raw_input,
                out_dir=_resolve_workspace_path(out, settings.data_dir)
                if out is not None
                else None,
                finding_set_id=finding_set_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyAIReviewOutputExistsError,
            StrategyAIReviewError,
            FileNotFoundError,
            ValueError,
            ValidationError,
            json.JSONDecodeError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        finding_set = result.finding_set
        typer.echo("status=pass")
        typer.echo(f"finding_set_status={finding_set.finding_set_status.value}")
        typer.echo(f"finding_count={len(finding_set.findings)}")
        typer.echo(f"auto_applied={str(finding_set.auto_applied).lower()}")
        typer.echo(f"permission_allowed={str(finding_set.permission_allowed).lower()}")
        typer.echo(f"finding_set_path={result.finding_set_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")

    @app.command("strategy-ai-review-note-record")
    def strategy_ai_review_note_record_cmd(
        packet: Path = typer.Option(
            ...,
            "--packet",
            dir_okay=False,
            help="strategy_ai_review_packet.v1 JSON.",
        ),
        provider: str = typer.Option(..., "--provider", help="AI provider name."),
        model: str = typer.Option(..., "--model", help="AI model name."),
        model_reasoning_effort: AIReviewModelReasoningEffort | None = typer.Option(
            None,
            "--model-reasoning-effort",
            help="AI model reasoning effort used for the review.",
        ),
        prompt_hash: str = typer.Option(
            ...,
            "--prompt-hash",
            help="sha256 hash of the prompt sent to the AI reviewer.",
        ),
        finding: list[str] = typer.Option(
            ...,
            "--finding",
            help="AI finding. Repeat for multiple findings.",
        ),
        limitation: list[str] = typer.Option(
            ...,
            "--limitation",
            help="AI limitation. Repeat for multiple limitations.",
        ),
        recommendation: AIReviewRecommendation = typer.Option(
            ...,
            "--recommendation",
            help="AI recommendation for human review.",
        ),
        disagreement: list[str] | None = typer.Option(
            None,
            "--disagreement",
            help="Disagreement with another AI/human note. Repeat for multiple disagreements.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            help="Output directory. Defaults to packet directory.",
        ),
        note_id: str = typer.Option("ai-review-note", "--note-id", help="Note id."),
        replace_existing: bool = typer.Option(
            False,
            "--replace-existing/--no-replace-existing",
            help="Replace existing note artifacts.",
        ),
    ) -> None:
        settings = get_settings()
        try:
            result = record_ai_review_note(
                packet_path=_resolve_workspace_path(packet, settings.data_dir),
                provider=provider,
                model=model,
                model_reasoning_effort=model_reasoning_effort,
                prompt_hash=prompt_hash,
                findings=finding,
                limitations=limitation,
                recommendation=recommendation,
                disagreements=disagreement,
                out_dir=_resolve_workspace_path(out, settings.data_dir)
                if out is not None
                else None,
                note_id=note_id,
                replace_existing=replace_existing,
            )
        except (
            StrategyAIReviewOutputExistsError,
            StrategyAIReviewError,
            FileNotFoundError,
            ValueError,
            ValidationError,
        ) as exc:
            typer.echo("status=fail")
            typer.echo(f"error={exc}")
            raise typer.Exit(2) from exc

        note = result.note
        typer.echo("status=pass")
        typer.echo(f"note_id={note.note_id}")
        typer.echo(f"recommendation={note.recommendation.value}")
        if note.model_reasoning_effort is not None:
            typer.echo(f"model_reasoning_effort={note.model_reasoning_effort.value}")
        typer.echo(f"auto_applied={str(note.auto_applied).lower()}")
        typer.echo(f"permission_allowed={str(note.permission_allowed).lower()}")
        typer.echo(f"note_path={result.note_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
