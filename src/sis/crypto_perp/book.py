from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal
import zlib

from pydantic import BaseModel, ConfigDict

from sis.crypto_perp.models import decimal_to_json_string

BookInvalidReason = Literal[
    "CHECKSUM_FAILURE",
    "SEQUENCE_GAP",
    "UPDATE_BEFORE_SNAPSHOT",
    "INVALID_LEVEL",
    "CROSSED_BOOK",
]


class BookApplyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    invalid_reason: BookInvalidReason | None = None
    best_bid: tuple[str, str] | None = None
    best_ask: tuple[str, str] | None = None
    spread_bps: str | None = None


def checksum_payload(
    bids: list[list[str]],
    asks: list[list[str]],
    *,
    depth: int = 25,
) -> str:
    parts: list[str] = []
    for index in range(max(len(bids[:depth]), len(asks[:depth]))):
        if index < len(bids[:depth]):
            parts.extend([str(bids[index][0]), str(bids[index][1])])
        if index < len(asks[:depth]):
            parts.extend([str(asks[index][0]), str(asks[index][1])])
    return ":".join(parts)


def bitget_signed_crc32(payload: str) -> int:
    checksum = zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF
    if checksum >= 2**31:
        checksum -= 2**32
    return checksum


def _spread_bps(best_bid: tuple[str, str], best_ask: tuple[str, str]) -> str:
    bid = Decimal(best_bid[0])
    ask = Decimal(best_ask[0])
    mid = (bid + ask) / Decimal("2")
    if mid == 0:
        return "0"
    return decimal_to_json_string((ask - bid) / mid * Decimal("10000"))


def _validate_levels(levels: list[list[str]], *, allow_zero: bool) -> bool:
    for level in levels:
        if len(level) < 2:
            return False
        try:
            price = Decimal(str(level[0]))
            quantity = Decimal(str(level[1]))
        except (InvalidOperation, ValueError):
            return False
        if price <= 0 or quantity < 0 or (not allow_zero and quantity == 0):
            return False
    return True


def _sorted_levels(levels: dict[str, str], *, reverse: bool) -> list[list[str]]:
    return [
        [price, quantity]
        for price, quantity in sorted(
            levels.items(),
            key=lambda item: Decimal(item[0]),
            reverse=reverse,
        )
    ]


def _snapshot_levels(levels: list[list[str]], *, reverse: bool) -> list[list[str]]:
    by_price = {
        str(price): str(quantity)
        for price, quantity in levels
        if Decimal(str(quantity)) > 0
    }
    return _sorted_levels(by_price, reverse=reverse)


def _merge_levels(
    current: list[list[str]],
    updates: list[list[str]],
    *,
    reverse: bool,
) -> list[list[str]]:
    levels = {str(price): str(quantity) for price, quantity in current}
    for price, quantity in updates:
        normalized_price = str(price)
        normalized_quantity = str(quantity)
        if Decimal(normalized_quantity) == 0:
            levels.pop(normalized_price, None)
        else:
            levels[normalized_price] = normalized_quantity
    return _sorted_levels(levels, reverse=reverse)


class BitgetOrderBook:
    def __init__(self, *, native_symbol: str, channel: str) -> None:
        self.native_symbol = native_symbol
        self.channel = channel
        self.valid = True
        self.invalid_reason: BookInvalidReason | None = None
        self.last_seq: int | None = None
        self.bids: list[list[str]] = []
        self.asks: list[list[str]] = []
        self.has_snapshot = False

    def _invalidate(self, reason: BookInvalidReason) -> BookApplyResult:
        self.valid = False
        self.invalid_reason = reason
        return BookApplyResult(valid=False, invalid_reason=reason)

    def apply_depth(
        self,
        *,
        action: str,
        bids: list[list[str]],
        asks: list[list[str]],
        seq: int,
        checksum: int | None,
        ts_event_ms: int,
    ) -> BookApplyResult:
        _ = ts_event_ms
        normalized_action = action.strip().lower()
        snapshot_channel = self.channel in {"books1", "books5", "books15"}
        is_snapshot = normalized_action == "snapshot" or snapshot_channel
        if not _validate_levels(bids, allow_zero=not is_snapshot):
            return self._invalidate("INVALID_LEVEL")
        if not _validate_levels(asks, allow_zero=not is_snapshot):
            return self._invalidate("INVALID_LEVEL")
        if not is_snapshot and not self.has_snapshot:
            return self._invalidate("UPDATE_BEFORE_SNAPSHOT")
        if not self.valid and not is_snapshot:
            return BookApplyResult(valid=False, invalid_reason=self.invalid_reason)
        if (
            not is_snapshot
            and self.last_seq is not None
            and seq > 0
            and seq != self.last_seq + 1
        ):
            return self._invalidate("SEQUENCE_GAP")

        if is_snapshot:
            self.bids = _snapshot_levels(bids, reverse=True)
            self.asks = _snapshot_levels(asks, reverse=False)
            self.has_snapshot = True
        else:
            self.bids = _merge_levels(self.bids, bids, reverse=True)
            self.asks = _merge_levels(self.asks, asks, reverse=False)
        self.last_seq = seq if seq > 0 else self.last_seq

        best_bid: tuple[str, str] | None = (
            (self.bids[0][0], self.bids[0][1]) if self.bids else None
        )
        best_ask: tuple[str, str] | None = (
            (self.asks[0][0], self.asks[0][1]) if self.asks else None
        )
        if best_bid and best_ask and Decimal(best_bid[0]) >= Decimal(best_ask[0]):
            return self._invalidate("CROSSED_BOOK")
        if checksum not in {None, 0}:
            actual = bitget_signed_crc32(checksum_payload(self.bids, self.asks))
            if actual != checksum:
                return self._invalidate("CHECKSUM_FAILURE")
        self.valid = True
        self.invalid_reason = None
        spread = _spread_bps(best_bid, best_ask) if best_bid and best_ask else None
        return BookApplyResult(
            valid=True,
            best_bid=best_bid,
            best_ask=best_ask,
            spread_bps=spread,
        )
