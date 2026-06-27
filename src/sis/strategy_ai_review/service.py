from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_ai_review.models import (
    AIReviewEvidenceRef,
    AIReviewEvidenceRefType,
    AIReviewContextEntryValue,
    AIReviewContextSection,
    AIReviewModelReasoningEffort,
    AIReviewPacketReference,
    AIReviewPacketStatus,
    AIReviewRecommendation,
    AIReviewSourceNoteReference,
    AIReviewSourceSummary,
    AIReviewStructuredFinding,
    StrategyAIReviewNote,
    StrategyAIReviewPacket,
    StrategyAIReviewStructuredFindings,
)
from sis.strategy_ai_review.rendering import (
    render_ai_review_note_markdown,
    render_ai_review_packet_markdown,
    render_ai_review_structured_findings_markdown,
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

STRATEGY_CASE_LITE_SCHEMA_VERSION = "strategy_case_lite.v1"


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


@dataclass(frozen=True)
class AIReviewStructuredFindingsResult:
    finding_set: StrategyAIReviewStructuredFindings
    finding_set_path: Path
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


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    return None


def _optional_string_list(payload: dict[str, Any], key: str) -> list[str] | None:
    value = payload.get(key)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def _strategy_case_lite_context(
    path: Path, payload: dict[str, Any]
) -> AIReviewContextSection | None:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return None

    entries: dict[str, AIReviewContextEntryValue] = {}
    for key in ("strategy_id", "case_id", "updated_at"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            entries[key] = value.strip()

    for key in ("artifact_count", "timeline_count"):
        value = _optional_int(summary, key)
        if value is not None:
            entries[key] = value

    latest_status = summary.get("latest_status")
    if latest_status is None or isinstance(latest_status, str):
        entries["latest_status"] = latest_status.strip() if isinstance(latest_status, str) else None

    for key in ("open_actions", "blocked_reasons"):
        value = _optional_string_list(summary, key)
        if value is not None:
            entries[key] = value

    if not entries:
        return None

    return AIReviewContextSection(
        section_type="strategy_case_lite_summary",
        title="Strategy Case Lite Summary",
        source_path=repo_relative_path(path),
        schema_version=STRATEGY_CASE_LITE_SCHEMA_VERSION,
        entries=entries,
    )


def _context_sections_for_source(
    path: Path, payload: dict[str, Any]
) -> list[AIReviewContextSection]:
    if payload.get("schema_version") != STRATEGY_CASE_LITE_SCHEMA_VERSION:
        return []
    section = _strategy_case_lite_context(path, payload)
    return [section] if section is not None else []


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
    context_sections: list[AIReviewContextSection] = []
    sensitive_count = 0
    for path in source_paths:
        payload = read_json_object(path)
        has_sensitive_key = _has_sensitive_key(payload)
        if has_sensitive_key:
            sensitive_count += 1
        else:
            context_sections.extend(_context_sections_for_source(path, payload))
        summaries.append(_source_summary(path, payload))

    ai_input_hash = _hash_payload(
        {
            "source_summaries": [summary.model_dump(mode="json") for summary in summaries],
            "context_sections": [section.model_dump(mode="json") for section in context_sections],
            "review_questions": review_questions or [],
        }
    )
    packet = StrategyAIReviewPacket(
        packet_id=packet_id,
        generated_at=generated_at or _utc_now(),
        producer=StageProducer(command="strategy-ai-review-packet-build"),
        packet_status=_packet_status(len(summaries), sensitive_count),
        source_summaries=summaries,
        context_sections=context_sections,
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
    model_reasoning_effort: AIReviewModelReasoningEffort | None = None,
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
        model_reasoning_effort=model_reasoning_effort,
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


def _packet_path_from_note(note_path: Path, note: StrategyAIReviewNote) -> Path:
    path = Path(note.source_packet.path)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path
    return note_path.parent / path


def _load_note_and_packet(
    note_path: Path,
) -> tuple[StrategyAIReviewNote, str, Path, StrategyAIReviewPacket, str]:
    note = StrategyAIReviewNote.model_validate(read_json_object(note_path))
    note_sha256 = sha256_file(note_path)
    packet_path = _packet_path_from_note(note_path, note)
    if not packet_path.exists():
        raise FileNotFoundError(f"source packet missing: {packet_path}")
    packet_sha256 = sha256_file(packet_path)
    if packet_sha256 != note.source_packet.sha256:
        raise StrategyAIReviewError("packet sha256 mismatch")
    packet = StrategyAIReviewPacket.model_validate(read_json_object(packet_path))
    if note.input_hash != packet.ai_input_hash:
        raise StrategyAIReviewError("note input_hash does not match packet ai_input_hash")
    return note, note_sha256, packet_path, packet, packet_sha256


def _validate_evidence_ref(
    ref: AIReviewEvidenceRef,
    *,
    note: StrategyAIReviewNote,
    packet: StrategyAIReviewPacket,
) -> None:
    if ref.ref_type == AIReviewEvidenceRefType.NOTE_FINDING:
        if ref.entry_key is not None:
            raise StrategyAIReviewError("entry_key must be omitted for note_finding")
        if ref.index >= len(note.findings):
            raise StrategyAIReviewError("note_finding index out of range")
        return
    if ref.ref_type == AIReviewEvidenceRefType.NOTE_LIMITATION:
        if ref.entry_key is not None:
            raise StrategyAIReviewError("entry_key must be omitted for note_limitation")
        if ref.index >= len(note.limitations):
            raise StrategyAIReviewError("note_limitation index out of range")
        return
    if ref.ref_type == AIReviewEvidenceRefType.PACKET_SOURCE_SUMMARY:
        if ref.entry_key is not None:
            raise StrategyAIReviewError("entry_key must be omitted for packet_source_summary")
        if ref.index >= len(packet.source_summaries):
            raise StrategyAIReviewError("packet_source_summary index out of range")
        return
    if ref.ref_type == AIReviewEvidenceRefType.PACKET_CONTEXT_SECTION:
        if ref.entry_key is not None:
            raise StrategyAIReviewError("entry_key must be omitted for packet_context_section")
        if ref.index >= len(packet.context_sections):
            raise StrategyAIReviewError("packet_context_section index out of range")
        return
    if ref.ref_type == AIReviewEvidenceRefType.PACKET_CONTEXT_ENTRY:
        if ref.index >= len(packet.context_sections):
            raise StrategyAIReviewError("packet_context_entry index out of range")
        if ref.entry_key is None:
            raise StrategyAIReviewError("entry_key is required for packet_context_entry")
        if ref.entry_key not in packet.context_sections[ref.index].entries:
            raise StrategyAIReviewError("entry_key not found in packet context section")
        return
    raise StrategyAIReviewError(f"unsupported evidence ref_type: {ref.ref_type}")


def _structured_finding(
    payload: dict[str, Any],
    *,
    index: int,
    note: StrategyAIReviewNote,
    packet: StrategyAIReviewPacket,
) -> AIReviewStructuredFinding:
    normalized = dict(payload)
    normalized.setdefault("finding_id", f"finding-{index:03d}")
    finding = AIReviewStructuredFinding.model_validate(normalized)
    for ref in finding.evidence_refs:
        _validate_evidence_ref(ref, note=note, packet=packet)
    return finding


def record_structured_findings(
    *,
    note_path: Path,
    structured_findings: list[dict[str, Any]],
    out_dir: Path | None = None,
    finding_set_id: str = "ai-review-structured-findings",
    replace_existing: bool = False,
    recorded_at: datetime | None = None,
) -> AIReviewStructuredFindingsResult:
    note, note_sha256, packet_path, packet, packet_sha256 = _load_note_and_packet(note_path)
    selected_out = out_dir or note_path.parent
    findings = [
        _structured_finding(payload, index=index, note=note, packet=packet)
        for index, payload in enumerate(structured_findings, start=1)
    ]
    finding_set = StrategyAIReviewStructuredFindings(
        finding_set_id=finding_set_id,
        recorded_at=recorded_at or _utc_now(),
        producer=StageProducer(command="strategy-ai-review-findings-structure"),
        source_note=AIReviewSourceNoteReference(
            path=repo_relative_path(note_path),
            sha256=note_sha256,
            input_hash=note.input_hash,
            prompt_hash=note.prompt_hash,
            provider=note.provider,
            model=note.model,
            model_reasoning_effort=note.model_reasoning_effort,
            recommendation=note.recommendation,
        ),
        source_packet=AIReviewPacketReference(
            path=repo_relative_path(packet_path),
            sha256=packet_sha256,
            ai_input_hash=packet.ai_input_hash,
        ),
        findings=findings,
    )
    finding_set_path = selected_out / "strategy_ai_review_structured_findings.json"
    report_path = selected_out / "strategy_ai_review_structured_findings.md"
    if not replace_existing and (finding_set_path.exists() or report_path.exists()):
        raise StrategyAIReviewOutputExistsError(
            f"output already exists: {repo_relative_path(selected_out)}"
        )
    write_json_artifact(finding_set_path, finding_set.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_ai_review_structured_findings_markdown(finding_set))
    return AIReviewStructuredFindingsResult(
        finding_set=finding_set,
        finding_set_path=finding_set_path,
        report_path=report_path,
    )
