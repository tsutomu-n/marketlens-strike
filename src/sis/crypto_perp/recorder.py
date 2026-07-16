from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.book import BitgetOrderBook
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.segments import CaptureSegmentRef, write_gzip_jsonl_segment
from sis.crypto_perp.ws_protocol import (
    BitgetWsTarget,
    InternalWsChannel,
    build_subscribe_message,
    parse_bitget_public_message,
)

CAPTURE_MANIFEST_SCHEMA_VERSION = "crypto_perp_capture_manifest.v1"
RAW_WS_ROW_SCHEMA_VERSION = "crypto_perp_ws_raw_message.v1"


class CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    event_id: str
    provider_id: Literal["bitget"]
    native_symbol: str
    channels: list[InternalWsChannel]
    duration_minutes: int
    output_root: Path
    max_concurrent_captures: int = 5

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("event_id must not be empty")
        return value

    @field_validator("native_symbol")
    @classmethod
    def validate_native_symbol(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped or stripped == "*":
            raise ValueError("capture requires a candidate symbol")
        return stripped

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("duration_minutes must be positive")
        return value

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[InternalWsChannel]) -> list[InternalWsChannel]:
        if not value:
            raise ValueError("channels must not be empty")
        return list(dict.fromkeys(value))


class CaptureSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    schema_version: str


class KnownCaptureGap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: str
    native_symbol: str
    reason_code: str
    ts_event: str | None = None
    seq: int | None = None


class CaptureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_capture_manifest.v1"] = (
        CAPTURE_MANIFEST_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[CaptureSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    capture_id: str
    event_id: str
    backend: Literal["native", "pybotters"]
    started_at: datetime
    ended_at: datetime
    channels: list[str]
    segments: list[CaptureSegmentRef]
    row_count: int
    subscription_attempts: int
    reconnect_count: int
    sequence_gap_count: int
    checksum_failure_count: int
    resync_count: int
    coverage_status: Literal["COMPLETE", "GAPPED", "EMPTY", "FAILED"]
    known_gaps: list[KnownCaptureGap]

    @field_validator("created_at", "started_at", "ended_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "started_at", "ended_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _utc_from_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return serialize_utc_z(datetime.fromtimestamp(value / 1000, tz=timezone.utc))


def _raw_row(
    *,
    request: CaptureRequest,
    channel: str | None,
    ts_event: str | None,
    ts_received: str,
    raw_payload: dict[str, Any],
    recv_ts_ms: int | None = None,
    connection_id: str | None = None,
    connection_sequence: int | None = None,
    recv_monotonic_ns: int | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": RAW_WS_ROW_SCHEMA_VERSION,
        "event_id": request.event_id,
        "provider_id": request.provider_id,
        "native_symbol": request.native_symbol,
        "channel": channel or "unknown",
        "ts_event": ts_event,
        "ts_received": ts_received,
        "raw_payload": raw_payload,
    }
    if recv_ts_ms is not None:
        row["recv_ts_ms"] = recv_ts_ms
    if connection_id is not None:
        row["connection_id"] = connection_id
    if connection_sequence is not None:
        row["connection_sequence"] = connection_sequence
    if recv_monotonic_ns is not None:
        row["recv_monotonic_ns"] = recv_monotonic_ns
    return row


def _depth_rows(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    rows: list[list[str]] = []
    for item in value:
        if isinstance(item, list) and len(item) >= 2:
            rows.append([str(item[0]), str(item[1])])
    return rows


def _book_key(channel: str | None, native_symbol: str) -> tuple[str, str]:
    return channel or "unknown", native_symbol


def _capture_id(request: CaptureRequest, started_at: datetime) -> str:
    return stable_hash(
        [
            "crypto-perp-capture",
            request.event_id,
            request.native_symbol,
            request.channels,
            serialize_utc_z(started_at),
        ]
    )


class CaptureAccumulator:
    """Shared parse and quality state for fixture and operational public capture."""

    def __init__(self, request: CaptureRequest, *, started_at: datetime | str) -> None:
        self.request = request
        self.started_at = ensure_utc_aware("started_at", started_at)
        self.capture_id = _capture_id(request, self.started_at)
        self.books: dict[tuple[str, str], BitgetOrderBook] = {}
        self.known_gaps: list[KnownCaptureGap] = []
        self.row_count = 0
        self.sequence_gap_count = 0
        self.checksum_failure_count = 0
        self.resync_count = 0
        self._invalid_book_keys: set[tuple[str, str]] = set()

    def ingest(
        self,
        raw: dict[str, Any] | str,
        *,
        received_at: datetime | str,
        recv_ts_ms: int | None = None,
        connection_id: str | None = None,
        connection_sequence: int | None = None,
        recv_monotonic_ns: int | None = None,
    ) -> dict[str, Any]:
        received = ensure_utc_aware("received_at", received_at)
        parsed = parse_bitget_public_message(raw)
        ts_event = _utc_from_ms(parsed.ts_event_ms)
        resolved_recv_ts_ms = (
            recv_ts_ms
            if recv_ts_ms is not None
            else int(received.timestamp() * 1000)
        )
        row = _raw_row(
            request=self.request,
            channel=parsed.channel,
            ts_event=ts_event,
            ts_received=serialize_utc_z(received),
            raw_payload=parsed.raw,
            recv_ts_ms=resolved_recv_ts_ms,
            connection_id=connection_id,
            connection_sequence=connection_sequence,
            recv_monotonic_ns=recv_monotonic_ns,
        )
        self.row_count += 1
        if parsed.kind != "data" or parsed.channel not in {"books", "books1", "books15"}:
            return row

        key = _book_key(
            parsed.channel,
            parsed.native_symbol or self.request.native_symbol,
        )
        book = self.books.setdefault(
            key,
            BitgetOrderBook(native_symbol=key[1], channel=key[0]),
        )
        for item in parsed.data:
            seq_value = item.get("seq")
            seq = int(seq_value) if seq_value is not None else 0
            checksum_value = item.get("checksum")
            checksum = int(checksum_value) if checksum_value is not None else None
            item_ts_value = item.get("ts")
            item_ts_ms = int(item_ts_value) if str(item_ts_value or "").isdigit() else 0
            result = book.apply_depth(
                action=parsed.action or "snapshot",
                bids=_depth_rows(item.get("bids")),
                asks=_depth_rows(item.get("asks")),
                seq=seq,
                checksum=checksum,
                ts_event_ms=item_ts_ms or parsed.ts_event_ms or 0,
            )
            if result.invalid_reason == "SEQUENCE_GAP":
                self.sequence_gap_count += 1
            if result.invalid_reason == "CHECKSUM_FAILURE":
                self.checksum_failure_count += 1
            if result.invalid_reason is not None:
                self._invalid_book_keys.add(key)
                self.known_gaps.append(
                    KnownCaptureGap(
                        channel=parsed.channel or "unknown",
                        native_symbol=(
                            parsed.native_symbol or self.request.native_symbol
                        ),
                        reason_code=result.invalid_reason,
                        ts_event=_utc_from_ms(item_ts_ms or parsed.ts_event_ms),
                        seq=seq,
                    )
                )
            elif key in self._invalid_book_keys:
                self._invalid_book_keys.remove(key)
                self.resync_count += 1
        return row

    def build_manifest(
        self,
        *,
        ended_at: datetime | str,
        segments: Sequence[CaptureSegmentRef],
        subscription_attempts: int,
        reconnect_count: int,
        failed: bool = False,
        producer_command: str = "crypto-perp-capture",
    ) -> CaptureManifest:
        ended = ensure_utc_aware("ended_at", ended_at)
        if failed:
            coverage_status: Literal["COMPLETE", "GAPPED", "EMPTY", "FAILED"] = (
                "FAILED"
            )
        elif self.row_count == 0:
            coverage_status = "EMPTY"
        elif self.known_gaps:
            coverage_status = "GAPPED"
        else:
            coverage_status = "COMPLETE"
        return CaptureManifest(
            artifact_id=stable_hash(
                [
                    "crypto-perp-capture-manifest-artifact",
                    self.capture_id,
                    [segment.model_dump(mode="json") for segment in segments],
                    coverage_status,
                ]
            ),
            created_at=ended,
            producer=CryptoPerpProducer(command=producer_command),
            source_refs=[],
            capture_id=self.capture_id,
            event_id=self.request.event_id,
            backend="native",
            started_at=self.started_at,
            ended_at=ended,
            channels=list(self.request.channels),
            segments=list(segments),
            row_count=self.row_count,
            subscription_attempts=subscription_attempts,
            reconnect_count=reconnect_count,
            sequence_gap_count=self.sequence_gap_count,
            checksum_failure_count=self.checksum_failure_count,
            resync_count=self.resync_count,
            coverage_status=coverage_status,
            known_gaps=list(self.known_gaps),
        )


def run_candidate_capture(
    request: CaptureRequest,
    *,
    raw_messages: Sequence[dict[str, Any] | str],
    received_at: datetime | str | None = None,
) -> CaptureManifest:
    received = ensure_utc_aware(
        "received_at",
        received_at or datetime.now(timezone.utc).replace(microsecond=0),
    )
    targets = [
        BitgetWsTarget(
            inst_type="USDT-FUTURES",
            channel=channel,
            inst_id=request.native_symbol,
        )
        for channel in request.channels
    ]
    _ = build_subscribe_message(targets)
    accumulator = CaptureAccumulator(request, started_at=received)
    rows = [accumulator.ingest(raw, received_at=received) for raw in raw_messages]
    segment_refs: list[CaptureSegmentRef] = []
    if rows:
        segment_refs.append(
            write_gzip_jsonl_segment(
                request.output_root
                / f"event_id={request.event_id}"
                / "part-000001.jsonl.gz",
                rows,
            )
        )
    return accumulator.build_manifest(
        ended_at=received,
        segments=segment_refs,
        subscription_attempts=1 if request.channels else 0,
        reconnect_count=0,
    )
