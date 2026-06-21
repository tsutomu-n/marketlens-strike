from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/crypto_perp/tardis"
SCRIPT_PATH = REPO_ROOT / "scripts/download_tardis_bitget_fixture.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("download_tardis_bitget_fixture", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tardis_trade_vwap_golden_fixture() -> None:
    tardis = _load_script()
    trades = tardis.load_trades(FIXTURE_ROOT / tardis.DEFAULT_TRADES)

    assert [trade.trade_id for trade in trades] == ["t1", "t2", "t3"]
    assert tardis.trade_vwap(trades) == Decimal("100.25")


def test_tardis_incremental_book_reconstruction_golden_fixture() -> None:
    tardis = _load_script()
    updates = tardis.load_book_updates(FIXTURE_ROOT / tardis.DEFAULT_BOOK)
    book = tardis.reconstruct_book(updates)

    assert len(updates) == 8
    assert book.best_bid == Decimal("100.5")
    assert book.best_ask == Decimal("101.5")
    assert Decimal("100") not in book.bids
    assert Decimal("101") not in book.asks


def test_tardis_derivative_ticker_and_summary_golden_fixture() -> None:
    tardis = _load_script()
    tickers = tardis.load_derivative_tickers(FIXTURE_ROOT / tardis.DEFAULT_TICKER)
    summary = tardis.build_summary(FIXTURE_ROOT)

    assert tickers[-1].funding_rate == Decimal("0.0002")
    assert summary == {
        "exchange": "bitget-futures",
        "symbol": "BTCUSDT",
        "trade_count": 3,
        "trade_vwap": "100.25",
        "book_update_count": 8,
        "best_bid": "100.5",
        "best_ask": "101.5",
        "ticker_count": 2,
        "funding_rate": "0.0002",
        "open_interest": "12355",
        "mark_price": "100.4",
        "index_price": "100.3",
    }
