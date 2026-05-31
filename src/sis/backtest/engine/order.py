from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: uuid4().hex)
    client_order_id: str | None = None
    created_ts: datetime
    symbol: str
    side: Literal["buy", "sell"]
    position_effect: Literal["open", "close"]
    order_type: Literal["market_like"] = "market_like"
    requested_notional_usd: float = Field(gt=0)
    requested_qty: float | None = Field(default=None, gt=0)
    limit_price: None = None
    reduce_only: bool = False
    strategy_id: str
    signal_id: str | None = None

    @model_validator(mode="after")
    def validate_order(self) -> Order:
        if not self.order_id.strip():
            raise ValueError("order_id must be non-empty")
        self.symbol = self.symbol.strip().upper()
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if not self.strategy_id.strip():
            raise ValueError("strategy_id must be non-empty")
        if self.position_effect == "close" and not self.reduce_only:
            raise ValueError("close orders must be reduce_only")
        return self
