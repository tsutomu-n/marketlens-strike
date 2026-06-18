from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_ai_review.models import AIReviewRecommendation
from sis.strategy_ai_review.service import build_ai_review_packet, record_ai_review_note


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_HASH = "sha256:" + "a" * 64


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / f"schemas/{name}").read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _safe_source(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_cases/ndx-breakout-001/strategy_case_lite.json",
        {
            "schema_version": "strategy_case_lite.v1",
            "strategy_id": "ndx-breakout-001",
            "updated_at": "2026-06-19T01:00:00Z",
            "summary": {
                "latest_status": "READY_FOR_HUMAN_DRIFT_REVIEW",
                "open_actions": ["REVISE_STRATEGY"],
            },
            "wallet_used": False,
            "exchange_write_used": False,
        },
    )


def test_ai_review_packet_uses_safe_summary_not_full_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _safe_source(tmp_path)

    result = build_ai_review_packet(
        source_paths=[source],
        out_dir=tmp_path / "data/strategy_ai_reviews/ndx-breakout-001",
        review_questions=["What should a human inspect next?"],
    )

    assert result.packet.packet_status.value == "READY_FOR_AI_REVIEW"
    assert result.packet.sensitive_source_count == 0
    assert result.packet.permission_allowed is False
    assert result.packet.source_summaries[0].strategy_id == "ndx-breakout-001"
    payload = json.loads(result.packet_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_ai_review_packet.v1.schema.json")).validate(payload)
    serialized = json.dumps(payload, sort_keys=True)
    assert "summary" not in serialized
    assert "open_actions" not in serialized


def test_ai_review_packet_blocks_sensitive_source_without_leaking_value(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _write_json(
        tmp_path / "data/source.json",
        {
            "schema_version": "strategy_case_lite.v1",
            "strategy_id": "ndx-breakout-001",
            "api_secret": "super-secret-value",
        },
    )

    result = build_ai_review_packet(
        source_paths=[source],
        out_dir=tmp_path / "data/strategy_ai_reviews/ndx-breakout-001",
    )

    assert result.packet.packet_status.value == "BLOCKED_SENSITIVE_SOURCE"
    assert result.packet.sensitive_source_count == 1
    serialized = result.packet_path.read_text(encoding="utf-8")
    assert "super-secret-value" not in serialized
    assert "api_secret" not in serialized


def test_ai_review_note_records_hashes_and_no_permission(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    packet = build_ai_review_packet(
        source_paths=[_safe_source(tmp_path)],
        out_dir=tmp_path / "data/strategy_ai_reviews/ndx-breakout-001",
    )

    result = record_ai_review_note(
        packet_path=packet.packet_path,
        provider="openai",
        model="gpt-reviewer",
        prompt_hash=PROMPT_HASH,
        findings=["Return drift should be reviewed by a human."],
        limitations=["AI did not inspect raw market data."],
        recommendation=AIReviewRecommendation.REVISE,
        disagreements=["Gemini note suggested EXTEND_OBSERVATION."],
    )

    assert result.note.input_hash == packet.packet.ai_input_hash
    assert result.note.prompt_hash == PROMPT_HASH
    assert result.note.auto_applied is False
    assert result.note.permission_allowed is False
    payload = json.loads(result.note_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_ai_review_note.v1.schema.json")).validate(payload)
