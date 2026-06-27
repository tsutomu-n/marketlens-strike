from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, DecimalValue, stable_hash
from sis.crypto_perp.tournament import TOURNAMENT_ACTIONS, TournamentAction
from sis.crypto_perp.tournament_rows import CostAwareTournamentRow


BIAS_GUARD_SCHEMA_VERSION = "crypto_perp_bias_guard.v1"
BiasGuardStatus = Literal["PASS", "BLOCKED"]
PboStatus = Literal["ESTIMATED", "NOT_ESTIMABLE"]


class BiasGuardCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check_id: str
    passed: bool
    observed: str
    required: str
    severity: Literal["error", "warning"] = "error"


class CryptoPerpBiasGuard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_bias_guard.v1"] = BIAS_GUARD_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    guard_id: str
    guard_status: BiasGuardStatus
    pbo_status: PboStatus
    event_count: int = Field(ge=0)
    min_events_for_pbo: int = Field(gt=0)
    fold_count: int = Field(ge=0)
    max_profit_concentration: DecimalValue
    checks: list[BiasGuardCheck]
    stop_reasons: list[str]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("max_profit_concentration")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value.normalize()) if value != value.to_integral() else str(value.quantize(Decimal("1")))


def _check(check_id: str, passed: bool, observed: object, required: object) -> BiasGuardCheck:
    return BiasGuardCheck(
        check_id=check_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
    )


def _event_set(rows: Sequence[CostAwareTournamentRow]) -> list[str]:
    return sorted({row.event_id for row in rows})


def _profit_concentration(rows: Sequence[CostAwareTournamentRow], action: TournamentAction) -> Decimal:
    values = [row.cost_adjusted_cash_estimate_usd for row in rows if row.action == action]
    positives = [value for value in values if value > 0]
    total = sum(positives, Decimal("0"))
    if total == 0:
        return Decimal("0")
    return max(positives) / total


def _max_concentration(rows: Sequence[CostAwareTournamentRow]) -> Decimal:
    return max((_profit_concentration(rows, action) for action in TOURNAMENT_ACTIONS), default=Decimal("0"))


def build_bias_guard(
    *,
    rows: Sequence[CostAwareTournamentRow],
    created_at: datetime | str,
    min_events_for_pbo: int = 30,
    fold_count: int = 0,
    lookahead_violation: bool = False,
    recursive_warmup_violation: bool = False,
    max_profit_concentration: Decimal = Decimal("0.60"),
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-bias-guard",
) -> CryptoPerpBiasGuard:
    if not rows:
        raise ValueError("rows must not be empty")
    if min_events_for_pbo <= 0:
        raise ValueError("min_events_for_pbo must be positive")
    if fold_count < 0:
        raise ValueError("fold_count must be non-negative")
    if max_profit_concentration < 0:
        raise ValueError("max_profit_concentration must be non-negative")
    created = ensure_utc_aware("created_at", created_at)
    event_set = _event_set(rows)
    event_count = len(event_set)
    pbo_status: PboStatus = (
        "ESTIMATED" if event_count >= min_events_for_pbo and fold_count >= 2 else "NOT_ESTIMABLE"
    )
    min_stress = min(row.stress_cash_estimate_usd for row in rows if row.action != "NO_TRADE")
    concentration = _max_concentration(rows)
    checks = [
        _check("same_event_set_has_three_actions", len(rows) == event_count * 3, len(rows), event_count * 3),
        _check("lookahead_absent", not lookahead_violation, lookahead_violation, False),
        _check("recursive_warmup_absent", not recursive_warmup_violation, recursive_warmup_violation, False),
        _check("sample_sufficient_for_pbo", pbo_status == "ESTIMATED", pbo_status, "ESTIMATED"),
        _check("stress_cash_non_negative", min_stress >= 0, min_stress, ">= 0"),
        _check(
            "profit_concentration_within_limit",
            concentration <= max_profit_concentration,
            concentration,
            f"<= {max_profit_concentration}",
        ),
    ]
    stop_reasons: list[str] = []
    for check in checks:
        if not check.passed:
            stop_reasons.append(f"BIAS_GUARD_FAILED_{check.check_id}")
    computed_gaps = list(known_gaps or [])
    if pbo_status == "NOT_ESTIMABLE":
        computed_gaps.append("PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT")
    computed_gaps = list(dict.fromkeys(computed_gaps))
    guard_status: BiasGuardStatus = "BLOCKED" if stop_reasons else "PASS"
    guard_id = stable_hash(
        [
            "crypto-perp-bias-guard",
            [row.model_dump(mode="json") for row in rows],
            serialize_utc_z(created),
            min_events_for_pbo,
            fold_count,
            lookahead_violation,
            recursive_warmup_violation,
            max_profit_concentration,
        ]
    )
    summary = {
        "guard_status": guard_status,
        "pbo_status": pbo_status,
        "event_count": event_count,
        "failed_check_count": len(stop_reasons),
        "min_stress_cash_estimate_usd": min_stress,
        "max_profit_concentration_observed": concentration,
    }
    return CryptoPerpBiasGuard(
        artifact_id=stable_hash(["crypto-perp-bias-guard-artifact", guard_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=[dict(ref) for ref in source_refs or []],
        guard_id=guard_id,
        guard_status=guard_status,
        pbo_status=pbo_status,
        event_count=event_count,
        min_events_for_pbo=min_events_for_pbo,
        fold_count=fold_count,
        max_profit_concentration=max_profit_concentration,
        checks=checks,
        stop_reasons=list(dict.fromkeys(stop_reasons)),
        known_gaps=computed_gaps,
        summary=summary,
    )
