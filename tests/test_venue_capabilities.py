from __future__ import annotations

import json
from pathlib import Path

from sis.venues.capabilities import VENUE_CAPABILITY_CATALOG
from sis.venues.capabilities import VENUE_CAPABILITY_EVALUATION_PLAN_DISABLED
from sis.venues.capabilities import (
    VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED,
    VENUE_CAPABILITY_PAPER_EXECUTION_DISABLED,
    VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED,
    VENUE_CAPABILITY_SCHEMA_DISABLED,
    evaluation_plan_enabled_venue_ids,
    schema_enabled_venue_ids,
    venue_capability,
    venue_capability_block_reasons,
)
from sis.venues.ids import VENUE_IDS
from sis.venues.suitability import VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION
from sis.venues.suitability import VENUE_SUITABILITY_CATALOG
from sis.venues.suitability import venue_suitability_block_reasons


def test_schema_enabled_capabilities_match_current_venue_ids() -> None:
    assert schema_enabled_venue_ids() == VENUE_IDS


def test_capability_catalog_matches_suitability_catalog_keys() -> None:
    assert set(VENUE_CAPABILITY_CATALOG) == set(VENUE_SUITABILITY_CATALOG)


def test_schema_enabled_capabilities_match_strategy_lab_execution_venue_schemas() -> None:
    expected = list(schema_enabled_venue_ids())

    for schema_name in (
        "strategy_signal.v1.schema.json",
        "trade_candidate.v1.schema.json",
        "paper_intent_preview.v1.schema.json",
    ):
        payload = json.loads(Path("schemas", schema_name).read_text(encoding="utf-8"))
        assert payload["properties"]["execution_venue"]["enum"] == expected


def test_evaluation_plan_capability_matches_schema_const() -> None:
    payload = json.loads(
        Path("schemas/evaluation_plan.mls.v1.schema.json").read_text(encoding="utf-8")
    )

    assert evaluation_plan_enabled_venue_ids() == (payload["properties"]["target_venue"]["const"],)


def test_bitget_demo_is_demo_only_and_non_writing() -> None:
    capability = venue_capability("bitget_demo")

    assert capability is not None
    assert capability.schema_enabled is True
    assert capability.strategy_lab_evaluation_plan_enabled is False
    assert capability.venue_family == "bitget_demo"
    assert capability.requires_credentials is True
    assert capability.read_only_network_enabled is False
    assert capability.credentialed_read_only_enabled is False
    assert capability.external_api_default_allowed is False
    assert capability.exchange_write_default_allowed is False
    assert capability.live_execution_enabled is False
    assert VENUE_CAPABILITY_EVALUATION_PLAN_DISABLED in capability.block_reasons
    assert VENUE_CAPABILITY_READ_ONLY_NETWORK_DISABLED in capability.block_reasons
    assert VENUE_CAPABILITY_LIVE_EXECUTION_DISABLED in capability.block_reasons


def test_future_venues_are_known_but_schema_disabled() -> None:
    for venue_id in ("bitget_futures", "hyperliquid_perp"):
        capability = venue_capability(venue_id)

        assert capability is not None
        assert capability.schema_enabled is False
        assert capability.strategy_lab_signal_enabled is False
        assert capability.strategy_lab_evaluation_plan_enabled is False
        assert capability.paper_candidate_enabled is False
        assert capability.paper_intent_enabled is False
        assert capability.paper_execution_enabled is False
        assert capability.live_execution_enabled is False
        assert capability.external_api_default_allowed is False
        assert capability.exchange_write_default_allowed is False
        assert VENUE_CAPABILITY_SCHEMA_DISABLED in capability.block_reasons
        assert VENUE_CAPABILITY_EVALUATION_PLAN_DISABLED in capability.block_reasons
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
