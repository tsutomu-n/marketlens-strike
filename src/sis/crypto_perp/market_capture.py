from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.io import file_artifact_ref, write_json_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.recorder import CaptureAccumulator, CaptureManifest, CaptureRequest
from sis.crypto_perp.segments import RotatingGzipJsonlWriter
from sis.crypto_perp.ws_protocol import (
    BitgetWsTarget,
    build_subscribe_message,
    parse_bitget_public_message,
)

BITGET_PUBLIC_WS_URL = "wss://ws.bitget.com/v2/ws/public"
OperationalChannel = Literal["books15", "trades"]
MessageSourceFactory = Callable[..., AsyncIterator[str | dict[str, Any]]]
SleepFn = Callable[[float], Awaitable[None]]


class MarketCaptureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    symbols: list[str]
    channels: list[OperationalChannel] = Field(default_factory=lambda: ["books15", "trades"])
    duration_seconds: int = Field(default=1800, gt=0)
    heartbeat_seconds: int = Field(default=30, gt=0)
    pong_timeout_seconds: int = Field(default=10, gt=0)
    reconnect_max_attempts: int = Field(default=5, ge=1)
    reconnect_initial_delay_seconds: float = Field(default=1.0, gt=0)
    reconnect_max_delay_seconds: float = Field(default=30.0, gt=0)
    segment_seconds: int = Field(default=60, gt=0)
    max_rows_per_segment: int = Field(default=10_000, gt=0)
    output_root: Path
    ws_url: str = BITGET_PUBLIC_WS_URL

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip().upper() for item in value if item.strip()))
        if not normalized:
            raise ValueError("at least one symbol is required")
        if len(normalized) > 20:
            raise ValueError("market capture is limited to 20 symbols per process")
        return normalized

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[OperationalChannel]) -> list[OperationalChannel]:
        normalized = list(dict.fromkeys(value))
        if not normalized:
            raise ValueError("at least one channel is required")
        return normalized


class MarketCaptureRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_market_capture_run.v1"] = (
        "crypto_perp_market_capture_run.v1"
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    run_id: str
    started_at: datetime
    ended_at: datetime
    network_attempted: Literal[True] = True
    external_api_called: Literal[True] = True
    ws_url: str
    symbols: list[str]
    channels: list[str]
    duration_seconds: float = Field(ge=0)
    connection_count: int = Field(ge=0)
    subscription_attempts: int = Field(ge=0)
    reconnect_count: int = Field(ge=0)
    heartbeat_sent_count: int = Field(ge=0)
    pong_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    row_count: int = Field(ge=0)
    bytes_written: int = Field(ge=0)
    projected_gzip_bytes_per_day: int | None = Field(default=None, ge=0)
    receive_delay_ms_p50: float | None = Field(default=None, ge=0)
    receive_delay_ms_p90: float | None = Field(default=None, ge=0)
    receive_delay_ms_p99: float | None = Field(default=None, ge=0)
    capture_manifest_paths: list[str]
    run_status: Literal["COMPLETE", "PARTIAL", "FAILED", "EMPTY"]
    reason_codes: list[str]

    @field_validator("created_at", "started_at", "ended_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "started_at", "ended_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


async def _default_message_source_factory(
    *,
    ws_url: str,
    targets: list[BitgetWsTarget],
    heartbeat_seconds: int,
    pong_timeout_seconds: int,
    stop_time_monotonic: float,
    heartbeat_sent_callback: Callable[[], None],
    pong_callback: Callable[[], None],
) -> AsyncIterator[str | dict[str, Any]]:
    """Yield public messages while independently maintaining Bitget string ping/pong."""

    import websockets

    async with websockets.connect(ws_url, ping_interval=None) as connection:
        await connection.send(json.dumps(build_subscribe_message(targets), separators=(",", ":")))
        next_ping_at = time.monotonic() + heartbeat_seconds
        pong_deadline: float | None = None
        while True:
            now = time.monotonic()
            if now >= stop_time_monotonic:
                return
            if pong_deadline is not None and now >= pong_deadline:
                raise ConnectionError("BITGET_WS_PONG_TIMEOUT")
            if now >= next_ping_at:
                await connection.send("ping")
                heartbeat_sent_callback()
                pong_deadline = now + pong_timeout_seconds
                next_ping_at = now + heartbeat_seconds
                continue

            deadlines = [stop_time_monotonic, next_ping_at]
            if pong_deadline is not None:
                deadlines.append(pong_deadline)
            timeout = max(0.001, min(deadlines) - now)
            try:
                raw = await asyncio.wait_for(connection.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                parsed = parse_bitget_public_message(raw)
            except Exception:
                parsed = None
            if parsed is not None and parsed.kind == "pong":
                pong_callback()
                pong_deadline = None
                continue
            yield raw


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def _capture_request(
    *,
    config: MarketCaptureConfig,
    symbol: str,
    run_id: str,
    run_root: Path,
) -> CaptureRequest:
    return CaptureRequest(
        event_id=f"market-capture-{run_id[:16]}-{symbol}",
        provider_id="bitget",
        native_symbol=symbol,
        channels=list(config.channels),
        duration_minutes=max(1, (config.duration_seconds + 59) // 60),
        output_root=run_root / f"symbol={symbol}",
    )


def _received_datetime(recv_ts_ms: int) -> datetime:
    return datetime.fromtimestamp(recv_ts_ms / 1000, tz=timezone.utc)


async def capture_bitget_public_market(
    config: MarketCaptureConfig,
    *,
    message_source_factory: MessageSourceFactory | None = None,
    utc_now: Callable[[], datetime] | None = None,
    wall_clock_ns: Callable[[], int] = time.time_ns,
    monotonic: Callable[[], float] = time.monotonic,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    sleep: SleepFn = asyncio.sleep,
) -> MarketCaptureRun:
    now_fn = utc_now or (lambda: datetime.now(timezone.utc).replace(microsecond=0))
    started_at = ensure_utc_aware("started_at", now_fn())
    started_monotonic = monotonic()
    run_id = stable_hash(
        [
            "crypto-perp-market-capture",
            config.symbols,
            config.channels,
            serialize_utc_z(started_at),
        ]
    )
    run_root = config.output_root / f"run_id={run_id}"
    run_root.mkdir(parents=True, exist_ok=True)
    requests = {
        symbol: _capture_request(
            config=config,
            symbol=symbol,
            run_id=run_id,
            run_root=run_root,
        )
        for symbol in config.symbols
    }
    accumulators = {
        symbol: CaptureAccumulator(request, started_at=started_at)
        for symbol, request in requests.items()
    }
    writers = {
        symbol: RotatingGzipJsonlWriter(
            output_root=request.output_root,
            capture_id=accumulators[symbol].capture_id,
            segment_seconds=config.segment_seconds,
            max_rows_per_segment=config.max_rows_per_segment,
            monotonic_fn=monotonic,
        )
        for symbol, request in requests.items()
    }
    targets = [
        BitgetWsTarget(inst_type="USDT-FUTURES", channel=channel, inst_id=symbol)
        for symbol in config.symbols
        for channel in config.channels
    ]
    source_factory = message_source_factory or _default_message_source_factory
    deadline = started_monotonic + config.duration_seconds
    connection_count = 0
    subscription_attempts = 0
    reconnect_count = 0
    heartbeat_sent_count = 0
    pong_count = 0
    error_count = 0
    reason_codes: list[str] = []
    receive_delays_ms: list[float] = []
    connection_index = 0
    delay = config.reconnect_initial_delay_seconds
    failed = False

    def record_heartbeat() -> None:
        nonlocal heartbeat_sent_count
        heartbeat_sent_count += 1

    def record_pong() -> None:
        nonlocal pong_count
        pong_count += 1

    while monotonic() < deadline:
        connection_index += 1
        connection_count += 1
        subscription_attempts += 1
        connection_id = f"{run_id[:12]}-{connection_index:04d}"
        connection_sequence = 0
        source_ended_early = False
        try:
            async for raw in source_factory(
                ws_url=config.ws_url,
                targets=targets,
                heartbeat_seconds=config.heartbeat_seconds,
                pong_timeout_seconds=config.pong_timeout_seconds,
                stop_time_monotonic=deadline,
                heartbeat_sent_callback=record_heartbeat,
                pong_callback=record_pong,
            ):
                if monotonic() >= deadline:
                    break
                connection_sequence += 1
                recv_ts_ms = wall_clock_ns() // 1_000_000
                received_at = _received_datetime(recv_ts_ms)
                parsed = parse_bitget_public_message(raw)
                if parsed.kind == "pong":
                    pong_count += 1
                    continue
                symbol = (parsed.native_symbol or "").strip().upper()
                accumulator = accumulators.get(symbol)
                writer = writers.get(symbol)
                if accumulator is None or writer is None:
                    if parsed.kind == "subscription":
                        continue
                    reason_codes.append("UNROUTABLE_WS_MESSAGE")
                    if parsed.kind == "error":
                        error_count += 1
                    continue
                row = accumulator.ingest(
                    raw,
                    received_at=received_at,
                    recv_ts_ms=recv_ts_ms,
                    connection_id=connection_id,
                    connection_sequence=connection_sequence,
                    recv_monotonic_ns=monotonic_ns(),
                )
                writer.append(row)
                if parsed.kind == "error":
                    error_count += 1
                    error_code = parsed.error_code or "unknown"
                    error_message = parsed.error_message or ""
                    reason_codes.append(
                        f"BITGET_WS_ERROR:{error_code}:{error_message}"
                    )
                    continue
                if parsed.ts_event_ms is not None:
                    receive_delay_ms = recv_ts_ms - parsed.ts_event_ms
                    if receive_delay_ms >= 0:
                        receive_delays_ms.append(float(receive_delay_ms))
                delay = config.reconnect_initial_delay_seconds
            source_ended_early = monotonic() < deadline
        except Exception as exc:  # pragma: no cover - injected source covers test paths
            error_count += 1
            reason_codes.append(
                f"CAPTURE_CONNECTION_ERROR:{type(exc).__name__}:{exc}"
            )
            source_ended_early = True

        if not source_ended_early or monotonic() >= deadline:
            break
        reconnect_count += 1
        if reconnect_count >= config.reconnect_max_attempts:
            failed = True
            reason_codes.append("CAPTURE_RECONNECT_LIMIT_REACHED")
            break
        reason_codes.append("CAPTURE_SOURCE_ENDED_BEFORE_DEADLINE")
        await sleep(min(delay, config.reconnect_max_delay_seconds))
        delay = min(delay * 2, config.reconnect_max_delay_seconds)

    ended_monotonic = monotonic()
    ended_at = ensure_utc_aware("ended_at", now_fn())
    manifest_paths: list[str] = []
    source_refs: list[dict[str, str]] = []
    total_rows = 0
    total_bytes = 0
    any_gaps = False
    for symbol in config.symbols:
        segments = writers[symbol].close()
        total_rows += accumulators[symbol].row_count
        total_bytes += writers[symbol].bytes_written
        manifest: CaptureManifest = accumulators[symbol].build_manifest(
            ended_at=ended_at,
            segments=segments,
            subscription_attempts=subscription_attempts,
            reconnect_count=reconnect_count,
            failed=failed,
            producer_command="crypto-perp-market-capture",
        )
        any_gaps = any_gaps or manifest.coverage_status in {"GAPPED", "FAILED"}
        manifest_path = run_root / f"symbol={symbol}" / "capture_manifest.json"
        write_json_artifact(manifest_path, manifest.model_dump(mode="json"))
        manifest_paths.append(manifest_path.as_posix())
        source_refs.append(file_artifact_ref(manifest_path, manifest.schema_version))

    actual_duration = max(0.0, ended_monotonic - started_monotonic)
    projected = (
        int(total_bytes / actual_duration * 86_400)
        if actual_duration > 0 and total_bytes > 0
        else None
    )
    if failed:
        run_status: Literal["COMPLETE", "PARTIAL", "FAILED", "EMPTY"] = "FAILED"
    elif total_rows == 0:
        run_status = "EMPTY"
    elif any_gaps or reconnect_count > 0 or error_count > 0:
        run_status = "PARTIAL"
    else:
        run_status = "COMPLETE"
    run = MarketCaptureRun(
        artifact_id=stable_hash(
            [
                "crypto-perp-market-capture-run-artifact",
                run_id,
                source_refs,
                run_status,
            ]
        ),
        created_at=ended_at,
        producer=CryptoPerpProducer(command="crypto-perp-market-capture"),
        source_refs=source_refs,
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        ws_url=config.ws_url,
        symbols=list(config.symbols),
        channels=list(config.channels),
        duration_seconds=actual_duration,
        connection_count=connection_count,
        subscription_attempts=subscription_attempts,
        reconnect_count=reconnect_count,
        heartbeat_sent_count=heartbeat_sent_count,
        pong_count=pong_count,
        error_count=error_count,
        row_count=total_rows,
        bytes_written=total_bytes,
        projected_gzip_bytes_per_day=projected,
        receive_delay_ms_p50=(
            statistics.median(receive_delays_ms) if receive_delays_ms else None
        ),
        receive_delay_ms_p90=_percentile(receive_delays_ms, 0.90),
        receive_delay_ms_p99=_percentile(receive_delays_ms, 0.99),
        capture_manifest_paths=manifest_paths,
        run_status=run_status,
        reason_codes=list(dict.fromkeys(reason_codes)),
    )
    write_json_artifact(run_root / "market_capture_run.json", run.model_dump(mode="json"))
    return run


def run_bitget_public_market_capture(
    config: MarketCaptureConfig,
    *,
    message_source_factory: MessageSourceFactory | None = None,
) -> MarketCaptureRun:
    return asyncio.run(
        capture_bitget_public_market(
            config,
            message_source_factory=message_source_factory,
        )
    )
