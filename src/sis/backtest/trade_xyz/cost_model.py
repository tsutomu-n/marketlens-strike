from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml


FundingPolicy = Literal["disabled_v0", "nullable_zero_v0", "fixture_hourly_v0"]


@dataclass(frozen=True)
class FeeResolution:
    taker_fee_bps: float | None
    maker_fee_bps: float | None
    source: str

    @classmethod
    def unresolved(cls) -> FeeResolution:
        return cls(taker_fee_bps=None, maker_fee_bps=None, source="unresolved")

    @property
    def resolved(self) -> bool:
        return self.taker_fee_bps is not None and self.maker_fee_bps is not None


def _as_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed >= 0 else None


def _load_fee_fallback(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    fallback = payload.get("fee_model", {}).get("trade_xyz", {}).get("fallback", {})
    if not isinstance(fallback, dict):
        return {}
    loaded: dict[str, dict[str, float]] = {}
    for mode, values in fallback.items():
        if not isinstance(values, dict):
            continue
        taker = _as_float(values.get("taker_bps"))
        maker = _as_float(values.get("maker_bps"))
        if taker is not None and maker is not None:
            loaded[str(mode)] = {"taker_bps": taker, "maker_bps": maker}
    return loaded


def resolve_fee_bps(
    row: dict[str, Any],
    *,
    fee_model_path: str | Path,
    fee_scenario: Literal["row_resolved", "standard", "growth"],
) -> FeeResolution:
    taker = _as_float(row.get("taker_fee_bps"))
    maker = _as_float(row.get("maker_fee_bps"))
    if taker is not None and maker is not None and fee_scenario == "row_resolved":
        return FeeResolution(taker_fee_bps=taker, maker_fee_bps=maker, source="row")

    mode = fee_scenario if fee_scenario != "row_resolved" else str(row.get("fee_mode") or "")
    fallback = _load_fee_fallback(Path(fee_model_path))
    values = fallback.get(mode)
    if values is None:
        return FeeResolution.unresolved()
    return FeeResolution(
        taker_fee_bps=values["taker_bps"],
        maker_fee_bps=values["maker_bps"],
        source=f"{fee_model_path}:{mode}",
    )


def calculate_market_like_fee(*, fill_notional_usd: float, taker_fee_bps: float) -> float:
    if fill_notional_usd < 0:
        raise ValueError("fill_notional_usd must be >= 0")
    if taker_fee_bps < 0:
        raise ValueError("taker_fee_bps must be >= 0")
    return fill_notional_usd * taker_fee_bps / 10_000


def calculate_v0_funding_amount(
    *,
    policy: FundingPolicy,
    position_qty: float,
    oracle_price: float | None,
    funding_rate: float | None,
    is_funding_event: bool,
    event_ts: datetime,
) -> tuple[float, str | None]:
    _ = event_ts
    if policy == "disabled_v0":
        return 0.0, None
    if policy == "nullable_zero_v0":
        if funding_rate is not None:
            return 0.0, "funding_rate_present_without_interval_assertion"
        return 0.0, None
    if not is_funding_event:
        return 0.0, None
    if funding_rate is None:
        return 0.0, None
    if oracle_price is None or oracle_price <= 0:
        return 0.0, "oracle_price_missing_for_funding"
    return -(position_qty * oracle_price * funding_rate), None
