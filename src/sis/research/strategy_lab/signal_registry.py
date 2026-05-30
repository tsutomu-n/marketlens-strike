from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import polars as pl

from sis.research.strategy_lab.specs import SymbolBinding
from sis.strategies.qqq_trend_rates_vix import build_qqq_trend_rates_vix_signals
from sis.strategies.sp500_trend_rates_vix import build_sp500_trend_rates_vix_signals

SignalGenerator = Callable[[pl.DataFrame, Any], pl.DataFrame]


@dataclass(frozen=True)
class SignalGeneratorDefinition:
    generator_id: str
    strategy_id: str
    strategy_family: str
    strategy_version: str
    symbol_bindings: tuple[SymbolBinding, ...]
    build: SignalGenerator

    def __post_init__(self) -> None:
        normalized = self.generator_id.strip()
        if not normalized:
            raise ValueError("generator_id must be non-empty")
        for field_name in ("strategy_id", "strategy_family", "strategy_version"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if not self.symbol_bindings:
            raise ValueError("symbol_bindings must be non-empty")
        object.__setattr__(self, "generator_id", normalized)


class SignalGeneratorRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, SignalGeneratorDefinition] = {}

    def register(self, definition: SignalGeneratorDefinition) -> None:
        normalized = definition.generator_id.strip()
        if not normalized:
            raise ValueError("generator_id must be non-empty")
        if normalized in self._definitions:
            raise ValueError(f"Signal generator already registered: {normalized}")
        self._definitions[normalized] = definition

    def definition(self, generator_id: str) -> SignalGeneratorDefinition:
        normalized = generator_id.strip()
        try:
            return self._definitions[normalized]
        except KeyError as exc:
            raise KeyError(f"Unknown signal generator: {normalized}") from exc

    def get(self, generator_id: str) -> SignalGenerator:
        return self.definition(generator_id).build

    def run(self, generator_id: str, frame: pl.DataFrame, spec: Any) -> pl.DataFrame:
        return self.definition(generator_id).build(frame, spec)

    def registered_ids(self) -> list[str]:
        return sorted(self._definitions)


def default_signal_generator_registry() -> SignalGeneratorRegistry:
    registry = SignalGeneratorRegistry()
    registry.register(
        SignalGeneratorDefinition(
            generator_id="qqq_trend_rates_vix",
            strategy_id="equity_index_momentum_v0",
            strategy_family="momentum",
            strategy_version="v0",
            symbol_bindings=(
                SymbolBinding(
                    execution_venue="trade_xyz",
                    execution_symbol="XYZ100",
                    real_market_symbol="QQQ",
                    asset_class="basket_index",
                ),
            ),
            build=lambda frame, _spec: build_qqq_trend_rates_vix_signals(frame),
        )
    )
    registry.register(
        SignalGeneratorDefinition(
            generator_id="sp500_trend_rates_vix",
            strategy_id="sp500_index_momentum_v0",
            strategy_family="momentum",
            strategy_version="v0",
            symbol_bindings=(
                SymbolBinding(
                    execution_venue="trade_xyz",
                    execution_symbol="SP500",
                    real_market_symbol="SPY",
                    asset_class="index",
                ),
            ),
            build=lambda frame, _spec: build_sp500_trend_rates_vix_signals(frame),
        )
    )
    return registry
