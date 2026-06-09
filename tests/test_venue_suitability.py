from __future__ import annotations

from sis.venues.suitability import (
    VENUE_ASSET_UNIVERSE_MISMATCH,
    VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT,
    VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION,
    assess_venue_suitability,
    venue_suitability_block_reasons,
)


def test_trade_xyz_ndx_qqq_is_research_only_until_residual_validation() -> None:
    research = assess_venue_suitability(
        venue_id="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        stage="research",
    )
    paper = assess_venue_suitability(
        venue_id="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        stage="paper_candidate",
    )

    assert research.allowed is True
    assert paper.allowed is False
    assert VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION in paper.reason_codes


def test_sp500_spy_trade_xyz_can_remain_existing_paper_fixture_path() -> None:
    reasons = venue_suitability_block_reasons(
        venue_id="trade_xyz",
        execution_symbol="SP500",
        real_market_symbol="SPY",
        stage="paper_intent",
    )

    assert reasons == []


def test_bitget_demo_rejects_ndx_qqq_but_accepts_crypto_fixture() -> None:
    ndx_reasons = venue_suitability_block_reasons(
        venue_id="bitget_demo",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        stage="paper_candidate",
    )
    crypto_reasons = venue_suitability_block_reasons(
        venue_id="bitget_demo",
        execution_symbol="BTCUSDT",
        real_market_symbol="BTCUSDT",
        stage="paper_candidate",
    )

    assert VENUE_ASSET_UNIVERSE_MISMATCH in ndx_reasons
    assert crypto_reasons == []


def test_future_direct_venues_are_catalog_only_not_operator_enabled() -> None:
    for venue_id in ("bitget_futures", "hyperliquid_perp"):
        reasons = venue_suitability_block_reasons(
            venue_id=venue_id,
            execution_symbol="BTCUSDT",
            real_market_symbol="BTCUSDT",
            stage="paper_candidate",
        )
        assert VENUE_NOT_ENABLED_FOR_OPERATOR_CONTEXT in reasons
