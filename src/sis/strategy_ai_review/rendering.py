from __future__ import annotations

from sis.strategy_ai_review.models import (
    StrategyAIReviewNote,
    StrategyAIReviewPacket,
    StrategyAIReviewStructuredFindings,
)


def render_ai_review_packet_markdown(packet: StrategyAIReviewPacket) -> str:
    lines = [
        f"# Strategy AI Review Packet: {packet.packet_id}",
        "",
        f"- packet_status: `{packet.packet_status.value}`",
        f"- source_count: `{len(packet.source_summaries)}`",
        f"- context_section_count: `{len(packet.context_sections)}`",
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
    lines.extend(["", "## Context Sections", ""])
    if packet.context_sections:
        for section in packet.context_sections:
            lines.extend(
                [
                    f"### {section.title}",
                    "",
                    f"- section_type: `{section.section_type}`",
                    f"- source_path: `{section.source_path}`",
                    f"- schema_version: `{section.schema_version}`",
                    "",
                    "| key | value |",
                    "|---|---|",
                ]
            )
            for key, value in section.entries.items():
                lines.append(f"| `{key}` | `{value}` |")
            lines.append("")
    else:
        lines.append("- none")
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
        f"- model_reasoning_effort: `{note.model_reasoning_effort.value if note.model_reasoning_effort is not None else ''}`",
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


def render_ai_review_structured_findings_markdown(
    finding_set: StrategyAIReviewStructuredFindings,
) -> str:
    lines = [
        f"# Strategy AI Review Structured Findings: {finding_set.finding_set_id}",
        "",
        f"- finding_set_status: `{finding_set.finding_set_status.value}`",
        f"- source_note: `{finding_set.source_note.path}`",
        f"- source_packet: `{finding_set.source_packet.path}`",
        f"- finding_count: `{len(finding_set.findings)}`",
        f"- auto_applied: `{str(finding_set.auto_applied).lower()}`",
        f"- permission_allowed: `{str(finding_set.permission_allowed).lower()}`",
        f"- paper_execution_allowed: `{str(finding_set.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(finding_set.live_allowed).lower()}`",
        "",
        "## Findings",
        "",
    ]
    if finding_set.findings:
        for finding in finding_set.findings:
            lines.extend(
                [
                    f"### {finding.finding_id}",
                    "",
                    f"- finding_type: `{finding.finding_type.value}`",
                    f"- severity: `{finding.severity.value}`",
                    f"- review_impact: `{finding.review_impact.value}`",
                    f"- recommended_next_action: `{finding.recommended_next_action.value}`",
                    f"- statement: {finding.statement}",
                    "",
                    "#### Evidence Refs",
                    "",
                ]
            )
            for ref in finding.evidence_refs:
                suffix = f", entry_key={ref.entry_key}" if ref.entry_key is not None else ""
                lines.append(f"- `{ref.ref_type.value}` index={ref.index}{suffix}")
            lines.extend(["", "#### Limitations", ""])
            if finding.limitations:
                lines.extend(f"- {item}" for item in finding.limitations)
            else:
                lines.append("- none")
            lines.append("")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact structures existing AI review notes for human inspection.",
            "- It does not auto-classify raw AI output, auto-apply changes, or permit paper/live execution.",
            "",
        ]
    )
    return "\n".join(lines)
