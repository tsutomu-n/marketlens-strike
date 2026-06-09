from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VenueSuitabilityStage = Literal["research", "paper_candidate", "paper_intent", "live"]

NDX_QQQ_EXECUTION_SYMBOLS = frozenset({"NDX", "QQQ", "XYZ100"})
NDX_QQQ_REAL_MARKET_SYMBOLS = frozenset({"^NDX", "NDX", "QQQ"})

VENUE_UNKNOWN = "VENUE_UNKNOWN"
VENUE_ASSET_UNIVERSE_MISMATCH = "VENUE_ASSET_UNIVERSE_MISMATCH"
VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT = "VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT"
VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION = (
    "VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION"
)


@dataclass(frozen=True)
class VenueSuitability:
    venue_id: str
    asset_universe: str
    supports_ndx_proxy: bool
    supports_qqq_direct: bool
    research_allowed: bool
    paper_candidate_allowed: bool
    paper_intent_allowed: bool
    live_allowed: bool
    default_enabled: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class VenueSuitabilityDecision:
    venue_id: str
    stage: VenueSuitabilityStage
    execution_symbol: str
    real_market_symbol: str
    ndx_qqq_family: bool
    allowed: bool
    reason_codes: tuple[str, ...]


VENUE_SUITABILITY_CATALOG: dict[str, VenueSuitability] = {
    "trade_xyz": VenueSuitability(
        venue_id="trade_xyz",
        asset_universe="local_fixture_or_demo",
        supports_ndx_proxy=True,
        supports_qqq_direct=False,
        research_allowed=True,
        paper_candidate_allowed=True,
        paper_intent_allowed=True,
        live_allowed=False,
        default_enabled=True,
    ),
    "bitget_demo": VenueSuitability(
        venue_id="bitget_demo",
        asset_universe="crypto_perp_fixture",
        supports_ndx_proxy=False,
        supports_qqq_direct=False,
        research_allowed=True,
        paper_candidate_allowed=True,
        paper_intent_allowed=True,
        live_allowed=False,
        default_enabled=True,
    ),
    "bitget_futures": VenueSuitability(
        venue_id="bitget_futures",
        asset_universe="crypto_perp",
        supports_ndx_proxy=False,
        supports_qqq_direct=False,
        research_allowed=False,
        paper_candidate_allowed=False,
        paper_intent_allowed=False,
        live_allowed=False,
        default_enabled=False,
        reason_codes=(VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT,),
    ),
    "hyperliquid_perp": VenueSuitability(
        venue_id="hyperliquid_perp",
        asset_universe="crypto_perp",
        supports_ndx_proxy=False,
        supports_qqq_direct=False,
        research_allowed=False,
        paper_candidate_allowed=False,
        paper_intent_allowed=False,
        live_allowed=False,
        default_enabled=False,
        reason_codes=(VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT,),
    ),
}


def _normalize_symbol(value: str) -> str:
    return value.strip().upper()


def is_ndx_qqq_family(*, execution_symbol: str, real_market_symbol: str) -> bool:
    execution = _normalize_symbol(execution_symbol)
    real_market = _normalize_symbol(real_market_symbol)
    return execution in NDX_QQQ_EXECUTION_SYMBOLS or real_market in NDX_QQQ_REAL_MARKET_SYMBOLS


def venue_suitability(venue_id: str) -> VenueSuitability | None:
    return VENUE_SUITABILITY_CATALOG.get(venue_id.strip().lower())


def _stage_allowed(profile: VenueSuitability, stage: VenueSuitabilityStage) -> bool:
    if stage == "research":
        return profile.research_allowed
    if stage == "paper_candidate":
        return profile.paper_candidate_allowed
    if stage == "paper_intent":
        return profile.paper_intent_allowed
    return profile.live_allowed


def _dedupe_reasons(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reason for reason in reasons if reason))


def assess_venue_suitability(
    *,
    venue_id: str,
    execution_symbol: str,
    real_market_symbol: str,
    stage: VenueSuitabilityStage,
) -> VenueSuitabilityDecision:
    normalized_venue = venue_id.strip().lower()
    normalized_execution = _normalize_symbol(execution_symbol)
    normalized_real_market = _normalize_symbol(real_market_symbol)
    ndx_qqq = is_ndx_qqq_family(
        execution_symbol=normalized_execution,
        real_market_symbol=normalized_real_market,
    )
    profile = venue_suitability(normalized_venue)
    if profile is None:
        return VenueSuitabilityDecision(
            venue_id=normalized_venue,
            stage=stage,
            execution_symbol=normalized_execution,
            real_market_symbol=normalized_real_market,
            ndx_qqq_family=ndx_qqq,
            allowed=False,
            reason_codes=(VENUE_UNKNOWN,),
        )

    reasons = list(profile.reason_codes)
    if not _stage_allowed(profile, stage):
        reasons.append(VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT)
    if stage == "live":
        reasons.append(VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT)
    if ndx_qqq and stage in {"paper_candidate", "paper_intent", "live"}:
        if normalized_venue == "trade_xyz":
            reasons.append(VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION)
        else:
            reasons.append(VENUE_ASSET_UNIVERSE_MISMATCH)

    reason_codes = _dedupe_reasons(reasons)
    return VenueSuitabilityDecision(
        venue_id=normalized_venue,
        stage=stage,
        execution_symbol=normalized_execution,
        real_market_symbol=normalized_real_market,
        ndx_qqq_family=ndx_qqq,
        allowed=not reason_codes,
        reason_codes=reason_codes,
    )


def venue_suitability_block_reasons(
    *,
    venue_id: str,
    execution_symbol: str,
    real_market_symbol: str,
    stage: VenueSuitabilityStage,
) -> list[str]:
    return list(
        assess_venue_suitability(
            venue_id=venue_id,
            execution_symbol=execution_symbol,
            real_market_symbol=real_market_symbol,
            stage=stage,
        ).reason_codes
    )
