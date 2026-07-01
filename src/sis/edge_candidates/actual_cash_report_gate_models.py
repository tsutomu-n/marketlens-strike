from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN, DecimalValue, decimal_to_json_string
from sis.edge_candidates import PROFIT_CORE_ACTUAL_CASH_REPORT_GATE_SCHEMA_VERSION
from sis.strategy_inputs.models import ProducerInfo


class ProfitCoreActualCashReportDecision(StrEnum):
    PROMOTE = "promote"
    WAIT = "wait"
    KILL = "kill"


class ProfitCoreActualCashReportStatus(StrEnum):
    COMPLETE = "complete"
    BLOCKED = "blocked"


class ActualCashReportGateArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_role: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_role", "path", "sha256")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact ref text fields must not be empty")
        return stripped


class ActualCashReportGateBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    blocker_code: str
    message: str
    source: str
    severity: Literal["block", "wait", "kill"]

    @field_validator("blocker_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("blocker_code must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("message", "source")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("blocker text fields must not be empty")
        return stripped


class ActualCashReportGatePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_events: int = Field(default=2, ge=1)
    max_largest_loss_usd: DecimalValue = Decimal("25")
    max_profit_concentration: DecimalValue = Decimal("0.60")
    max_operator_burden_minutes: DecimalValue = Decimal("120")

    @field_validator(
        "max_largest_loss_usd",
        "max_profit_concentration",
        "max_operator_burden_minutes",
    )
    @classmethod
    def validate_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("policy thresholds must be non-negative")
        return value

    @field_serializer(
        "max_largest_loss_usd",
        "max_profit_concentration",
        "max_operator_burden_minutes",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class ProfitCoreActualCashReportGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_actual_cash_report_gate.v1"] = (
        PROFIT_CORE_ACTUAL_CASH_REPORT_GATE_SCHEMA_VERSION
    )
    report_id: str
    recorded_at: datetime
    producer: ProducerInfo
    candidate_id: str
    measurement_id: str
    report_status: ProfitCoreActualCashReportStatus
    decision: ProfitCoreActualCashReportDecision
    promotion_allowed: bool
    blockers: list[ActualCashReportGateBlocker] = Field(default_factory=list)
    source_refs: list[ActualCashReportGateArtifactRef] = Field(min_length=4)
    measurement_ref: ActualCashReportGateArtifactRef
    readiness_packet_ref: ActualCashReportGateArtifactRef | None = None
    evidence_packet_ref: ActualCashReportGateArtifactRef | None = None
    actual_cash_rows_ref: ActualCashReportGateArtifactRef | None = None
    protocol_ref: ActualCashReportGateArtifactRef | None = None
    multiplicity_account_ref: ActualCashReportGateArtifactRef | None = None
    backtest_kill_gate_ref: ActualCashReportGateArtifactRef | None = None
    virtual_gate_ref: ActualCashReportGateArtifactRef | None = None
    policy: ActualCashReportGatePolicy
    sample_size: dict[str, Any]
    event_diversity: dict[str, Any]
    measured_action: str | None
    actual_cash_result_usd: str | None
    no_trade_result_usd: str | None
    actual_cash_edge_over_NO_TRADE: str | None
    profit_concentration: str | None
    largest_loss_usd: str | None
    operator_burden_minutes: str | None
    reconcile_mismatch: bool
    evidence_basis: dict[str, dict[str, Any]]
    actual_cash: bool
    cash_metric_basis: Literal["actual_cash", "blocked"]
    order_submitted_by_this_command: Literal[False] = False
    network_attempted: Literal[False] = False
    credentials_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    permits_live_order: Literal[False] = False
    permits_actual_cash_execution: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "order_submitted_by_this_command": False,
            "network_attempted": False,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "permits_live_order": False,
            "permits_actual_cash_execution": False,
        }
    )

    @field_validator("report_id", "candidate_id", "measurement_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("recorded_at", mode="before")
    @classmethod
    def validate_recorded_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("recorded_at", value)

    @field_validator("boundary")
    @classmethod
    def validate_boundary(cls, value: dict[str, bool]) -> dict[str, bool]:
        expected = {
            "order_submitted_by_this_command": False,
            "network_attempted": False,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "permits_live_order": False,
            "permits_actual_cash_execution": False,
        }
        if value != expected:
            raise ValueError("boundary must keep report gate side effects false")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class ActualCashReportGateWriteResult:
    gate: ProfitCoreActualCashReportGate
    gate_path: Path
    gate_sha256: str


__all__ = [
    "ActualCashReportGateArtifactRef",
    "ActualCashReportGateBlocker",
    "ActualCashReportGatePolicy",
    "ActualCashReportGateWriteResult",
    "ProfitCoreActualCashReportDecision",
    "ProfitCoreActualCashReportGate",
    "ProfitCoreActualCashReportStatus",
]
