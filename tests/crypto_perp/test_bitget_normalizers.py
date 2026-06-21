from __future__ import annotations

import json
from pathlib import Path

import pytest

from sis.crypto_perp.bitget.normalizers import (
    normalize_candles,
    normalize_funding_history,
    normalize_instruments,
    normalize_open_interest,
    normalize_tickers,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures/crypto_perp/bitget/public"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_normalize_instruments_keeps_futures_metadata() -> None:
    rows = normalize_instruments(_fixture("instruments.json"))

    assert rows[0]["native_symbol"] == "BTCUSDT"
    assert rows[0]["status"] == "online"
    assert rows[0]["maker_fee_rate"] == "0.0002"
    assert rows[0]["funding_interval_hours"] == "8"


def test_normalize_tickers_keeps_quote_fields_as_strings() -> None:
    rows = normalize_tickers(_fixture("tickers.json"))

    assert rows[0]["last_price"] == "90216.3"
    assert rows[0]["bid1_price"] == "90216.3"
    assert rows[0]["open_interest_raw"] == "27606.0718"


def test_normalize_candles_preserves_ohlcv_order() -> None:
    rows = normalize_candles(_fixture("candles.json"), candle_type="market", interval="15m")

    assert rows[0]["ts_open"] == "1687708800000"
    assert rows[0]["open"] == "27176.93"
    assert rows[0]["quote_turnover"] == "81246917.3294"
    assert rows[0]["candle_type"] == "market"


def test_normalize_open_interest_and_funding_history() -> None:
    oi_rows = normalize_open_interest(_fixture("open_interest.json"))
    funding_rows = normalize_funding_history(_fixture("funding_history.json"))

    assert oi_rows == [
        {
            "native_symbol": "BTCUSDT",
            "open_interest_raw": "2243.019",
            "ts_event": "1730969652411",
        }
    ]
    assert funding_rows[0]["funding_rate"] == "0.0001"


def test_normalizers_reject_wrong_shape() -> None:
    with pytest.raises(ValueError):
        normalize_instruments({"code": "00000", "data": {"not": "a-list"}})
