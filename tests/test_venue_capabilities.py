from __future__ import annotations

from sis.venues.capabilities import (
    VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED,
    VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED,
    VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED,
    VENUE_CAPABILITY_SCHEMA_DISABLED,
    schema_enabled_venue_ids,
    venue_capability,
    venue_capability_block_reasons,
)
from sis.venues.ids import VENUE_IDS
from sis.venues.suitability import VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION
from sis.venues.suitability import venue_suitability_block_reasons


def test_schema_enabled_capabilities_match_current_venue_ids() -> None:
    assert schema_enabled_venue_ids() == VENUE_IDS


def test_bitget_demo_is_demo_only_and_non_writing() -> None:
    capability = venue_capability("bitget_demo")

    assert capability is not None
    assert capability.schema_enabled is True
    assert capability.venue_family == "bitget_demo"
    assert capability.requires_credentials is True
    assert capability.read_only_network_enabled is False
    assert capability.credentialed_read_only_enabled is False
    assert capability.external_api_default_allowed is False
    assert capability.exchange_write_default_allowed is False
    assert capability.live_execution_enabled is False
    assert VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED in capability.block_reasons
    assert VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED in capability.block_reasons


def test_future_venues_are_known_but_schema_disabled() -> None:
    for venue_id in ("bitget_futures", "hyperliquid_perp"):
        capability = venue_capability(venue_id)

        assert capability is not None
        assert capability.schema_enabled is False
        assert capability.strategy_lab_signal_enabled is False
        assert capability.paper_candidate_enabled is False
        assert capability.paper_intent_enabled is False
        assert capability.paper_execution_enabled is False
        assert capability.live_execution_enabled is False
        assert capability.external_api_default_allowed is False
        assert capability.exchange_write_default_allowed is False
        assert VENUE_CAPABILITY_SCHEMA_DISABLED in capability.block_reasons
        assert VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED in capability.block_reasons
        assert VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED in capability.block_reasons


def test_hyperliquid_direct_perp_does_not_imply_trade_xyz_surface() -> None:
    capability = venue_capability("hyperliquid_perp")

    assert capability is not None
    assert capability.venue_family == "hyperliquid"
    assert capability.asset_universe == "crypto_perp"
    assert all("Trade[XYZ] proxy" in note for note in capability.notes[-1:])


def test_unknown_venue_fails_closed() -> None:
    assert venue_capability("missing_venue") is None
    assert venue_capability_block_reasons("missing_venue") == ["VENUE_CAPABILITY_UNKNOWN"]


def test_ndx_qqq_paper_path_remains_blocked_for_trade_xyz() -> None:
    reasons = venue_suitability_block_reasons(
        venue_id="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        stage="paper_candidate",
    )

    assert VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION in reasons
