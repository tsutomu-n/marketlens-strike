from __future__ import annotations

from sis.models import AssetClass, InstrumentSpec, Venue


GTRADE_TARGETS: list[InstrumentSpec] = [
    InstrumentSpec(
        venue=Venue.GTRADE,
        canonical_symbol="SPY",
        venue_symbol="SPY/USD",
        pair_index=86,
        asset_class=AssetClass.INDEX,
        chain=["arbitrum", "base", "solana"],
        collateral="requires_live_probe",
        api_readable=True,
        api_orderable=True,
        execution_price_ref="mark",
        liquidation_price_ref="index",
        active=True,
        notes=["indices session", "closed session open/close/edit unavailable"],
    ),
    InstrumentSpec(
        venue=Venue.GTRADE,
        canonical_symbol="QQQ",
        venue_symbol="QQQ/USD",
        pair_index=87,
        asset_class=AssetClass.INDEX,
        chain=["arbitrum", "base", "solana"],
        collateral="requires_live_probe",
        api_readable=True,
        api_orderable=True,
        execution_price_ref="mark",
        liquidation_price_ref="index",
        active=True,
        notes=["indices session", "closed session open/close/edit unavailable"],
    ),
    InstrumentSpec(
        venue=Venue.GTRADE,
        canonical_symbol="XAU",
        venue_symbol="XAU/USD",
        pair_index=90,
        asset_class=AssetClass.COMMODITY,
        chain="requires_live_probe",
        collateral="requires_live_probe",
        api_readable=True,
        api_orderable=True,
        execution_price_ref="mark",
        liquidation_price_ref="index",
        active=True,
        notes=["commodity session", "daily maintenance break"],
    ),
]

