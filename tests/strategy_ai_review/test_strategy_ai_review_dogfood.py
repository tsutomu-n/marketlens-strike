from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_ai_review.models import AIReviewRecommendation
from sis.strategy_ai_review.service import (
    build_ai_review_packet,
    record_ai_review_note,
    record_structured_findings,
)

from .test_strategy_ai_review import PROMPT_HASH, REPO_ROOT, _safe_source


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / f"schemas/{name}").read_text(encoding="utf-8"))


def test_strategy_ai_review_dogfood_chain_markdown_lineage_and_permissions(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    packet = build_ai_review_packet(
        source_paths=[_safe_source(tmp_path)],
        out_dir=tmp_path / "data/strategy_ai_reviews/pr-ai-dogfood-00",
        packet_id="pr-ai-dogfood-00-packet",
        review_questions=["What should a human inspect next?"],
    )
    note = record_ai_review_note(
        packet_path=packet.packet_path,
        provider="codex-cli",
        model="gpt-5.5",
        model_reasoning_effort="xhigh",
        prompt_hash=PROMPT_HASH,
        findings=[
            "Human should inspect the referenced strategy_case_lite.v1 source artifact.",
            "Human should inspect the open action REVISE_STRATEGY before changing authoring.",
            "The packet is summary-only, so deeper critique needs more allowlisted evidence.",
        ],
        limitations=[
            "AI did not inspect raw market data.",
            "AI did not inspect the full source artifact payload.",
        ],
        recommendation=AIReviewRecommendation.HUMAN_REVIEW_REQUIRED,
        note_id="pr-ai-dogfood-00-note",
    )
    result = record_structured_findings(
        note_path=note.note_path,
        finding_set_id="pr-ai-dogfood-00-structured-findings",
        structured_findings=[
            {
                "finding_id": "inspect-source",
                "finding_type": "SOURCE_ARTIFACT_REVIEW",
                "severity": "MEDIUM",
                "review_impact": "HUMAN_REVIEW_REQUIRED",
                "statement": "Inspect the referenced strategy_case_lite.v1 source artifact.",
                "evidence_refs": [
                    {"ref_type": "note_finding", "index": 0},
                    {"ref_type": "packet_source_summary", "index": 0},
                ],
                "recommended_next_action": "INSPECT_SOURCE_ARTIFACT",
                "limitations": ["AI did not inspect raw market data."],
            },
            {
                "finding_id": "inspect-open-action",
                "finding_type": "OPEN_ACTION_REVIEW",
                "severity": "MEDIUM",
                "review_impact": "HUMAN_REVIEW_REQUIRED",
                "statement": "Review open action REVISE_STRATEGY against underlying evidence.",
                "evidence_refs": [
                    {"ref_type": "note_finding", "index": 1},
                    {"ref_type": "packet_context_entry", "index": 0, "entry_key": "open_actions"},
                ],
                "recommended_next_action": "INSPECT_DRIFT_EVIDENCE",
                "limitations": ["AI did not inspect the full source artifact payload."],
            },
        ],
    )

    payload = json.loads(result.finding_set_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_ai_review_structured_findings.v1.schema.json")).validate(
        payload
    )
    assert payload["auto_applied"] is False
    assert payload["permission_allowed"] is False
    assert payload["paper_execution_allowed"] is False
    assert payload["live_allowed"] is False
    assert payload["source_note"]["input_hash"] == payload["source_packet"]["ai_input_hash"]
    assert payload["findings"][1]["evidence_refs"][1] == {
        "ref_type": "packet_context_entry",
        "index": 0,
        "entry_key": "open_actions",
    }

    markdown = result.report_path.read_text(encoding="utf-8")
    assert "# Strategy AI Review Structured Findings" in markdown
    assert "finding_count: `2`" in markdown
    assert "source_note:" in markdown
    assert "source_packet:" in markdown
    assert "#### Evidence Refs" in markdown
    assert "`packet_context_entry` index=0, entry_key=open_actions" in markdown
    assert (
        "It does not auto-classify raw AI output, auto-apply changes, or permit paper/live execution."
        in markdown
    )
