from __future__ import annotations

from pathlib import Path

from sis.execution.base import AdapterOrderEstimate, AdapterPositionSnapshot, OrderIntent
from sis.storage.jsonl_store import read_json


class GTradeExecutionAdapter:
    adapter_name = "gtrade"

    def __init__(self, *, registry_path: Path, balance_snapshot: dict | None = None) -> None:
        self._registry_path = registry_path
        self._balance_snapshot = balance_snapshot or {"currency": "USD", "equity": None}

    def _registry_rows(self) -> list[dict]:
        payload = read_json(self._registry_path)
        return payload if isinstance(payload, list) else []

    def read_balance(self) -> dict:
        return {"venue": self.adapter_name, **self._balance_snapshot}

    def read_positions(self) -> list[AdapterPositionSnapshot]:
        return []

    def estimate_order(self, intent: OrderIntent) -> AdapterOrderEstimate:
        matched = next(
            (row for row in self._registry_rows() if str(row.get("canonical_symbol")).upper() == intent.canonical_symbol.upper()),
            None,
        )
        open_fee_bps = float(matched.get("opening_fee_bps")) if matched and matched.get("opening_fee_bps") is not None else None
        return AdapterOrderEstimate(
            venue=self.adapter_name,
            canonical_symbol=intent.canonical_symbol,
            side=intent.side,
            estimated_entry_price=None,
            estimated_cost_bps=open_fee_bps,
            price_reference="mark",
            notes=["read_only_adapter", "registry_based_estimate"],
        )

    def healthcheck(self) -> dict:
        return {
            "adapter": self.adapter_name,
            "registry_exists": self._registry_path.exists(),
            "mode": "read_only",
        }
