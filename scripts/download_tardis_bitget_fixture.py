#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal


DEFAULT_TRADES = "bitget_futures_BTCUSDT_2024-12-01_trades.csv"
DEFAULT_BOOK = "bitget_futures_BTCUSDT_2024-12-01_incremental_book_L2.csv"
DEFAULT_TICKER = "bitget_futures_BTCUSDT_2024-12-01_derivative_ticker.csv"


@dataclass(frozen=True)
class TardisTrade:
    exchange: str
    symbol: str
    timestamp: int
    local_timestamp: int
    trade_id: str
    side: Literal["buy", "sell"]
    price: Decimal
    amount: Decimal


@dataclass(frozen=True)
class TardisBookUpdate:
    exchange: str
    symbol: str
    timestamp: int
    local_timestamp: int
    is_snapshot: bool
    side: Literal["bid", "ask"]
    price: Decimal
    amount: Decimal


@dataclass(frozen=True)
class TardisDerivativeTicker:
    exchange: str
    symbol: str
    timestamp: int
    local_timestamp: int
    funding_rate: Decimal
    open_interest: Decimal
    mark_price: Decimal
    index_price: Decimal


@dataclass
class L2Book:
    bids: dict[Decimal, Decimal]
    asks: dict[Decimal, Decimal]

    def apply(self, update: TardisBookUpdate) -> None:
        levels = self.bids if update.side == "bid" else self.asks
        if update.amount == 0:
            levels.pop(update.price, None)
            return
        levels[update.price] = update.amount

    @property
    def best_bid(self) -> Decimal | None:
        return max(self.bids) if self.bids else None

    @property
    def best_ask(self) -> Decimal | None:
        return min(self.asks) if self.asks else None


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)
        return
    with path.open("r", encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def _side(value: str) -> Literal["buy", "sell"]:
    if value not in {"buy", "sell"}:
        raise ValueError(f"unsupported trade side: {value}")
    return value


def _book_side(value: str) -> Literal["bid", "ask"]:
    if value not in {"bid", "ask"}:
        raise ValueError(f"unsupported book side: {value}")
    return value


def _snapshot(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"unsupported is_snapshot value: {value}")


def load_trades(path: Path) -> list[TardisTrade]:
    return [
        TardisTrade(
            exchange=row["exchange"],
            symbol=row["symbol"],
            timestamp=int(row["timestamp"]),
            local_timestamp=int(row["local_timestamp"]),
            trade_id=row["id"],
            side=_side(row["side"]),
            price=Decimal(row["price"]),
            amount=Decimal(row["amount"]),
        )
        for row in _read_csv(path)
    ]


def load_book_updates(path: Path) -> list[TardisBookUpdate]:
    return [
        TardisBookUpdate(
            exchange=row["exchange"],
            symbol=row["symbol"],
            timestamp=int(row["timestamp"]),
            local_timestamp=int(row["local_timestamp"]),
            is_snapshot=_snapshot(row["is_snapshot"]),
            side=_book_side(row["side"]),
            price=Decimal(row["price"]),
            amount=Decimal(row["amount"]),
        )
        for row in _read_csv(path)
    ]


def load_derivative_tickers(path: Path) -> list[TardisDerivativeTicker]:
    return [
        TardisDerivativeTicker(
            exchange=row["exchange"],
            symbol=row["symbol"],
            timestamp=int(row["timestamp"]),
            local_timestamp=int(row["local_timestamp"]),
            funding_rate=Decimal(row["funding_rate"]),
            open_interest=Decimal(row["open_interest"]),
            mark_price=Decimal(row["mark_price"]),
            index_price=Decimal(row["index_price"]),
        )
        for row in _read_csv(path)
    ]


def trade_vwap(trades: Sequence[TardisTrade]) -> Decimal:
    amount = sum((trade.amount for trade in trades), Decimal("0"))
    if amount <= 0:
        raise ValueError("trade amount must be positive")
    notional = sum((trade.price * trade.amount for trade in trades), Decimal("0"))
    return notional / amount


def reconstruct_book(updates: Sequence[TardisBookUpdate]) -> L2Book:
    book = L2Book(bids={}, asks={})
    active_snapshot_timestamp: int | None = None
    for update in updates:
        if update.is_snapshot:
            if active_snapshot_timestamp != update.local_timestamp:
                book.bids.clear()
                book.asks.clear()
                active_snapshot_timestamp = update.local_timestamp
        else:
            active_snapshot_timestamp = None
        book.apply(update)
    return book


def fixture_paths(root: Path) -> dict[str, Path]:
    return {
        "trades": root / DEFAULT_TRADES,
        "book": root / DEFAULT_BOOK,
        "ticker": root / DEFAULT_TICKER,
    }


def build_summary(root: Path) -> dict[str, Any]:
    paths = fixture_paths(root)
    trades = load_trades(paths["trades"])
    updates = load_book_updates(paths["book"])
    tickers = load_derivative_tickers(paths["ticker"])
    book = reconstruct_book(updates)
    if book.best_bid is None or book.best_ask is None:
        raise ValueError("book reconstruction did not produce both bid and ask")
    if not tickers:
        raise ValueError("derivative ticker fixture is empty")
    last_ticker = tickers[-1]
    return {
        "exchange": trades[0].exchange if trades else "",
        "symbol": trades[0].symbol if trades else "",
        "trade_count": len(trades),
        "trade_vwap": _decimal_string(trade_vwap(trades)),
        "book_update_count": len(updates),
        "best_bid": _decimal_string(book.best_bid),
        "best_ask": _decimal_string(book.best_ask),
        "ticker_count": len(tickers),
        "funding_rate": _decimal_string(last_ticker.funding_rate),
        "open_interest": _decimal_string(last_ticker.open_interest),
        "mark_price": _decimal_string(last_ticker.mark_price),
        "index_price": _decimal_string(last_ticker.index_price),
    }


def download_url(url: str, out: Path) -> None:
    import httpx

    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        with out.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download explicit Tardis CSV URLs or summarize a local Bitget fixture."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download", help="download one explicit URL")
    download.add_argument("--url", required=True)
    download.add_argument("--out", type=Path, required=True)
    summarize = subparsers.add_parser("summarize", help="summarize a local fixture directory")
    summarize.add_argument("--root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "download":
        download_url(args.url, args.out)
        return 0
    if args.command == "summarize":
        print(json.dumps(build_summary(args.root), ensure_ascii=False, sort_keys=True))
        return 0
    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
