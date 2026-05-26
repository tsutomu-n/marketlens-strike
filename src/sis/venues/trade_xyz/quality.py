from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeXyzQualityPolicy:
    max_spread_bps: float = 50.0
    min_depth_10bps_usd: float = 1000.0
    max_price_age_ms: int = 10_000


def quality_blocks(
    *,
    spread_bps: float | None,
    depth_10bps_usd: float | None,
    recv_ts_ms: int | None,
    source_ts_ms: int | None,
    policy: TradeXyzQualityPolicy | None = None,
) -> list[str]:
    cfg = policy or TradeXyzQualityPolicy()
    reasons: list[str] = []

    if spread_bps is not None and spread_bps > cfg.max_spread_bps:
        reasons.append("BLOCK_SPREAD_TOO_WIDE")
    if depth_10bps_usd is not None and depth_10bps_usd < cfg.min_depth_10bps_usd:
        reasons.append("BLOCK_DEPTH_TOO_THIN")
    if (
        recv_ts_ms is not None
        and source_ts_ms is not None
        and recv_ts_ms >= source_ts_ms
        and recv_ts_ms - source_ts_ms > cfg.max_price_age_ms
    ):
        reasons.append("BLOCK_PRICE_STALE")
    return reasons
