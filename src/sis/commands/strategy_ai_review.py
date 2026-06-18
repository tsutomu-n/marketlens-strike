from __future__ import annotations

from pathlib import Path

import typer
from pydantic import ValidationError

from sis.commands.strategy_authoring import _resolve_workspace_path
from sis.settings import get_settings
from sis.strategy_ai_review.models import AIReviewRecommendation
from sis.strategy_ai_review.service import (
    StrategyAIReviewError,
    StrategyAIReviewOutputExistsError,
    build_ai_review_packet,
    record_ai_review_note,
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
        typer.echo(f"sensitive_source_count={packet.sensitive_source_count}")
        typer.echo(f"packet_path={result.packet_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
        if packet.packet_status.value != "READY_FOR_AI_REVIEW":
            raise typer.Exit(2)

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
        typer.echo(f"auto_applied={str(note.auto_applied).lower()}")
        typer.echo(f"permission_allowed={str(note.permission_allowed).lower()}")
        typer.echo(f"note_path={result.note_path.as_posix()}")
        typer.echo(f"report_path={result.report_path.as_posix()}")
