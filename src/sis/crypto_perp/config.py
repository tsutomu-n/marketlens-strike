from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
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
from sis.crypto_perp.io import read_mapping_file
from sis.crypto_perp.models import (
    CONFIG_SCHEMA_VERSION,
    CaptureChannel,
    CryptoPerpBoundary,
    DecimalValue,
    ID_PATTERN,
    decimal_to_json_string,
)


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: Literal["bitget"]
    product_type: Literal["USDT-FUTURES"]
    base_url: str

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        stripped = value.rstrip("/")
        if not stripped.startswith("https://"):
            raise ValueError("base_url must be https")
        return stripped


class NetworkPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_external_network_allowed: Literal[False] = False
    public_network_env_var: str = "SIS_ALLOW_PUBLIC_NETWORK"
    credentialed_read_env_var: str = "SIS_ALLOW_CREDENTIALED_READ"
    tiny_live_env_var: str = "SIS_ENABLE_TINY_LIVE_MEASUREMENT"

    @field_validator("public_network_env_var", "credentialed_read_env_var", "tiny_live_env_var")
    @classmethod
    def validate_env_var(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or not stripped.replace("_", "").isalnum() or not stripped.isupper():
            raise ValueError("env var names must be uppercase identifiers")
        return stripped


class HeartbeatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruments_interval_seconds: int = Field(gt=0)
    tickers_interval_seconds: int = Field(gt=0)
    open_interest_interval_seconds: int = Field(gt=0)


class UniverseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote_asset: Literal["USDT"]
    require_online_status: bool = True
    min_listing_age_hours: int = Field(ge=0)


class ScreeningConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    history_backfill_hours: int = Field(ge=148)
    candle_interval: Literal["15m"]
    slow_window_hours: int = Field(gt=0)
    slow_return_threshold: DecimalValue = Field(gt=Decimal("0"))
    slow_turnover_impulse_threshold: DecimalValue = Field(gt=Decimal("0"))
    fast_window_minutes: int = Field(gt=0)
    fast_abs_return_floor: DecimalValue = Field(gt=Decimal("0"))
    fast_robust_z_threshold: DecimalValue = Field(gt=Decimal("0"))
    fast_turnover_percentile_threshold: DecimalValue = Field(gt=Decimal("0"), le=Decimal("1"))

    @model_validator(mode="after")
    def validate_windows(self) -> ScreeningConfig:
        if self.history_backfill_hours < self.slow_window_hours * 2:
            raise ValueError("history_backfill_hours must cover current and previous slow windows")
        return self

    @field_serializer(
        "slow_return_threshold",
        "slow_turnover_impulse_threshold",
        "fast_abs_return_floor",
        "fast_robust_z_threshold",
        "fast_turnover_percentile_threshold",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CandidateCaptureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_concurrent_captures: int = Field(ge=1, le=5)
    duration_minutes: int = Field(gt=0)
    channels: list[CaptureChannel] = Field(min_length=1)
    channel_limit_per_connection: int = Field(gt=0, le=50)

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[CaptureChannel]) -> list[CaptureChannel]:
        return list(dict.fromkeys(value))


class OutcomesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    horizon_minutes: list[int] = Field(min_length=1)

    @field_validator("horizon_minutes")
    @classmethod
    def validate_horizons(cls, value: list[int]) -> list[int]:
        cleaned = sorted(set(value))
        if any(item <= 0 for item in cleaned):
            raise ValueError("horizon_minutes must be positive")
        return cleaned


class ExecutionReplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notional_grid_usd: list[DecimalValue] = Field(min_length=1)
    latency_grid_seconds: list[int] = Field(min_length=1)

    @field_validator("notional_grid_usd")
    @classmethod
    def validate_notional_grid(cls, value: list[Decimal]) -> list[Decimal]:
        cleaned = sorted(set(value))
        if any(item <= 0 for item in cleaned):
            raise ValueError("notional_grid_usd must be positive")
        return cleaned

    @field_validator("latency_grid_seconds")
    @classmethod
    def validate_latency_grid(cls, value: list[int]) -> list[int]:
        cleaned = sorted(set(value))
        if any(item <= 0 for item in cleaned):
            raise ValueError("latency_grid_seconds must be positive")
        return cleaned

    @field_serializer("notional_grid_usd")
    def serialize_notional_grid(self, value: list[Decimal]) -> list[str]:
        return [decimal_to_json_string(item) for item in value]


class CapitalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capital_ceiling_usd: DecimalValue = Field(gt=Decimal("0"), le=Decimal("3000"))
    lifetime_experiment_budget_usd: DecimalValue = Field(gt=Decimal("0"))
    measurement_notional_min_usd: DecimalValue = Field(gt=Decimal("0"), le=Decimal("25"))
    measurement_notional_max_usd: DecimalValue = Field(gt=Decimal("0"), le=Decimal("25"))
    allow_top_up: Literal[False] = False
    max_open_positions: Literal[1] = 1

    @model_validator(mode="after")
    def validate_capital(self) -> CapitalConfig:
        if self.lifetime_experiment_budget_usd > self.capital_ceiling_usd:
            raise ValueError("lifetime_experiment_budget_usd must be <= capital_ceiling_usd")
        if self.measurement_notional_min_usd > self.measurement_notional_max_usd:
            raise ValueError("measurement min must be <= max")
        return self

    @field_serializer(
        "capital_ceiling_usd",
        "lifetime_experiment_budget_usd",
        "measurement_notional_min_usd",
        "measurement_notional_max_usd",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CryptoPerpLabConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_lab_config.v1"] = CONFIG_SCHEMA_VERSION
    config_id: str
    created_at: datetime
    provider: ProviderConfig
    network_policy: NetworkPolicyConfig
    heartbeat: HeartbeatConfig
    universe: UniverseConfig
    screening: ScreeningConfig
    candidate_capture: CandidateCaptureConfig
    outcomes: OutcomesConfig
    execution_replay: ExecutionReplayConfig
    capital: CapitalConfig
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)

    @field_validator("config_id")
    @classmethod
    def validate_config_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("config_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return value

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


def load_crypto_perp_lab_config(path: Path) -> CryptoPerpLabConfig:
    return CryptoPerpLabConfig.model_validate(read_mapping_file(path))
