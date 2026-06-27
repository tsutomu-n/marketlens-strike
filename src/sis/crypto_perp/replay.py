from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)
from sis.crypto_perp.events import CryptoPerpEvent


EXECUTION_REPLAY_SCHEMA_VERSION = "crypto_perp_execution_replay.v1"
REPLAY_SLICE_SCHEMA_VERSION = "crypto_perp_replay_slice.v1"
DEFAULT_REPLAY_NOTIONAL_USD_GRID: tuple[Decimal, ...] = (
    Decimal("5"),
    Decimal("10"),
    Decimal("25"),
    Decimal("50"),
    Decimal("100"),
    Decimal("250"),
)
DEFAULT_REPLAY_LATENCY_SECONDS_GRID: tuple[int, ...] = (5, 15, 30, 60)


class DepthLevel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    price: DecimalValue
    size: DecimalValue

    @field_validator("price", "size")
    @classmethod
    def validate_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("depth price and size must be positive")
        return value

    @field_serializer("price", "size")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class ReplayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    side: Literal["buy", "sell"]
    requested_qty: DecimalValue
    requested_notional_usd: DecimalValue | None = None
    latency_seconds: int = Field(ge=0)

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_validator("requested_qty")
    @classmethod
    def validate_requested_qty(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("requested_qty must be positive")
        return value

    @field_validator("requested_notional_usd")
    @classmethod
    def validate_requested_notional(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("requested_notional_usd must be positive when provided")
        return value

    @field_serializer("requested_qty", "requested_notional_usd")
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


class ExecutionReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_execution_replay.v1"] = EXECUTION_REPLAY_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    replay_id: str
    event_id: str
    side: Literal["buy", "sell"]
    requested_qty: DecimalValue
    requested_notional_usd: DecimalValue | None
    filled_qty: DecimalValue
    unfilled_qty: DecimalValue
    fill_status: Literal["FILLED", "UNFILLABLE"]
    entry_vwap: DecimalValue | None
    entry_book_side: Literal["bid", "ask"]
    latency_seconds: int = Field(ge=0)
    depth_levels_consumed: int = Field(ge=0)
    known_gaps: list[str]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "requested_qty",
        "requested_notional_usd",
        "filled_qty",
        "unfilled_qty",
        "entry_vwap",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


class CryptoPerpReplaySlice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_replay_slice.v1"] = REPLAY_SLICE_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    replay_slice_id: str
    event_id: str
    information_cutoff_at: datetime
    included_sources: list[str]
    known_gaps: list[str]
    row_counts: dict[str, int]
    min_ts: datetime | None = None
    max_ts: datetime | None = None
    summary: dict[str, object]

    @field_validator("created_at", "information_cutoff_at", "min_ts", "max_ts", mode="before")
    @classmethod
    def validate_timestamp(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "information_cutoff_at", "min_ts", "max_ts")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return serialize_utc_z(value)


def _event_source_refs(event: CryptoPerpEvent) -> list[dict[str, str]]:
    return [ref.model_dump(mode="json") for ref in event.source_refs]


def build_replay_slice(
    *,
    event: CryptoPerpEvent,
    created_at: datetime | str,
    included_sources: Sequence[str],
    row_counts: dict[str, int] | None = None,
    min_ts: datetime | str | None = None,
    max_ts: datetime | str | None = None,
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-replay-slice",
) -> CryptoPerpReplaySlice:
    created = ensure_utc_aware("created_at", created_at)
    cutoff = event.information_cutoff_at
    parsed_min = ensure_utc_aware("min_ts", min_ts) if min_ts is not None else None
    parsed_max = ensure_utc_aware("max_ts", max_ts) if max_ts is not None else None
    if parsed_min is not None and parsed_max is not None and parsed_min > parsed_max:
        raise ValueError("min_ts must be less than or equal to max_ts")
    if parsed_max is not None and parsed_max > cutoff:
        raise ValueError("replay slice must not include data after information_cutoff_at")
    counts = dict(row_counts or {})
    for source_id, row_count in counts.items():
        if row_count < 0:
            raise ValueError(f"row_count for {source_id} must be non-negative")
    included = list(dict.fromkeys(source.strip() for source in included_sources if source.strip()))
    if not included:
        raise ValueError("included_sources must not be empty")
    refs = [*_event_source_refs(event), *(dict(ref) for ref in source_refs or [])]
    computed_gaps = list(known_gaps or [])
    for source in included:
        if counts.get(source) == 0:
            computed_gaps.append(f"{source.upper()}_ROW_COUNT_ZERO")
    computed_gaps = list(dict.fromkeys(computed_gaps))
    summary = {
        "event_id": event.event_id,
        "included_source_count": len(included),
        "row_count_total": sum(counts.values()),
        "known_gap_count": len(computed_gaps),
        "future_data_included": False,
    }
    replay_slice_id = stable_hash(
        [
            "crypto-perp-replay-slice",
            event.event_id,
            serialize_utc_z(cutoff),
            included,
            counts,
            serialize_utc_z(parsed_min) if parsed_min is not None else None,
            serialize_utc_z(parsed_max) if parsed_max is not None else None,
            computed_gaps,
        ]
    )
    return CryptoPerpReplaySlice(
        artifact_id=stable_hash(["crypto-perp-replay-slice-artifact", replay_slice_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=refs,
        replay_slice_id=replay_slice_id,
        event_id=event.event_id,
        information_cutoff_at=cutoff,
        included_sources=included,
        known_gaps=computed_gaps,
        row_counts=counts,
        min_ts=parsed_min,
        max_ts=parsed_max,
        summary=summary,
    )


def _ordered_depth(
    side: Literal["buy", "sell"], bids: Sequence[DepthLevel], asks: Sequence[DepthLevel]
) -> list[DepthLevel]:
    if side == "buy":
        return sorted(asks, key=lambda level: level.price)
    return sorted(bids, key=lambda level: level.price, reverse=True)


def _book_side(side: Literal["buy", "sell"]) -> Literal["bid", "ask"]:
    if side == "buy":
        return "ask"
    return "bid"


def _consume_depth(
    *, requested_qty: Decimal, levels: Sequence[DepthLevel]
) -> tuple[Decimal, Decimal | None, int]:
    remaining = requested_qty
    filled = Decimal("0")
    notional = Decimal("0")
    levels_consumed = 0
    for level in levels:
        if remaining <= 0:
            break
        take = min(remaining, level.size)
        if take <= 0:
            continue
        filled += take
        notional += take * level.price
        remaining -= take
        levels_consumed += 1
    if filled == 0:
        return filled, None, levels_consumed
    return filled, notional / filled, levels_consumed


def replay_order(
    request: ReplayOrderRequest,
    *,
    bids: Sequence[DepthLevel],
    asks: Sequence[DepthLevel],
    replayed_at: datetime | str,
    source_refs: Sequence[dict[str, str]] | None = None,
    producer_command: str = "crypto-perp-execution-replay",
) -> ExecutionReplayResult:
    replayed = ensure_utc_aware("replayed_at", replayed_at)
    levels = _ordered_depth(request.side, bids, asks)
    filled_qty, entry_vwap, levels_consumed = _consume_depth(
        requested_qty=request.requested_qty,
        levels=levels,
    )
    unfilled_qty = request.requested_qty - filled_qty
    known_gaps = ["DEPTH_EXHAUSTED"] if unfilled_qty > 0 else []
    fill_status: Literal["FILLED", "UNFILLABLE"] = "FILLED" if unfilled_qty == 0 else "UNFILLABLE"
    replay_id = stable_hash(
        [
            "crypto-perp-execution-replay",
            request.model_dump(mode="json"),
            serialize_utc_z(replayed),
            [level.model_dump(mode="json") for level in levels],
            fill_status,
        ]
    )
    return ExecutionReplayResult(
        artifact_id=stable_hash(["crypto-perp-execution-replay-artifact", replay_id]),
        created_at=replayed,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=list(source_refs or []),
        replay_id=replay_id,
        event_id=request.event_id,
        side=request.side,
        requested_qty=request.requested_qty,
        requested_notional_usd=request.requested_notional_usd,
        filled_qty=filled_qty,
        unfilled_qty=unfilled_qty,
        fill_status=fill_status,
        entry_vwap=entry_vwap,
        entry_book_side=_book_side(request.side),
        latency_seconds=request.latency_seconds,
        depth_levels_consumed=levels_consumed,
        known_gaps=known_gaps,
    )


def build_replay_grid_requests(
    *,
    event_id: str,
    side: Literal["buy", "sell"],
    reference_price: DecimalValue,
    notionals_usd: Sequence[Decimal] = DEFAULT_REPLAY_NOTIONAL_USD_GRID,
    latency_seconds_grid: Sequence[int] = DEFAULT_REPLAY_LATENCY_SECONDS_GRID,
) -> list[ReplayOrderRequest]:
    if reference_price <= 0:
        raise ValueError("reference_price must be positive")
    requests: list[ReplayOrderRequest] = []
    for notional in notionals_usd:
        if notional <= 0:
            raise ValueError("notionals_usd must contain positive values")
        requested_qty = notional / reference_price
        for latency_seconds in latency_seconds_grid:
            requests.append(
                ReplayOrderRequest(
                    event_id=event_id,
                    side=side,
                    requested_qty=requested_qty,
                    requested_notional_usd=notional,
                    latency_seconds=latency_seconds,
                )
            )
    return requests
