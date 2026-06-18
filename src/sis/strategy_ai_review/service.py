from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_ai_review.models import (
    AIReviewPacketReference,
    AIReviewPacketStatus,
    AIReviewRecommendation,
    AIReviewSourceSummary,
    StrategyAIReviewNote,
    StrategyAIReviewPacket,
)
from sis.strategy_ai_review.rendering import (
    render_ai_review_note_markdown,
    render_ai_review_packet_markdown,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import detect_json_schema_version, repo_relative_path
from sis.strategy_stage.models import StageProducer


SENSITIVE_KEY_FRAGMENTS = (
    "secret",
    "credential",
    "private_key",
    "api_key",
    "account",
)

SAFE_FALSE_BOUNDARY_KEYS = {
    "wallet_used",
    "exchange_write_used",
    "signing_used",
    "credentials_used",
}


@dataclass(frozen=True)
class AIReviewPacketResult:
    packet: StrategyAIReviewPacket
    packet_path: Path
    report_path: Path


@dataclass(frozen=True)
class AIReviewNoteResult:
    note: StrategyAIReviewNote
    note_path: Path
    report_path: Path


class StrategyAIReviewError(ValueError):
    pass


class StrategyAIReviewOutputExistsError(StrategyAIReviewError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _hash_payload(payload: object) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_sensitive_key(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in SAFE_FALSE_BOUNDARY_KEYS and value is False:
                continue
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                return True
            if lowered in {"wallet_used", "exchange_write_used"} and value is not False:
                return True
            if _has_sensitive_key(value):
                return True
    elif isinstance(payload, list):
        return any(_has_sensitive_key(item) for item in payload)
    return False


def _source_summary(path: Path, payload: dict[str, Any]) -> AIReviewSourceSummary:
    return AIReviewSourceSummary(
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
        strategy_id=_first_string(payload, ("strategy_id", "case_id", "review_id")),
        status=_first_string(
            payload,
            (
                "decision",
                "review_status",
                "ingest_status",
                "request_status",
                "handoff_status",
                "packet_status",
            ),
        ),
        action=_first_string(payload, ("recommended_action", "next_action", "request_status")),
    )


def _packet_status(source_count: int, sensitive_count: int) -> AIReviewPacketStatus:
    if source_count == 0:
        return AIReviewPacketStatus.NO_SOURCES
    if sensitive_count:
        return AIReviewPacketStatus.BLOCKED_SENSITIVE_SOURCE
    return AIReviewPacketStatus.READY_FOR_AI_REVIEW


def build_ai_review_packet(
    *,
    source_paths: list[Path],
    out_dir: Path,
    packet_id: str = "ai-review-packet",
    review_questions: list[str] | None = None,
    replace_existing: bool = False,
    generated_at: datetime | None = None,
) -> AIReviewPacketResult:
    missing = [path for path in source_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"source artifact missing: {missing[0]}")

    summaries: list[AIReviewSourceSummary] = []
    sensitive_count = 0
    for path in source_paths:
        payload = read_json_object(path)
        if _has_sensitive_key(payload):
            sensitive_count += 1
        summaries.append(_source_summary(path, payload))

    ai_input_hash = _hash_payload(
        {
            "source_summaries": [summary.model_dump(mode="json") for summary in summaries],
            "review_questions": review_questions or [],
        }
    )
    packet = StrategyAIReviewPacket(
        packet_id=packet_id,
        generated_at=generated_at or _utc_now(),
        producer=StageProducer(command="strategy-ai-review-packet-build"),
        packet_status=_packet_status(len(summaries), sensitive_count),
        source_summaries=summaries,
        sensitive_source_count=sensitive_count,
        review_questions=review_questions or [],
        ai_input_hash=ai_input_hash,
    )

    packet_path = out_dir / "strategy_ai_review_packet.json"
    report_path = out_dir / "strategy_ai_review_packet.md"
    if not replace_existing and (packet_path.exists() or report_path.exists()):
        raise StrategyAIReviewOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(packet_path, packet.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_ai_review_packet_markdown(packet))
    return AIReviewPacketResult(packet=packet, packet_path=packet_path, report_path=report_path)


def record_ai_review_note(
    *,
    packet_path: Path,
    provider: str,
    model: str,
    prompt_hash: str,
    findings: list[str],
    limitations: list[str],
    recommendation: AIReviewRecommendation,
    out_dir: Path | None = None,
    note_id: str = "ai-review-note",
    disagreements: list[str] | None = None,
    replace_existing: bool = False,
    recorded_at: datetime | None = None,
) -> AIReviewNoteResult:
    payload = read_json_object(packet_path)
    packet = StrategyAIReviewPacket.model_validate(payload)
    selected_out = out_dir or packet_path.parent
    note = StrategyAIReviewNote(
        note_id=note_id,
        recorded_at=recorded_at or _utc_now(),
        producer=StageProducer(command="strategy-ai-review-note-record"),
        source_packet=AIReviewPacketReference(
            path=repo_relative_path(packet_path),
            sha256=sha256_file(packet_path),
            ai_input_hash=packet.ai_input_hash,
        ),
        provider=provider,
        model=model,
        prompt_hash=prompt_hash,
        input_hash=packet.ai_input_hash,
        limitations=limitations,
        findings=findings,
        recommendation=recommendation,
        disagreements=disagreements or [],
    )
    note_path = selected_out / "strategy_ai_review_note.json"
    report_path = selected_out / "strategy_ai_review_note.md"
    if not replace_existing and (note_path.exists() or report_path.exists()):
        raise StrategyAIReviewOutputExistsError(
            f"output already exists: {repo_relative_path(selected_out)}"
        )
    write_json_artifact(note_path, note.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_ai_review_note_markdown(note))
    return AIReviewNoteResult(note=note, note_path=note_path, report_path=report_path)
