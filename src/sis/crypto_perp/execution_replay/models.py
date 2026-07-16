from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
)

ReplaySide = Literal["LONG", "SHORT"]
FillStatus = Literal["FILLED", "PARTIAL", "UNFILLABLE"]
ReplayStatus = Literal[
    "COMPLETE",
    "PARTIAL",
    "UNFILLABLE",
    "STALE_BOOK",
    "DATA_GAP",
    "INVALID_INPUT",
]
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def _serialize_decimal(value: Decimal | None) -> str | None:
    return None if value is None else decimal_to_json_string(value)


class ReplayArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact path must not be empty")
        return stripped

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("sha256 must be a lowercase SHA-256 digest")
        return normalized


class ReplayFundingEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    funding_event_ts: datetime
    funding_rate: DecimalValue
    oracle_price_at_funding: DecimalValue = Field(gt=0)

    @field_validator("funding_event_ts", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("funding_event_ts", value)

    @field_serializer("funding_event_ts")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("funding_rate", "oracle_price_at_funding")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class ExecutionReplayCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_execution_replay_case.v1"] = (
        "crypto_perp_execution_replay_case.v1"
    )
    case_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[ReplayArtifactRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    event_id: str
    decision_id: str
    symbol: str
    side: ReplaySide
    decision_at: datetime
    entry_arrival_at: datetime
    planned_exit_at: datetime
    exit_arrival_at: datetime
    holding_minutes: int = Field(gt=0)
    entry_latency_ms: int = Field(ge=0)
    exit_latency_ms: int = Field(ge=0)
    notional_usd: DecimalValue = Field(gt=0)
    taker_fee_rate: DecimalValue = Field(gt=0)
    max_book_wait_ms: int = Field(default=1000, ge=0)
    allow_partial_fill: bool = False
    capture_manifest_ref: ReplayArtifactRef
    funding_events: list[ReplayFundingEvent] = Field(default_factory=list)
    evidence_basis: Literal["DEPTH15_SNAPSHOT"] = "DEPTH15_SNAPSHOT"
    known_limits: list[str] = Field(default_factory=list)

    @field_validator(
        "created_at",
        "decision_at",
        "entry_arrival_at",
        "planned_exit_at",
        "exit_arrival_at",
        mode="before",
    )
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_validator("event_id", "decision_id", "case_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("symbol must not be empty")
        return stripped

    @model_validator(mode="after")
    def validate_timeline(self) -> ExecutionReplayCase:
        if self.entry_arrival_at < self.decision_at:
            raise ValueError("entry_arrival_at must be >= decision_at")
        if self.planned_exit_at <= self.entry_arrival_at:
            raise ValueError("planned_exit_at must be after entry_arrival_at")
        if self.exit_arrival_at < self.planned_exit_at:
            raise ValueError("exit_arrival_at must be >= planned_exit_at")
        return self

    @field_serializer(
        "created_at",
        "decision_at",
        "entry_arrival_at",
        "planned_exit_at",
        "exit_arrival_at",
    )
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("notional_usd", "taker_fee_rate")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class BookSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    ts_event: datetime
    ts_received: datetime
    recv_ts_ms: int | None = Field(default=None, ge=0)
    sequence: int | None = None
    checksum: int | None = None
    bids: list[tuple[DecimalValue, DecimalValue]]
    asks: list[tuple[DecimalValue, DecimalValue]]
    source_segment_path: str
    source_row_index: int = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("symbol must not be empty")
        return stripped

    @field_validator("ts_event", "ts_received", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @model_validator(mode="after")
    def validate_book(self) -> BookSnapshot:
        if not self.bids or not self.asks:
            raise ValueError("both book sides are required")
        if any(
            price <= 0 or quantity <= 0
            for price, quantity in [*self.bids, *self.asks]
        ):
            raise ValueError("book prices and quantities must be positive")
        if list(self.bids) != sorted(
            self.bids,
            key=lambda item: item[0],
            reverse=True,
        ):
            raise ValueError("bids must be sorted descending")
        if list(self.asks) != sorted(self.asks, key=lambda item: item[0]):
            raise ValueError("asks must be sorted ascending")
        if self.bids[0][0] >= self.asks[0][0]:
            raise ValueError("book must not be crossed")
        return self

    @field_serializer("ts_event", "ts_received")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("bids", "asks")
    def serialize_levels(
        self,
        value: list[tuple[Decimal, Decimal]],
    ) -> list[list[str]]:
        return [
            [decimal_to_json_string(price), decimal_to_json_string(quantity)]
            for price, quantity in value
        ]


class DepthFillResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: FillStatus
    requested_notional_usd: DecimalValue | None = None
    requested_quantity: DecimalValue | None = None
    filled_notional_usd: DecimalValue = Decimal("0")
    filled_quantity: DecimalValue = Decimal("0")
    unfilled_notional_usd: DecimalValue | None = None
    unfilled_quantity: DecimalValue | None = None
    vwap: DecimalValue | None = None
    worst_price: DecimalValue | None = None
    levels_consumed: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_fill(self) -> DepthFillResult:
        if self.filled_notional_usd < 0 or self.filled_quantity < 0:
            raise ValueError("filled values must be non-negative")
        if self.status == "UNFILLABLE" and (
            self.filled_notional_usd != 0 or self.filled_quantity != 0
        ):
            raise ValueError("unfillable result must not report a fill")
        if self.status != "UNFILLABLE" and (self.vwap is None or self.vwap <= 0):
            raise ValueError("filled result requires a positive VWAP")
        return self

    @field_serializer(
        "requested_notional_usd",
        "requested_quantity",
        "filled_notional_usd",
        "filled_quantity",
        "unfilled_notional_usd",
        "unfilled_quantity",
        "vwap",
        "worst_price",
    )
    def serialize_decimals(self, value: Decimal | None) -> str | None:
        return _serialize_decimal(value)


class ExecutionReplayResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_execution_replay_result.v1"] = (
        "crypto_perp_execution_replay_result.v1"
    )
    result_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[ReplayArtifactRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    case_id: str
    event_id: str
    symbol: str
    side: ReplaySide
    replay_status: ReplayStatus
    entry_snapshot_at: datetime | None = None
    entry_snapshot_received_at: datetime | None = None
    exit_snapshot_at: datetime | None = None
    exit_snapshot_received_at: datetime | None = None
    entry_book_wait_ms: int | None = Field(default=None, ge=0)
    exit_book_wait_ms: int | None = Field(default=None, ge=0)
    entry_fill: DepthFillResult | None = None
    exit_fill: DepthFillResult | None = None
    gross_pnl_usd: DecimalValue | None = None
    entry_fee_usd: DecimalValue = Decimal("0")
    exit_fee_usd: DecimalValue | None = None
    funding_cashflow_usd: DecimalValue | None = None
    net_pnl_estimate_usd: DecimalValue | None = None
    residual_position_quantity: DecimalValue = Decimal("0")
    known_limits: list[str]
    actual_cash_used: Literal[False] = False
    profit_proven: Literal[False] = False

    @field_validator(
        "created_at",
        "entry_snapshot_at",
        "entry_snapshot_received_at",
        "exit_snapshot_at",
        "exit_snapshot_received_at",
        mode="before",
    )
    @classmethod
    def validate_utc_optional(
        cls,
        value: datetime | str | None,
    ) -> datetime | None:
        return None if value is None else ensure_utc_aware("timestamp", value)

    @model_validator(mode="after")
    def validate_complete_result(self) -> ExecutionReplayResult:
        if self.replay_status == "COMPLETE":
            if self.net_pnl_estimate_usd is None or self.residual_position_quantity != 0:
                raise ValueError(
                    "complete replay requires final PnL and zero residual position"
                )
        return self

    @field_serializer(
        "created_at",
        "entry_snapshot_at",
        "entry_snapshot_received_at",
        "exit_snapshot_at",
        "exit_snapshot_received_at",
    )
    def serialize_timestamp_optional(self, value: datetime | None) -> str | None:
        return None if value is None else serialize_utc_z(value)

    @field_serializer(
        "gross_pnl_usd",
        "entry_fee_usd",
        "exit_fee_usd",
        "funding_cashflow_usd",
        "net_pnl_estimate_usd",
        "residual_position_quantity",
    )
    def serialize_decimals(self, value: Decimal | None) -> str | None:
        return _serialize_decimal(value)
