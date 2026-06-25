from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.specs import SymbolBinding


def _row_symbol_binding(
    *,
    row: dict[str, Any],
    spec: Any,
    bindings: dict[str, SymbolBinding],
) -> tuple[str, SymbolBinding] | None:
    symbol = str(row.get("canonical_symbol") or "").upper()
    if spec.rules.multi_leg.enabled and symbol != spec.rules.multi_leg.anchor_real_market_symbol:
        return None
    binding = bindings.get(symbol)
    if binding is None:
        return None
    return symbol, binding
