from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.signal_registry import (
    SignalGeneratorRegistry,
    default_signal_generator_registry,
)
from sis.research.strategy_lab.specs import SymbolBinding


def test_signal_generator_registry_fails_closed_for_unknown_generator() -> None:
    registry = SignalGeneratorRegistry()

    with pytest.raises(KeyError, match="unknown_generator"):
        registry.get("unknown_generator")


def test_signal_generator_registry_runs_registered_generator() -> None:
    registry = SignalGeneratorRegistry()
    registry.register("demo", lambda frame, spec: frame.with_columns(pl.lit("demo").alias("kind")))

    result = registry.run("demo", pl.DataFrame({"value": [1]}), spec={"id": "demo"})

    assert result.get_column("kind").to_list() == ["demo"]


def test_default_signal_generator_registry_includes_known_generators() -> None:
    registry = default_signal_generator_registry()

    assert registry.registered_ids() == ["qqq_trend_rates_vix", "sp500_trend_rates_vix"]


def test_strategy_signal_frame_requires_binding_columns() -> None:
    frame = pl.DataFrame(
        {
            "schema_version": ["strategy_signal.v1"],
            "signal_id": ["sig-001"],
            "generated_at": [datetime.now(timezone.utc)],
            "strategy_id": ["equity_index_momentum_v0"],
            "strategy_family": ["momentum"],
            "strategy_version": ["v0"],
            "ts_signal": [datetime.now(timezone.utc)],
            "timeframe": ["4h"],
            "execution_venue": ["trade_xyz"],
            "execution_symbol": ["XYZ100"],
            "side": ["long"],
            "confidence": [0.8],
            "tail_bucket": ["top"],
        }
    )

    with pytest.raises(ValueError, match="real_market_symbol"):
        validate_strategy_signal_frame(frame, symbol_bindings=[])


def test_strategy_signal_frame_requires_known_symbol_binding() -> None:
    now = datetime.now(timezone.utc)
    frame = pl.DataFrame(
        {
            "schema_version": ["strategy_signal.v1"],
            "signal_id": ["sig-001"],
            "generated_at": [now],
            "strategy_id": ["equity_index_momentum_v0"],
            "strategy_family": ["momentum"],
            "strategy_version": ["v0"],
            "ts_signal": [now],
            "timeframe": ["4h"],
            "execution_venue": ["trade_xyz"],
            "execution_symbol": ["XYZ100"],
            "real_market_symbol": ["QQQ"],
            "side": ["long"],
            "confidence": [0.8],
            "tail_bucket": ["top"],
        }
    )

    with pytest.raises(ValueError, match="SymbolBinding"):
        validate_strategy_signal_frame(
            frame,
            symbol_bindings=[
                SymbolBinding(
                    execution_venue="trade_xyz",
                    execution_symbol="SP500",
                    real_market_symbol="SPY",
                    asset_class="index",
                )
            ],
        )


def test_strategy_signal_frame_accepts_bound_records() -> None:
    now = datetime.now(timezone.utc)
    frame = pl.DataFrame(
        {
            "schema_version": ["strategy_signal.v1"],
            "signal_id": ["sig-001"],
            "generated_at": [now],
            "strategy_id": ["equity_index_momentum_v0"],
            "strategy_family": ["momentum"],
            "strategy_version": ["v0"],
            "ts_signal": [now],
            "timeframe": ["4h"],
            "execution_venue": ["trade_xyz"],
            "execution_symbol": ["XYZ100"],
            "real_market_symbol": ["QQQ"],
            "side": ["long"],
            "confidence": [0.8],
            "tail_bucket": ["top"],
        }
    )

    validated = validate_strategy_signal_frame(
        frame,
        symbol_bindings=[
            SymbolBinding(
                execution_venue="trade_xyz",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                asset_class="basket_index",
            )
        ],
    )

    assert validated.height == 1
