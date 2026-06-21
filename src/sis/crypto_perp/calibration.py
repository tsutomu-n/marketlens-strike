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


CALIBRATION_REPORT_SCHEMA_VERSION = "crypto_perp_calibration_report.v1"


class ActualFill(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    side: Literal["buy", "sell"]
    actual_vwap: DecimalValue
    actual_fee_usd: DecimalValue

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_serializer("actual_vwap", "actual_fee_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class SimulatedFill(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    side: Literal["buy", "sell"]
    simulated_vwap: DecimalValue
    simulated_fee_usd: DecimalValue

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_serializer("simulated_vwap", "simulated_fee_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CalibrationBiasRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    side: Literal["buy", "sell"]
    status: Literal["MATCHED", "MISSING_SIMULATION"]
    actual_vwap: DecimalValue
    simulated_vwap: DecimalValue | None
    vwap_bias_usd: DecimalValue | None
    actual_fee_usd: DecimalValue
    simulated_fee_usd: DecimalValue | None
    fee_bias_usd: DecimalValue | None

    @field_serializer(
        "actual_vwap",
        "simulated_vwap",
        "vwap_bias_usd",
        "actual_fee_usd",
        "simulated_fee_usd",
        "fee_bias_usd",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


class CalibrationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_calibration_report.v1"] = CALIBRATION_REPORT_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    report_id: str
    generated_at: datetime
    fill_count: int = Field(ge=0)
    calibration_confidence: Literal["LOW", "MEDIUM", "HIGH"]
    bias_rows: list[CalibrationBiasRow]
    known_gaps: list[str]

    @field_validator("created_at", "generated_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "generated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _simulated_key(fill: SimulatedFill) -> tuple[str, Literal["buy", "sell"]]:
    return fill.event_id, fill.side


def _confidence(
    matched_count: int, min_high_confidence_fills: int
) -> Literal["LOW", "MEDIUM", "HIGH"]:
    if matched_count < min_high_confidence_fills:
        return "LOW"
    return "HIGH"


def build_calibration_report(
    *,
    report_id: str,
    generated_at: datetime | str,
    actual_fills: Sequence[ActualFill],
    simulated_fills: Sequence[SimulatedFill],
    min_high_confidence_fills: int,
    source_refs: Sequence[dict[str, str]] | None = None,
    producer_command: str = "crypto-perp-calibration-report",
) -> CalibrationReport:
    generated = ensure_utc_aware("generated_at", generated_at)
    simulated_by_key = {_simulated_key(fill): fill for fill in simulated_fills}
    rows: list[CalibrationBiasRow] = []
    known_gaps: list[str] = []
    matched_count = 0
    for actual in actual_fills:
        simulated = simulated_by_key.get((actual.event_id, actual.side))
        if simulated is None:
            known_gaps.append("MISSING_SIMULATION")
            rows.append(
                CalibrationBiasRow(
                    event_id=actual.event_id,
                    side=actual.side,
                    status="MISSING_SIMULATION",
                    actual_vwap=actual.actual_vwap,
                    simulated_vwap=None,
                    vwap_bias_usd=None,
                    actual_fee_usd=actual.actual_fee_usd,
                    simulated_fee_usd=None,
                    fee_bias_usd=None,
                )
            )
            continue
        matched_count += 1
        rows.append(
            CalibrationBiasRow(
                event_id=actual.event_id,
                side=actual.side,
                status="MATCHED",
                actual_vwap=actual.actual_vwap,
                simulated_vwap=simulated.simulated_vwap,
                vwap_bias_usd=actual.actual_vwap - simulated.simulated_vwap,
                actual_fee_usd=actual.actual_fee_usd,
                simulated_fee_usd=simulated.simulated_fee_usd,
                fee_bias_usd=actual.actual_fee_usd - simulated.simulated_fee_usd,
            )
        )
    known_gaps = list(dict.fromkeys(known_gaps))
    return CalibrationReport(
        artifact_id=stable_hash(
            ["crypto-perp-calibration-report-artifact", report_id, serialize_utc_z(generated)]
        ),
        created_at=generated,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=list(source_refs or []),
        report_id=report_id,
        generated_at=generated,
        fill_count=matched_count,
        calibration_confidence=_confidence(matched_count, min_high_confidence_fills),
        bias_rows=rows,
        known_gaps=known_gaps,
    )
