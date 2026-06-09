from __future__ import annotations

from dataclasses import dataclass


VENUE_CAPABILITY_UNKNOWN = "VENUE_CAPABILITY_UNKNOWN"
VENUE_CAPABILITY_SCHEMA_DISABLED = "VENUE_CAPABILITY_SCHEMA_DISABLED"
VENUE_CAPABILITY_STRATEGY_LAB_SIGNAL_DISABLED = "VENUE_CAPABILITY_STRATEGY_LAB_SIGNAL_DISABLED"
VENUE_CAPABILITY_PAPER_CANDIDATE_DISABLED = "VENUE_CAPABILITY_PAPER_CANDIDATE_DISABLED"
VENUE_CAPABILITY_PAPER_INTENT_DISABLED = "VENUE_CAPABILITY_PAPER_INTENT_DISABLED"
VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED = "VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED"
VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED = "VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED"
VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED = "VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED"


@dataclass(frozen=True)
class VenueCapability:
    venue_id: str
    venue_family: str
    asset_universe: str
    schema_enabled: bool
    strategy_lab_signal_enabled: bool
    paper_candidate_enabled: bool
    paper_intent_enabled: bool
    read_only_network_enabled: bool
    credentialed_read_only_enabled: bool
    paper_execution_enabled: bool
    live_execution_enabled: bool
    requires_credentials: bool
    external_api_default_allowed: bool
    exchange_write_default_allowed: bool
    notes: tuple[str, ...] = ()
    block_reasons: tuple[str, ...] = ()


VENUE_CAPABILITY_CATALOG: dict[str, VenueCapability] = {
    "trade_xyz": VenueCapability(
        venue_id="trade_xyz",
        venue_family="trade_xyz_proxy",
        asset_universe="proxy_index_and_equity_like_perp",
        schema_enabled=True,
        strategy_lab_signal_enabled=True,
        paper_candidate_enabled=True,
        paper_intent_enabled=True,
        read_only_network_enabled=True,
        credentialed_read_only_enabled=False,
        paper_execution_enabled=True,
        live_execution_enabled=False,
        requires_credentials=False,
        external_api_default_allowed=False,
        exchange_write_default_allowed=False,
        notes=(
            "Implemented proxy/research/read-only surface.",
            "Live execution remains outside the public operator CLI.",
        ),
        block_reasons=(VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED,),
    ),
    "bitget_demo": VenueCapability(
        venue_id="bitget_demo",
        venue_family="bitget_demo",
        asset_universe="crypto_perp_fixture",
        schema_enabled=True,
        strategy_lab_signal_enabled=True,
        paper_candidate_enabled=True,
        paper_intent_enabled=True,
        read_only_network_enabled=False,
        credentialed_read_only_enabled=False,
        paper_execution_enabled=True,
        live_execution_enabled=False,
        requires_credentials=True,
        external_api_default_allowed=False,
        exchange_write_default_allowed=False,
        notes=(
            "Demo/local fixture surface.",
            "Configured credentials only prove local env presence.",
            "Production Bitget futures must use a separate venue id.",
        ),
        block_reasons=(
            VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED,
            VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED,
        ),
    ),
    "bitget_futures": VenueCapability(
        venue_id="bitget_futures",
        venue_family="bitget",
        asset_universe="crypto_perp",
        schema_enabled=False,
        strategy_lab_signal_enabled=False,
        paper_candidate_enabled=False,
        paper_intent_enabled=False,
        read_only_network_enabled=False,
        credentialed_read_only_enabled=False,
        paper_execution_enabled=False,
        live_execution_enabled=False,
        requires_credentials=True,
        external_api_default_allowed=False,
        exchange_write_default_allowed=False,
        notes=(
            "Future production Bitget futures venue.",
            "Catalog-only until schema widening and read-only smoke are approved.",
        ),
        block_reasons=(
            VENUE_CAPABILITY_SCHEMA_DISABLED,
            VENUE_CAPABILITY_STRATEGY_LAB_SIGNAL_DISABLED,
            VENUE_CAPABILITY_PAPER_CANDIDATE_DISABLED,
            VENUE_CAPABILITY_PAPER_INTENT_DISABLED,
            VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED,
            VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED,
            VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED,
        ),
    ),
    "hyperliquid_perp": VenueCapability(
        venue_id="hyperliquid_perp",
        venue_family="hyperliquid",
        asset_universe="crypto_perp",
        schema_enabled=False,
        strategy_lab_signal_enabled=False,
        paper_candidate_enabled=False,
        paper_intent_enabled=False,
        read_only_network_enabled=False,
        credentialed_read_only_enabled=False,
        paper_execution_enabled=False,
        live_execution_enabled=False,
        requires_credentials=False,
        external_api_default_allowed=False,
        exchange_write_default_allowed=False,
        notes=(
            "Future direct Hyperliquid perp venue.",
            "Do not treat Trade[XYZ] proxy code as this generic direct-perp venue.",
        ),
        block_reasons=(
            VENUE_CAPABILITY_SCHEMA_DISABLED,
            VENUE_CAPABILITY_STRATEGY_LAB_SIGNAL_DISABLED,
            VENUE_CAPABILITY_PAPER_CANDIDATE_DISABLED,
            VENUE_CAPABILITY_PAPER_INTENT_DISABLED,
            VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED,
            VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED,
            VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED,
        ),
    ),
}


def venue_capability(venue_id: str) -> VenueCapability | None:
    return VENUE_CAPABILITY_CATALOG.get(venue_id.strip().lower())


def venue_capability_block_reasons(venue_id: str) -> list[str]:
    capability = venue_capability(venue_id)
    if capability is None:
        return [VENUE_CAPABILITY_UNKNOWN]
    return list(capability.block_reasons)


def schema_enabled_venue_ids() -> tuple[str, ...]:
    return tuple(
        venue_id
        for venue_id, capability in VENUE_CAPABILITY_CATALOG.items()
        if capability.schema_enabled
    )
