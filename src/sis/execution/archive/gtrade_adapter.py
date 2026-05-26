from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.execution.base import (
    AdapterActionResult,
    AdapterFillSnapshot,
    AdapterOrderEstimate,
    AdapterOrderStatus,
    AdapterPositionSnapshot,
    OrderIntent,
)
from sis.storage.jsonl_store import read_json


class GTradeExecutionAdapter:
    adapter_name = "gtrade"

    def __init__(
        self,
        *,
        registry_path: Path,
        balance_snapshot: dict | None = None,
        balance_snapshot_path: Path | None = None,
        positions_snapshot_path: Path | None = None,
        fills_snapshot_path: Path | None = None,
        order_status_path: Path | None = None,
    ) -> None:
        self._registry_path = registry_path
        self._balance_snapshot = balance_snapshot or {"currency": "USD", "equity": None}
        self._balance_snapshot_path = balance_snapshot_path
        self._positions_snapshot_path = positions_snapshot_path
        self._fills_snapshot_path = fills_snapshot_path
        self._order_status_path = order_status_path

    @staticmethod
    def _json_list(payload: object) -> list[dict]:
        return payload if isinstance(payload, list) else []

    @staticmethod
    def _fills_from_payload(payload: object) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            fills = payload.get("fills", [])
            return fills if isinstance(fills, list) else []
        return []

    def _registry_rows(self) -> list[dict]:
        return self._json_list(read_json(self._registry_path))

    def _order_status_rows(self) -> list[dict]:
        if self._order_status_path is None or not self._order_status_path.exists():
            return []
        return self._json_list(read_json(self._order_status_path))

    def _fill_rows(self) -> list[dict]:
        if self._fills_snapshot_path is None or not self._fills_snapshot_path.exists():
            return []
        return self._fills_from_payload(read_json(self._fills_snapshot_path))

    def read_balance(self) -> dict:
        snapshot = self._balance_snapshot
        snapshot_exists = False
        if self._balance_snapshot_path is not None and self._balance_snapshot_path.exists():
            payload = read_json(self._balance_snapshot_path)
            if isinstance(payload, dict):
                snapshot = payload
                snapshot_exists = True
        return {
            "venue": self.adapter_name,
            **snapshot,
            "balance_snapshot_exists": snapshot_exists,
            "mode": "read_only",
        }

    def read_positions(self) -> list[AdapterPositionSnapshot]:
        if self._positions_snapshot_path is None or not self._positions_snapshot_path.exists():
            return []
        frame = pl.read_parquet(self._positions_snapshot_path)
        snapshots: list[AdapterPositionSnapshot] = []
        for row in frame.to_dicts():
            if str(row.get("venue", "")).lower() != self.adapter_name:
                continue
            quantity = row.get("quantity")
            avg_entry_price = row.get("avg_entry_price")
            snapshots.append(
                AdapterPositionSnapshot(
                    venue=self.adapter_name,
                    canonical_symbol=str(row.get("canonical_symbol") or ""),
                    side=str(row.get("side") or "").lower(),
                    quantity=float(quantity) if quantity is not None else 0.0,
                    entry_price=float(avg_entry_price) if avg_entry_price is not None else None,
                    liquidation_price=None,
                )
            )
        return snapshots

    def estimate_order(self, intent: OrderIntent) -> AdapterOrderEstimate:
        matched = next(
            (
                row
                for row in self._registry_rows()
                if str(row.get("canonical_symbol")).upper() == intent.canonical_symbol.upper()
            ),
            None,
        )
        open_fee_bps = (
            float(matched.get("opening_fee_bps"))
            if matched and matched.get("opening_fee_bps") is not None
            else None
        )
        return AdapterOrderEstimate(
            venue=self.adapter_name,
            canonical_symbol=intent.canonical_symbol,
            side=intent.side,
            estimated_entry_price=None,
            estimated_cost_bps=open_fee_bps,
            price_reference="mark",
            notes=["read_only_adapter", "registry_based_estimate"],
        )

    def read_order_status(self, order_id: str) -> AdapterOrderStatus:
        matched = next(
            (row for row in self._order_status_rows() if str(row.get("order_id")) == order_id), None
        )
        if matched is None:
            return AdapterOrderStatus(
                venue=self.adapter_name,
                order_id=order_id,
                canonical_symbol=None,
                side=None,
                quantity=None,
                status="unknown_read_only",
                notes=["read_only_adapter", "no_order_status_snapshot"],
            )
        quantity = matched.get("quantity")
        return AdapterOrderStatus(
            venue=self.adapter_name,
            order_id=order_id,
            canonical_symbol=matched.get("canonical_symbol"),
            side=matched.get("side"),
            quantity=float(quantity) if quantity is not None else None,
            status=str(matched.get("status", "unknown")),
            notes=["read_only_adapter", "snapshot_status"],
        )

    def read_order_statuses(self, limit: int | None = None) -> list[AdapterOrderStatus]:
        rows = self._order_status_rows()
        if limit is not None:
            rows = rows[:limit]
        statuses: list[AdapterOrderStatus] = []
        for row in rows:
            quantity = row.get("quantity")
            statuses.append(
                AdapterOrderStatus(
                    venue=self.adapter_name,
                    order_id=str(row.get("order_id") or "unknown_order"),
                    canonical_symbol=row.get("canonical_symbol"),
                    side=row.get("side"),
                    quantity=float(quantity) if quantity is not None else None,
                    status=str(row.get("status", "unknown")),
                    notes=["read_only_adapter", "snapshot_status"],
                )
            )
        return statuses

    def read_fills(self, limit: int | None = None) -> list[AdapterFillSnapshot]:
        rows = self._fill_rows()
        if limit is not None:
            rows = rows[:limit]
        snapshots: list[AdapterFillSnapshot] = []
        for row in rows:
            quantity = row.get("quantity")
            price = row.get("price")
            snapshots.append(
                AdapterFillSnapshot(
                    venue=self.adapter_name,
                    fill_id=str(row.get("fill_id") or row.get("id") or "unknown_fill"),
                    order_id=str(row["order_id"]) if row.get("order_id") is not None else None,
                    canonical_symbol=row.get("canonical_symbol"),
                    side=row.get("side"),
                    quantity=float(quantity) if quantity is not None else None,
                    price=float(price) if price is not None else None,
                    status=str(row.get("status", "filled_snapshot")),
                    ts_fill=str(row["ts_fill"]) if row.get("ts_fill") is not None else None,
                    notes=["read_only_adapter", "snapshot_fill"],
                )
            )
        return snapshots

    def cancel_order(self, order_id: str) -> AdapterActionResult:
        return AdapterActionResult(
            venue=self.adapter_name,
            action="cancel_order",
            target=order_id,
            success=False,
            status="blocked_read_only",
            notes=["read_only_adapter", "cancel_not_available"],
        )

    def close_position(self, canonical_symbol: str, side: str | None = None) -> AdapterActionResult:
        suffix = f":{side.lower()}" if side else ""
        return AdapterActionResult(
            venue=self.adapter_name,
            action="close_position",
            target=f"{canonical_symbol.upper()}{suffix}",
            success=False,
            status="blocked_read_only",
            notes=["read_only_adapter", "close_not_available"],
        )

    def healthcheck(self) -> dict:
        return {
            "adapter": self.adapter_name,
            "registry_exists": self._registry_path.exists(),
            "balance_snapshot_exists": bool(
                self._balance_snapshot_path and self._balance_snapshot_path.exists()
            ),
            "positions_snapshot_exists": bool(
                self._positions_snapshot_path and self._positions_snapshot_path.exists()
            ),
            "fills_snapshot_exists": bool(
                self._fills_snapshot_path and self._fills_snapshot_path.exists()
            ),
            "order_status_snapshot_exists": bool(
                self._order_status_path and self._order_status_path.exists()
            ),
            "mode": "read_only",
        }
