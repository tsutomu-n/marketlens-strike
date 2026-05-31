from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FillPriceSource = Literal[
    "exec_buy_price",
    "exec_sell_price",
    "best_ask",
    "best_bid",
    "fill_best_ask",
    "fill_best_bid",
    "ask_price",
    "bid_price",
    "mid_plus_half_spread",
    "mid_minus_half_spread",
    "fill_mid_plus_half_spread",
    "fill_mid_minus_half_spread",
]


class Fill(BaseModel):
    fill_id: str
    order_id: str
    event_ts: datetime
    symbol: str
    side: Literal["buy", "sell"]
    position_effect: Literal["open", "close"]
    qty: float = Field(gt=0)
    fill_price: float = Field(gt=0)
    fill_notional_usd: float = Field(gt=0)
    fee_bps: float = Field(ge=0)
    fee_amount: float = Field(ge=0)
    fee_source: str = "unknown"
    extra_slippage_bps: float = Field(ge=0)
    extra_slippage_amount: float = Field(ge=0)
    funding_amount_delta: float = 0.0
    liquidity_flag: Literal["taker"] = "taker"
    fill_price_source: FillPriceSource

    @model_validator(mode="after")
    def validate_fill(self) -> Fill:
        if not self.fill_id.strip():
            raise ValueError("fill_id must be non-empty")
        if not self.order_id.strip():
            raise ValueError("order_id must be non-empty")
        self.symbol = self.symbol.strip().upper()
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        expected_notional = self.qty * self.fill_price
        if abs(self.fill_notional_usd - expected_notional) > 1e-9:
            raise ValueError("fill_notional_usd must equal qty * fill_price")
        return self


def _positive_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed > 0 else None


def resolve_market_like_fill_price(
    row: dict[str, object], *, side: Literal["buy", "sell"]
) -> tuple[float | None, FillPriceSource | None]:
    if side == "buy":
        for source in ("exec_buy_price", "fill_best_ask", "best_ask", "ask_price"):
            price = _positive_float(row.get(source))
            if price is not None:
                return price, source
        mid = _positive_float(row.get("fill_mid_price")) or _positive_float(row.get("mid_price"))
        spread_bps = _positive_float(row.get("fill_spread_bps")) or _positive_float(
            row.get("spread_bps")
        )
        if mid is not None and spread_bps is not None:
            source = (
                "fill_mid_plus_half_spread"
                if row.get("fill_mid_price") is not None
                else "mid_plus_half_spread"
            )
            return mid * (1 + spread_bps / 20_000), source
        return None, None

    for source in ("exec_sell_price", "fill_best_bid", "best_bid", "bid_price"):
        price = _positive_float(row.get(source))
        if price is not None:
            return price, source
    mid = _positive_float(row.get("fill_mid_price")) or _positive_float(row.get("mid_price"))
    spread_bps = _positive_float(row.get("fill_spread_bps")) or _positive_float(
        row.get("spread_bps")
    )
    if mid is not None and spread_bps is not None:
        source = (
            "fill_mid_minus_half_spread"
            if row.get("fill_mid_price") is not None
            else "mid_minus_half_spread"
        )
        return mid * (1 - spread_bps / 20_000), source
    return None, None


def next_fill_row_index(*, signal_row_index: int, row_count: int) -> int | None:
    candidate = signal_row_index + 1
    return candidate if candidate < row_count else None
