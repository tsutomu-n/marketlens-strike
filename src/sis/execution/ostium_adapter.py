from __future__ import annotations

from pathlib import Path

from sis.execution.base import AdapterOrderEstimate, AdapterPositionSnapshot, OrderIntent
from sis.storage.jsonl_store import read_json
from sis.venues.ostium.positions import latest_positions_sidecar


class OstiumExecutionAdapter:
    adapter_name = "ostium"

    def __init__(self, *, registry_path: Path, positions_root: Path, balance_snapshot: dict | None = None) -> None:
        self._registry_path = registry_path
        self._positions_root = positions_root
        self._balance_snapshot = balance_snapshot or {"currency": "USD", "equity": None}

    def _registry_rows(self) -> list[dict]:
        payload = read_json(self._registry_path)
        return payload if isinstance(payload, list) else []

    def read_balance(self) -> dict:
        return {"venue": self.adapter_name, **self._balance_snapshot}

    def read_positions(self) -> list[AdapterPositionSnapshot]:
        path = latest_positions_sidecar(self._positions_root)
        if path is None:
            return []
        payload = read_json(path)
        positions = payload.get("positions", []) if isinstance(payload, dict) else []
        snapshots: list[AdapterPositionSnapshot] = []
        for item in positions:
            venue_symbol = str(item.get("venue_symbol", ""))
            matched = next((row for row in self._registry_rows() if row.get("venue_symbol") == venue_symbol), None)
            snapshots.append(
                AdapterPositionSnapshot(
                    venue=self.adapter_name,
                    canonical_symbol=str((matched or {}).get("canonical_symbol") or venue_symbol),
                    side=str(item.get("side", "long")).lower(),
                    quantity=float(item.get("size", 1.0) or 1.0),
                    entry_price=float(item["entry_px"]) if item.get("entry_px") is not None else None,
                    liquidation_price=float(item["liquidation_px"]) if item.get("liquidation_px") is not None else None,
                )
            )
        return snapshots

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
            price_reference="bid_ask_or_price_after_impact",
            notes=["read_only_adapter", "registry_based_estimate"],
        )

    def healthcheck(self) -> dict:
        return {
            "adapter": self.adapter_name,
            "registry_exists": self._registry_path.exists(),
            "positions_root_exists": self._positions_root.exists(),
            "mode": "read_only",
        }
