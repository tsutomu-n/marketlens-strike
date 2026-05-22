from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl


@dataclass(frozen=True)
class CostProfile:
    venue: str
    symbol: str
    open_fee_bps: float
    close_fee_bps: float
    spread_p50_bps: float
    spread_p90_bps: float
    holding_cost_4h_bps: float
    holding_cost_24h_bps: float
    holding_cost_72h_bps: float


def _as_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def load_cost_profiles(path: Path | None) -> dict[tuple[str, str], CostProfile]:
    if path is None or not path.exists():
        return {}

    frame = pl.read_csv(path)
    profiles: dict[tuple[str, str], CostProfile] = {}
    for row in frame.to_dicts():
        venue = str(row.get("venue") or "").strip().lower()
        symbol = str(row.get("symbol") or "").strip().upper()
        if not venue or not symbol:
            continue

        profiles[(venue, symbol)] = CostProfile(
            venue=venue,
            symbol=symbol,
            open_fee_bps=_as_float(row.get("open_fee_bps")) or 0.0,
            close_fee_bps=_as_float(row.get("close_fee_bps")) or 0.0,
            spread_p50_bps=_as_float(row.get("spread_p50_bps")) or 0.0,
            spread_p90_bps=_as_float(row.get("spread_p90_bps")) or 0.0,
            holding_cost_4h_bps=_as_float(row.get("holding_cost_4h_bps")) or 0.0,
            holding_cost_24h_bps=_as_float(row.get("holding_cost_24h_bps")) or 0.0,
            holding_cost_72h_bps=_as_float(row.get("holding_cost_72h_bps")) or 0.0,
        )
    return profiles


def _normalize_holding_horizon(holding_horizon: str | None) -> str:
    value = (holding_horizon or "").strip().lower()
    if value in {"4h", "240m", "240min"}:
        return "4h"
    if value in {"1d", "24h", "d"}:
        return "1d"
    if value in {"3d", "72h"}:
        return "3d"
    return "4h"


def _holding_cost_for_horizon(profile: CostProfile, holding_horizon: str | None) -> float:
    normalized = _normalize_holding_horizon(holding_horizon)
    if normalized == "1d":
        return profile.holding_cost_24h_bps
    if normalized == "3d":
        return profile.holding_cost_72h_bps
    return profile.holding_cost_4h_bps


def round_trip_cost_bps(
    *,
    venue: str,
    symbol: str,
    holding_horizon: str,
    quote_spread_bps: float | None,
    cost_profiles: dict[tuple[str, str], CostProfile],
) -> tuple[float, str]:
    key = (venue.strip().lower(), symbol.strip().upper())
    profile = cost_profiles.get(key)

    if profile is None:
        fee_bps = 10.0 if key[0] == "gtrade" else 0.0
        spread = quote_spread_bps if quote_spread_bps is not None else 0.0
        return fee_bps + spread, "fallback"

    if quote_spread_bps is not None:
        spread = quote_spread_bps
        spread_source = "live_spread"
    elif profile.spread_p90_bps > 0:
        spread = profile.spread_p90_bps
        spread_source = "matrix_spread_p90"
    elif profile.spread_p50_bps > 0:
        spread = profile.spread_p50_bps
        spread_source = "matrix_spread_p50"
    else:
        spread = 0.0
        spread_source = "fallback_spread_zero"

    holding = _holding_cost_for_horizon(profile, holding_horizon)
    total = profile.open_fee_bps + profile.close_fee_bps + spread + holding
    return total, spread_source
