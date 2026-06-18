from __future__ import annotations

from sis.strategy_ai_review.models import StrategyAIReviewNote, StrategyAIReviewPacket


def render_ai_review_packet_markdown(packet: StrategyAIReviewPacket) -> str:
    lines = [
        f"# Strategy AI Review Packet: {packet.packet_id}",
        "",
        f"- packet_status: `{packet.packet_status.value}`",
        f"- source_count: `{len(packet.source_summaries)}`",
        f"- sensitive_source_count: `{packet.sensitive_source_count}`",
        f"- ai_input_hash: `{packet.ai_input_hash}`",
        f"- permission_allowed: `{str(packet.permission_allowed).lower()}`",
        "",
        "## Review Questions",
        "",
    ]
    lines.extend(
        f"- {question}" for question in packet.review_questions
    ) if packet.review_questions else lines.append("- none")
    lines.extend(
        [
            "",
            "## Source Summaries",
            "",
            "| path | schema_version | strategy_id | status | action | sha256 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for source in packet.source_summaries:
        lines.append(
            f"| `{source.path}` | `{source.schema_version or ''}` | `{source.strategy_id or ''}` | `{source.status or ''}` | `{source.action or ''}` | `{source.sha256}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This packet contains source summaries only, not full artifact payloads.",
            "- It does not permit paper execution, live execution, wallet use, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)


def render_ai_review_note_markdown(note: StrategyAIReviewNote) -> str:
    lines = [
        f"# Strategy AI Review Note: {note.note_id}",
        "",
        f"- provider: `{note.provider}`",
        f"- model: `{note.model}`",
        f"- recommendation: `{note.recommendation.value}`",
        f"- prompt_hash: `{note.prompt_hash}`",
        f"- input_hash: `{note.input_hash}`",
        f"- auto_applied: `{str(note.auto_applied).lower()}`",
        f"- permission_allowed: `{str(note.permission_allowed).lower()}`",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in note.limitations)
    lines.extend(["", "## Findings", ""])
    lines.extend(f"- {item}" for item in note.findings)
    lines.extend(["", "## Disagreements", ""])
    lines.extend(
        f"- {item}" for item in note.disagreements
    ) if note.disagreements else lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This note records AI output for human review only.",
            "- It does not auto-apply changes or permit paper/live execution.",
            "",
        ]
    )
    return "\n".join(lines)
