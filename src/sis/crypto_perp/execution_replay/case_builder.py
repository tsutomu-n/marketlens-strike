from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, cast

from sis.crypto_perp.decisions import CryptoPerpDecision
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.execution_replay.models import (
    ExecutionReplayCase,
    ReplayArtifactRef,
    ReplayFundingEvent,
    ReplaySide,
)
from sis.crypto_perp.io import file_sha256
from sis.crypto_perp.models import CryptoPerpAction, CryptoPerpProducer, stable_hash
from sis.crypto_perp.recorder import CaptureManifest


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _artifact_ref(path: Path, schema_version: str | None) -> ReplayArtifactRef:
    return ReplayArtifactRef(
        path=path.as_posix(),
        sha256=file_sha256(path),
        schema_version=schema_version,
    )


def load_funding_events(
    path: Path | None,
    *,
    symbol: str,
) -> list[ReplayFundingEvent]:
    if path is None:
        return []
    payloads: list[dict[str, Any]] = []
    if path.suffix.lower() == ".jsonl":
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(
                    f"funding row must be an object: {path}:{line_number}"
                )
            payloads.append(payload)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            payloads = [item for item in payload["rows"] if isinstance(item, dict)]
        elif isinstance(payload, list):
            payloads = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            payloads = [payload]
        else:
            raise ValueError(f"unsupported funding payload: {path}")
    events: list[ReplayFundingEvent] = []
    normalized_symbol = symbol.strip().upper()
    for payload in payloads:
        row_symbol = str(
            payload.get("canonical_symbol") or payload.get("symbol") or ""
        ).upper()
        if row_symbol and row_symbol != normalized_symbol:
            continue
        events.append(
            ReplayFundingEvent(
                funding_event_ts=(
                    payload.get("funding_event_ts") or payload.get("event_ts")
                ),
                funding_rate=payload.get("funding_rate"),
                oracle_price_at_funding=(
                    payload.get("oracle_price_at_funding")
                    or payload.get("oracle_price")
                    or payload.get("mark_price")
                ),
            )
        )
    return sorted(events, key=lambda item: item.funding_event_ts)


def build_execution_replay_case(
    *,
    event_path: Path,
    decision_path: Path,
    capture_manifest_path: Path,
    created_at: datetime | str,
    notional_usd: Decimal,
    holding_minutes: int,
    entry_latency_ms: int,
    exit_latency_ms: int,
    taker_fee_rate: Decimal,
    max_book_wait_ms: int,
    allow_partial_fill: bool,
    funding_events_path: Path | None = None,
) -> ExecutionReplayCase:
    if notional_usd <= 0:
        raise ValueError("notional_usd must be positive")
    if taker_fee_rate <= 0:
        raise ValueError("taker_fee_rate must be positive")
    if holding_minutes <= 0:
        raise ValueError("holding_minutes must be positive")
    if entry_latency_ms < 0 or exit_latency_ms < 0:
        raise ValueError("latency must be non-negative")
    if max_book_wait_ms < 0:
        raise ValueError("max_book_wait_ms must be non-negative")

    event = CryptoPerpEvent.model_validate(_read_json_object(event_path))
    decision = CryptoPerpDecision.model_validate(_read_json_object(decision_path))
    manifest = CaptureManifest.model_validate(
        _read_json_object(capture_manifest_path)
    )
    if decision.event_id != event.event_id:
        raise ValueError("DECISION_EVENT_MISMATCH")
    if decision.source_event_sha256 != file_sha256(event_path):
        raise ValueError("DECISION_SOURCE_EVENT_HASH_MISMATCH")
    if decision.action not in {
        CryptoPerpAction.CONTINUATION_LONG,
        CryptoPerpAction.REVERSAL_SHORT,
    }:
        raise ValueError("DECISION_ACTION_NOT_TRADABLE")
    if decision.size_cap_usd > 0 and notional_usd > decision.size_cap_usd:
        raise ValueError("NOTIONAL_EXCEEDS_DECISION_SIZE_CAP")
    if "books15" not in manifest.channels:
        raise ValueError("CAPTURE_MANIFEST_BOOKS15_REQUIRED")
    if manifest.coverage_status in {"FAILED", "EMPTY"}:
        raise ValueError("CAPTURE_MANIFEST_NOT_USABLE")

    side = cast(
        ReplaySide,
        (
            "LONG"
            if decision.action == CryptoPerpAction.CONTINUATION_LONG
            else "SHORT"
        ),
    )
    entry_arrival = decision.decision_at + timedelta(milliseconds=entry_latency_ms)
    planned_exit = entry_arrival + timedelta(minutes=holding_minutes)
    exit_arrival = planned_exit + timedelta(milliseconds=exit_latency_ms)
    funding_events = load_funding_events(
        funding_events_path,
        symbol=event.native_symbol,
    )
    source_refs = [
        _artifact_ref(event_path, event.schema_version),
        _artifact_ref(decision_path, decision.schema_version),
        _artifact_ref(capture_manifest_path, manifest.schema_version),
    ]
    if funding_events_path is not None:
        source_refs.append(_artifact_ref(funding_events_path, None))
    known_limits = [
        "HISTORICAL_BOOK_REPLAY_DOES_NOT_MODEL_MARKET_IMPACT",
        "DEPTH15_ONLY_NO_LEVELS_BEYOND_CAPTURED_BOOK",
        "TAKER_ONLY",
        "NO_LIQUIDATION_MODEL",
        "NO_QUEUE_MODEL",
        "HOLDING_STARTS_AT_ORDER_ARRIVAL_NOT_CONFIRMED_FILL",
        "INSTRUMENT_PRECISION_AND_MINIMUM_NOT_REPLAYED",
    ]
    if manifest.coverage_status == "GAPPED":
        known_limits.append("CAPTURE_MANIFEST_GAPPED")
    if not funding_events:
        known_limits.append("FUNDING_NOT_REPLAYED")
    case_id = stable_hash(
        [
            "crypto-perp-execution-replay-case",
            event.event_id,
            decision.decision_id,
            file_sha256(capture_manifest_path),
            str(notional_usd),
            holding_minutes,
            entry_latency_ms,
            exit_latency_ms,
            str(taker_fee_rate),
            max_book_wait_ms,
            allow_partial_fill,
            [item.model_dump(mode="json") for item in funding_events],
        ]
    )
    return ExecutionReplayCase(
        case_id=case_id,
        created_at=created_at,
        producer=CryptoPerpProducer(command="crypto-perp-execution-replay"),
        source_refs=source_refs,
        event_id=event.event_id,
        decision_id=decision.decision_id,
        symbol=event.native_symbol,
        side=side,
        decision_at=decision.decision_at,
        entry_arrival_at=entry_arrival,
        planned_exit_at=planned_exit,
        exit_arrival_at=exit_arrival,
        holding_minutes=holding_minutes,
        entry_latency_ms=entry_latency_ms,
        exit_latency_ms=exit_latency_ms,
        notional_usd=notional_usd,
        taker_fee_rate=taker_fee_rate,
        max_book_wait_ms=max_book_wait_ms,
        allow_partial_fill=allow_partial_fill,
        capture_manifest_ref=_artifact_ref(
            capture_manifest_path,
            manifest.schema_version,
        ),
        funding_events=funding_events,
        known_limits=known_limits,
    )
