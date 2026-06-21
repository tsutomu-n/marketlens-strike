from __future__ import annotations

from decimal import Decimal
from typing import Literal
import zlib

from pydantic import BaseModel, ConfigDict

from sis.crypto_perp.models import decimal_to_json_string


BookInvalidReason = Literal["CHECKSUM_FAILURE", "SEQUENCE_GAP"]


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


class BitgetOrderBook:
    def __init__(self, *, native_symbol: str, channel: str) -> None:
        self.native_symbol = native_symbol
        self.channel = channel
        self.valid = True
        self.invalid_reason: BookInvalidReason | None = None
        self.last_seq: int | None = None
        self.bids: list[list[str]] = []
        self.asks: list[list[str]] = []

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
        if action == "update" and self.last_seq is not None and seq != self.last_seq + 1:
            return self._invalidate("SEQUENCE_GAP")
        self.bids = sorted(bids, key=lambda item: Decimal(item[0]), reverse=True)
        self.asks = sorted(asks, key=lambda item: Decimal(item[0]))
        self.last_seq = seq
        if checksum not in {None, 0}:
            actual = bitget_signed_crc32(checksum_payload(self.bids, self.asks))
            if actual != checksum:
                return self._invalidate("CHECKSUM_FAILURE")
        self.valid = True
        self.invalid_reason = None
        best_bid: tuple[str, str] | None = (self.bids[0][0], self.bids[0][1]) if self.bids else None
        best_ask: tuple[str, str] | None = (self.asks[0][0], self.asks[0][1]) if self.asks else None
        spread = _spread_bps(best_bid, best_ask) if best_bid and best_ask else None
        return BookApplyResult(
            valid=True,
            best_bid=best_bid,
            best_ask=best_ask,
            spread_bps=spread,
        )
