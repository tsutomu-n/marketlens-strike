from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.strategy_ai_review.models import AIReviewRecommendation
from sis.strategy_ai_review.service import (
    StrategyAIReviewError,
    build_ai_review_packet,
    record_ai_review_note,
    record_structured_findings,
)

from .test_strategy_ai_review import PROMPT_HASH, REPO_ROOT, _safe_source


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / f"schemas/{name}").read_text(encoding="utf-8"))


def _note_path(tmp_path: Path) -> Path:
    packet = build_ai_review_packet(
        source_paths=[_safe_source(tmp_path)],
        out_dir=tmp_path / "data/strategy_ai_reviews/ndx-breakout-001",
    )
    note = record_ai_review_note(
        packet_path=packet.packet_path,
        provider="codex-cli",
        model="gpt-5.5",
        prompt_hash=PROMPT_HASH,
        findings=[
            "Human should inspect the referenced strategy_case_lite.v1 source artifact.",
            "Human should inspect the open action REVISE_STRATEGY.",
        ],
        limitations=["AI did not inspect raw market data."],
        recommendation=AIReviewRecommendation.HUMAN_REVIEW_REQUIRED,
    )
    return note.note_path


def _structured_input() -> list[dict]:
    return [
        {
            "finding_type": "SOURCE_ARTIFACT_REVIEW",
            "severity": "MEDIUM",
            "review_impact": "HUMAN_REVIEW_REQUIRED",
            "statement": "Inspect the referenced strategy_case_lite.v1 source artifact.",
            "evidence_refs": [
                {"ref_type": "note_finding", "index": 0},
                {"ref_type": "packet_context_entry", "index": 0, "entry_key": "open_actions"},
            ],
            "recommended_next_action": "INSPECT_SOURCE_ARTIFACT",
            "limitations": ["AI did not inspect raw market data."],
        }
    ]


def test_structured_findings_record_typed_refs_and_lineage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = record_structured_findings(
        note_path=_note_path(tmp_path),
        structured_findings=_structured_input(),
    )

    assert result.finding_set.finding_set_status == "RECORDED"
    assert result.finding_set.findings[0].finding_id == "finding-001"
    assert result.finding_set.findings[0].severity == "MEDIUM"
    assert result.finding_set.findings[0].review_impact == "HUMAN_REVIEW_REQUIRED"
    assert result.finding_set.source_note.provider == "codex-cli"
    assert result.finding_set.source_note.model == "gpt-5.5"
    assert result.finding_set.auto_applied is False
    assert result.finding_set.permission_allowed is False
    payload = json.loads(result.finding_set_path.read_text(encoding="utf-8"))
    assert "model_reasoning_effort" not in payload["source_note"]
    Draft202012Validator(_schema("strategy_ai_review_structured_findings.v1.schema.json")).validate(
        payload
    )
    serialized = json.dumps(payload, sort_keys=True)
    assert "source_artifacts" not in serialized
    assert '"timeline":' not in serialized
    assert "latest_source_hashes" not in serialized


def test_structured_findings_reject_invalid_evidence_ref(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    findings = _structured_input()
    findings[0]["evidence_refs"] = [{"ref_type": "packet_context_entry", "index": 0}]

    with pytest.raises(StrategyAIReviewError, match="entry_key"):
        record_structured_findings(
            note_path=_note_path(tmp_path),
            structured_findings=findings,
        )


def test_structured_findings_reject_stale_packet_lineage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    note_path = _note_path(tmp_path)
    note_payload = json.loads(note_path.read_text(encoding="utf-8"))
    packet_path = tmp_path / note_payload["source_packet"]["path"]
    packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_payload["ai_input_hash"] = "sha256:" + "f" * 64
    packet_path.write_text(json.dumps(packet_payload), encoding="utf-8")

    with pytest.raises(StrategyAIReviewError, match="packet sha256 mismatch"):
        record_structured_findings(
            note_path=note_path,
            structured_findings=_structured_input(),
        )
