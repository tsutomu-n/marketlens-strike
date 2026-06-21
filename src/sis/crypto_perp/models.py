from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    BeforeValidator,
    field_serializer,
    field_validator,
)

from sis.crypto_perp.clock import serialize_utc_z


CONFIG_SCHEMA_VERSION = "crypto_perp_lab_config.v1"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DecimalValue = Annotated[Decimal, BeforeValidator(lambda value: Decimal(str(value)))]


class CryptoPerpAction(StrEnum):
    REVERSAL_SHORT = "REVERSAL_SHORT"
    CONTINUATION_LONG = "CONTINUATION_LONG"
    NO_TRADE = "NO_TRADE"
    UNKNOWN = "UNKNOWN"
    CAPTURE_ONLY = "CAPTURE_ONLY"


class CaptureChannel(StrEnum):
    TRADES = "trades"
    BOOKS1 = "books1"
    BOOKS15 = "books15"


def decimal_to_json_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


def stable_hash(parts: list[Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CryptoPerpBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False


class CryptoPerpProducer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal["sis"] = "sis"
    command: str

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must not be empty")
        return stripped


class ConfigValidationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_config_validation.v1"] = "crypto_perp_config_validation.v1"
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    config_id: str
    config_hash: str
    validation_status: Literal["PASS"] = "PASS"
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)
