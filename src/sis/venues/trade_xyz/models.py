from __future__ import annotations

from dataclasses import dataclass

from sis.models import InstrumentSpec


@dataclass(frozen=True)
class TradeXyzAssetResolution:
    symbol: str
    coin: str
    perp_dex_index: int | None
    index_in_meta: int | None
    asset_id: int | None
    has_mid_price: bool
    excluded: bool
    api_orderable: bool


@dataclass(frozen=True)
class TradeXyzRegistryBuildResult:
    instruments: list[InstrumentSpec]
    resolutions: list[TradeXyzAssetResolution]
