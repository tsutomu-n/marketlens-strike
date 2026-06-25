from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.build_row_context import (
    _row_symbol_binding,
)
from sis.research.strategy_lab.specs import SymbolBinding


def _binding(symbol: str = "AAPL") -> SymbolBinding:
    return SymbolBinding(
        execution_venue="bitget_demo",
        execution_symbol=symbol,
        real_market_symbol=symbol,
        asset_class="equity",
    )


def _spec(*, multi_leg_enabled: bool = False, anchor: str = "AAPL") -> SimpleNamespace:
    return SimpleNamespace(
        rules=SimpleNamespace(
            multi_leg=SimpleNamespace(
                enabled=multi_leg_enabled,
                anchor_real_market_symbol=anchor,
            )
        )
    )


def test_row_symbol_binding_uppercases_canonical_symbol() -> None:
    binding = _binding("AAPL")

    result = _row_symbol_binding(
        row={"canonical_symbol": "aapl"},
        spec=_spec(),
        bindings={"AAPL": binding},
    )

    assert result == ("AAPL", binding)


def test_row_symbol_binding_skips_missing_binding() -> None:
    assert (
        _row_symbol_binding(
            row={"canonical_symbol": "MSFT"},
            spec=_spec(),
            bindings={},
        )
        is None
    )


def test_row_symbol_binding_skips_non_anchor_multi_leg_rows() -> None:
    anchor_binding = _binding("AAPL")
    hedge_binding = _binding("MSFT")
    spec = _spec(multi_leg_enabled=True, anchor="AAPL")

    assert (
        _row_symbol_binding(
            row={"canonical_symbol": "MSFT"},
            spec=spec,
            bindings={"AAPL": anchor_binding, "MSFT": hedge_binding},
        )
        is None
    )
    assert _row_symbol_binding(
        row={"canonical_symbol": "aapl"},
        spec=spec,
        bindings={"AAPL": anchor_binding, "MSFT": hedge_binding},
    ) == ("AAPL", anchor_binding)
