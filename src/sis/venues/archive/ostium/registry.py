from __future__ import annotations

from sis.models import AssetClass, InstrumentSpec, Venue


OSTIUM_TARGETS: list[InstrumentSpec] = [
    InstrumentSpec(
        venue=Venue.OSTIUM,
        canonical_symbol="SPX_EQUIV",
        venue_symbol="requires_probe",
        asset_class=AssetClass.INDEX,
        chain="arbitrum",
        collateral="USDC",
        api_readable=True,
        api_orderable=False,
        execution_price_ref="bid_ask_or_price_after_impact",
        liquidation_price_ref="requires_probe",
        active=False,
        notes=["resolve current symbol via Builder API read-only price probe"],
    ),
    InstrumentSpec(
        venue=Venue.OSTIUM,
        canonical_symbol="NDX_EQUIV",
        venue_symbol="requires_probe",
        asset_class=AssetClass.INDEX,
        chain="arbitrum",
        collateral="USDC",
        api_readable=True,
        api_orderable=False,
        execution_price_ref="bid_ask_or_price_after_impact",
        liquidation_price_ref="requires_probe",
        active=False,
        notes=["resolve current symbol via Builder API read-only price probe"],
    ),
    InstrumentSpec(
        venue=Venue.OSTIUM,
        canonical_symbol="XAU",
        venue_symbol="requires_probe",
        asset_class=AssetClass.COMMODITY,
        chain="arbitrum",
        collateral="USDC",
        api_readable=True,
        api_orderable=False,
        execution_price_ref="bid_ask_or_price_after_impact",
        liquidation_price_ref="requires_probe",
        active=False,
        notes=["resolve current symbol via Builder API read-only price probe"],
    ),
]
