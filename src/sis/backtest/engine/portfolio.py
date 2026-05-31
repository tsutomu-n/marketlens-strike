from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from sis.backtest.engine.fill import Fill


class Portfolio(BaseModel):
    initial_cash_usd: float = Field(gt=0)
    cash_usd: float
    position_qty: float = Field(ge=0)
    avg_entry_price: float = Field(ge=0)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    fees_paid: float = 0.0
    slippage_paid: float = 0.0
    funding_pnl: float = 0.0
    equity: float
    open_entry_fees: float = 0.0
    open_entry_slippage: float = 0.0

    @classmethod
    def flat(cls, *, initial_cash_usd: float) -> Portfolio:
        return cls(
            initial_cash_usd=initial_cash_usd,
            cash_usd=initial_cash_usd,
            position_qty=0.0,
            avg_entry_price=0.0,
            equity=initial_cash_usd,
        )

    @model_validator(mode="after")
    def validate_portfolio(self) -> Portfolio:
        if self.position_qty == 0 and self.avg_entry_price != 0:
            raise ValueError("flat portfolio must have avg_entry_price=0")
        if self.position_qty > 0 and self.avg_entry_price <= 0:
            raise ValueError("open portfolio must have avg_entry_price > 0")
        if self.fees_paid < 0:
            raise ValueError("fees_paid must be >= 0")
        if self.slippage_paid < 0:
            raise ValueError("slippage_paid must be >= 0")
        return self

    def apply_fill(self, fill: Fill) -> Portfolio:
        if fill.position_effect == "open":
            return self._apply_open(fill)
        return self._apply_close(fill)

    def apply_funding(self, amount: float) -> Portfolio:
        cash_usd = self.cash_usd + amount
        funding_pnl = self.funding_pnl + amount
        equity = cash_usd + self.position_qty * self.avg_entry_price
        return self.model_copy(
            update={
                "cash_usd": cash_usd,
                "funding_pnl": funding_pnl,
                "equity": equity,
            }
        )

    def _apply_open(self, fill: Fill) -> Portfolio:
        if fill.side != "buy":
            raise ValueError("long-only portfolio only supports buy/open fills")
        total_qty = self.position_qty + fill.qty
        avg_entry_price = (
            (self.avg_entry_price * self.position_qty) + fill.fill_notional_usd
        ) / total_qty
        cash_usd = self.cash_usd - fill.fill_notional_usd - fill.fee_amount
        cash_usd -= fill.extra_slippage_amount
        fees_paid = self.fees_paid + fill.fee_amount
        slippage_paid = self.slippage_paid + fill.extra_slippage_amount
        funding_pnl = self.funding_pnl + fill.funding_amount_delta
        equity = cash_usd + total_qty * fill.fill_price
        return self.model_copy(
            update={
                "cash_usd": cash_usd,
                "position_qty": total_qty,
                "avg_entry_price": avg_entry_price,
                "unrealized_pnl": (fill.fill_price - avg_entry_price) * total_qty,
                "fees_paid": fees_paid,
                "slippage_paid": slippage_paid,
                "funding_pnl": funding_pnl,
                "equity": equity,
                "open_entry_fees": self.open_entry_fees + fill.fee_amount,
                "open_entry_slippage": self.open_entry_slippage + fill.extra_slippage_amount,
            }
        )

    def _apply_close(self, fill: Fill) -> Portfolio:
        if fill.side != "sell":
            raise ValueError("long-only portfolio only supports sell/close fills")
        if fill.qty > self.position_qty + 1e-12:
            raise ValueError("close quantity exceeds open position")
        if self.position_qty <= 0:
            raise ValueError("cannot close when flat")

        close_fraction = fill.qty / self.position_qty
        entry_fees = self.open_entry_fees * close_fraction
        entry_slippage = self.open_entry_slippage * close_fraction
        gross_pnl = (fill.fill_price - self.avg_entry_price) * fill.qty
        net_realized_delta = (
            gross_pnl
            - entry_fees
            - entry_slippage
            - fill.fee_amount
            - fill.extra_slippage_amount
            + fill.funding_amount_delta
        )
        remaining_qty = self.position_qty - fill.qty
        remaining_entry_fees = self.open_entry_fees - entry_fees
        remaining_entry_slippage = self.open_entry_slippage - entry_slippage
        cash_usd = self.cash_usd + fill.fill_notional_usd - fill.fee_amount
        cash_usd -= fill.extra_slippage_amount
        fees_paid = self.fees_paid + fill.fee_amount
        slippage_paid = self.slippage_paid + fill.extra_slippage_amount
        funding_pnl = self.funding_pnl + fill.funding_amount_delta
        avg_entry_price = self.avg_entry_price if remaining_qty > 1e-12 else 0.0
        unrealized_pnl = (
            (fill.fill_price - avg_entry_price) * remaining_qty if remaining_qty > 1e-12 else 0.0
        )
        equity = cash_usd + remaining_qty * fill.fill_price
        return self.model_copy(
            update={
                "cash_usd": cash_usd,
                "position_qty": max(remaining_qty, 0.0),
                "avg_entry_price": avg_entry_price,
                "realized_pnl": self.realized_pnl + net_realized_delta,
                "unrealized_pnl": unrealized_pnl,
                "fees_paid": fees_paid,
                "slippage_paid": slippage_paid,
                "funding_pnl": funding_pnl,
                "equity": equity,
                "open_entry_fees": remaining_entry_fees if remaining_qty > 1e-12 else 0.0,
                "open_entry_slippage": remaining_entry_slippage if remaining_qty > 1e-12 else 0.0,
            }
        )
