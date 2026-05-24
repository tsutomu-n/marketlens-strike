from __future__ import annotations

from dataclasses import dataclass

from sis.execution.base import AdapterPositionSnapshot
from sis.paper.portfolio import PaperPosition


@dataclass(frozen=True)
class ReconciliationResult:
    matched: int
    missing_in_adapter: list[dict]
    missing_in_internal: list[dict]


def reconcile_positions(
    internal_positions: list[PaperPosition],
    adapter_positions: list[AdapterPositionSnapshot],
) -> ReconciliationResult:
    internal_map = {
        (item.venue, item.canonical_symbol, item.side): item
        for item in internal_positions
    }
    adapter_map = {
        (item.venue, item.canonical_symbol, item.side): item
        for item in adapter_positions
    }

    matched = 0
    missing_in_adapter: list[dict] = []
    missing_in_internal: list[dict] = []

    for key, internal in internal_map.items():
        adapter = adapter_map.get(key)
        if adapter is None:
            missing_in_adapter.append({"venue": key[0], "canonical_symbol": key[1], "side": key[2]})
            continue
        matched += 1
        if abs(float(internal.quantity) - float(adapter.quantity)) > 1e-9:
            missing_in_adapter.append(
                {
                    "venue": key[0],
                    "canonical_symbol": key[1],
                    "side": key[2],
                    "internal_quantity": float(internal.quantity),
                    "adapter_quantity": float(adapter.quantity),
                }
            )

    for key in adapter_map:
        if key not in internal_map:
            missing_in_internal.append({"venue": key[0], "canonical_symbol": key[1], "side": key[2]})

    return ReconciliationResult(
        matched=matched,
        missing_in_adapter=missing_in_adapter,
        missing_in_internal=missing_in_internal,
    )
