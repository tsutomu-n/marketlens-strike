from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
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


CASH_LEDGER_SCHEMA_VERSION = "crypto_perp_cash_ledger.v1"


class CashLedgerEntryType(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    REALIZED_PNL = "REALIZED_PNL"
    FEE = "FEE"
    FUNDING = "FUNDING"
    INFRA_COST = "INFRA_COST"
    POD_RUIN = "POD_RUIN"


class CashLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry_id: str
    pod_id: str
    event_id: str | None
    entry_type: CashLedgerEntryType
    amount_usd: DecimalValue
    occurred_at: datetime
    ruined: bool = False

    @field_validator("entry_id", "pod_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("event_id")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty when provided")
        return stripped

    @field_validator("occurred_at", mode="before")
    @classmethod
    def validate_occurred_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("occurred_at", value)

    @field_serializer("occurred_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("amount_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CashPodSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pod_id: str
    entry_count: int = Field(ge=0)
    total_deposits_usd: DecimalValue
    total_withdrawals_usd: DecimalValue
    total_realized_pnl_usd: DecimalValue
    total_fees_usd: DecimalValue
    total_funding_usd: DecimalValue
    total_infra_cost_usd: DecimalValue
    total_ruin_usd: DecimalValue
    actual_cash_result_usd: DecimalValue
    ruined: bool

    @field_serializer(
        "total_deposits_usd",
        "total_withdrawals_usd",
        "total_realized_pnl_usd",
        "total_fees_usd",
        "total_funding_usd",
        "total_infra_cost_usd",
        "total_ruin_usd",
        "actual_cash_result_usd",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CryptoPerpCashLedger(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_cash_ledger.v1"] = CASH_LEDGER_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    ledger_id: str
    observed_at: datetime
    entries: list[CashLedgerEntry]
    pod_summaries: dict[str, CashPodSummary]
    total_deposits_usd: DecimalValue
    total_withdrawals_usd: DecimalValue
    total_realized_pnl_usd: DecimalValue
    total_fees_usd: DecimalValue
    total_funding_usd: DecimalValue
    total_infra_cost_usd: DecimalValue
    total_ruin_usd: DecimalValue
    actual_cash_result_usd: DecimalValue
    known_gaps: list[str]

    @field_validator("created_at", "observed_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_validator("artifact_id", "ledger_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_serializer("created_at", "observed_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "total_deposits_usd",
        "total_withdrawals_usd",
        "total_realized_pnl_usd",
        "total_fees_usd",
        "total_funding_usd",
        "total_infra_cost_usd",
        "total_ruin_usd",
        "actual_cash_result_usd",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


_ZERO = Decimal("0")


def _sum_amount(entries: Iterable[CashLedgerEntry], entry_type: CashLedgerEntryType) -> Decimal:
    return sum((entry.amount_usd for entry in entries if entry.entry_type == entry_type), _ZERO)


def _sum_result(entries: Iterable[CashLedgerEntry]) -> Decimal:
    return sum((entry.amount_usd for entry in entries), _ZERO)


def _pod_summary(pod_id: str, entries: Sequence[CashLedgerEntry]) -> CashPodSummary:
    return CashPodSummary(
        pod_id=pod_id,
        entry_count=len(entries),
        total_deposits_usd=_sum_amount(entries, CashLedgerEntryType.DEPOSIT),
        total_withdrawals_usd=_sum_amount(entries, CashLedgerEntryType.WITHDRAWAL),
        total_realized_pnl_usd=_sum_amount(entries, CashLedgerEntryType.REALIZED_PNL),
        total_fees_usd=_sum_amount(entries, CashLedgerEntryType.FEE),
        total_funding_usd=_sum_amount(entries, CashLedgerEntryType.FUNDING),
        total_infra_cost_usd=_sum_amount(entries, CashLedgerEntryType.INFRA_COST),
        total_ruin_usd=_sum_amount(entries, CashLedgerEntryType.POD_RUIN),
        actual_cash_result_usd=_sum_result(entries),
        ruined=any(
            entry.ruined or entry.entry_type == CashLedgerEntryType.POD_RUIN for entry in entries
        ),
    )


def _pod_summaries(entries: Sequence[CashLedgerEntry]) -> dict[str, CashPodSummary]:
    grouped: dict[str, list[CashLedgerEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.pod_id, []).append(entry)
    return {
        pod_id: _pod_summary(pod_id, pod_entries) for pod_id, pod_entries in sorted(grouped.items())
    }


def build_cash_ledger(
    *,
    ledger_id: str,
    observed_at: datetime | str,
    entries: Sequence[CashLedgerEntry],
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-cash-ledger",
) -> CryptoPerpCashLedger:
    observed = ensure_utc_aware("observed_at", observed_at)
    entry_list = list(entries)
    return CryptoPerpCashLedger(
        artifact_id=stable_hash(
            ["crypto-perp-cash-ledger-artifact", ledger_id, serialize_utc_z(observed)]
        ),
        created_at=observed,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=list(source_refs or []),
        ledger_id=ledger_id,
        observed_at=observed,
        entries=entry_list,
        pod_summaries=_pod_summaries(entry_list),
        total_deposits_usd=_sum_amount(entry_list, CashLedgerEntryType.DEPOSIT),
        total_withdrawals_usd=_sum_amount(entry_list, CashLedgerEntryType.WITHDRAWAL),
        total_realized_pnl_usd=_sum_amount(entry_list, CashLedgerEntryType.REALIZED_PNL),
        total_fees_usd=_sum_amount(entry_list, CashLedgerEntryType.FEE),
        total_funding_usd=_sum_amount(entry_list, CashLedgerEntryType.FUNDING),
        total_infra_cost_usd=_sum_amount(entry_list, CashLedgerEntryType.INFRA_COST),
        total_ruin_usd=_sum_amount(entry_list, CashLedgerEntryType.POD_RUIN),
        actual_cash_result_usd=_sum_result(entry_list),
        known_gaps=list(known_gaps or []),
    )
