from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _data_list(payload: Mapping[str, Any]) -> list[Any]:
    if payload.get("code") != "00000":
        raise ValueError("Bitget response code is not success")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("Bitget response data must be a list")
    return data


def _data_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if payload.get("code") != "00000":
        raise ValueError("Bitget response code is not success")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ValueError("Bitget response data must be an object")
    return data


def _row_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("Bitget row must be an object")
    return value


def _text(row: Mapping[str, Any], key: str) -> str:
    if key not in row:
        raise ValueError(f"missing Bitget field: {key}")
    return str(row[key])


def _optional_text(row: Mapping[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    return str(value)


def _first_text(row: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _optional_text(row, key)
        if value is not None:
            return value
    return None


def normalize_instruments(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _data_list(payload):
        row = _row_mapping(item)
        rows.append(
            {
                "native_symbol": _text(row, "symbol"),
                "canonical_symbol": _text(row, "symbol"),
                "base_asset": _text(row, "baseCoin"),
                "quote_asset": _text(row, "quoteCoin"),
                "type": _text(row, "type"),
                "status": _text(row, "status"),
                "launch_time": _text(row, "launchTime"),
                "off_time": _text(row, "offTime"),
                "limit_open_time": _text(row, "limitOpenTime"),
                "maker_fee_rate": _text(row, "makerFeeRate"),
                "taker_fee_rate": _text(row, "takerFeeRate"),
                "price_precision": _text(row, "pricePrecision"),
                "quantity_precision": _text(row, "quantityPrecision"),
                "price_multiplier": _text(row, "priceMultiplier"),
                "quantity_multiplier": _text(row, "quantityMultiplier"),
                "min_order_qty": _text(row, "minOrderQty"),
                "min_order_amount": _text(row, "minOrderAmount"),
                "max_market_order_qty": _text(row, "maxMarketOrderQty"),
                "min_leverage": _text(row, "minLeverage"),
                "max_leverage": _text(row, "maxLeverage"),
                "funding_interval_hours": _text(row, "fundInterval"),
            }
        )
    return rows


def normalize_mix_contracts(
    payload: Mapping[str, Any], *, product_type: str
) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for item in _data_list(payload):
        row = _row_mapping(item)
        symbol = _text(row, "symbol")
        rows.append(
            {
                "symbol": symbol,
                "product_type": _optional_text(row, "productType") or product_type,
                "base_coin": _optional_text(row, "baseCoin"),
                "quote_coin": _optional_text(row, "quoteCoin"),
                "symbol_type": _optional_text(row, "symbolType"),
                "symbol_status": _optional_text(row, "symbolStatus"),
                "min_trade_usdt": _optional_text(row, "minTradeUSDT"),
                "max_lever": _optional_text(row, "maxLever"),
                "is_rwa": _optional_text(row, "isRwa"),
            }
        )
    return rows


def normalize_mix_tickers(payload: Mapping[str, Any]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for item in _data_list(payload):
        row = _row_mapping(item)
        rows.append(
            {
                "symbol": _text(row, "symbol"),
                "ts": _optional_text(row, "ts"),
                "last_price": _first_text(row, ("lastPr", "lastPrice")),
                "bid_price": _first_text(row, ("bidPr", "bid1Price")),
                "ask_price": _first_text(row, ("askPr", "ask1Price")),
                "bid_size": _first_text(row, ("bidSz", "bid1Size")),
                "ask_size": _first_text(row, ("askSz", "ask1Size")),
                "change_24h": _first_text(row, ("change24h", "price24hPcnt")),
                "base_volume_24h": _first_text(row, ("baseVolume", "volume24h")),
                "quote_volume_24h": _first_text(row, ("quoteVolume", "turnover24h")),
                "usdt_volume_24h": _first_text(
                    row,
                    ("usdtVolume", "quoteVolume", "turnover24h"),
                ),
                "index_price": _optional_text(row, "indexPrice"),
                "mark_price": _optional_text(row, "markPrice"),
                "funding_rate": _optional_text(row, "fundingRate"),
                "next_funding_time_ms": _first_text(row, ("nextFundingTime", "fundingTime")),
                "holding_amount": _first_text(row, ("holdingAmount", "openInterest")),
            }
        )
    return rows


def normalize_mix_history_candles(
    payload: Mapping[str, Any],
    *,
    symbol: str,
    granularity: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _data_list(payload):
        if not isinstance(item, Sequence) or isinstance(item, str) or len(item) < 7:
            raise ValueError("Bitget history candle row must be a sequence with at least 7 fields")
        rows.append(
            {
                "symbol": symbol,
                "ts": str(item[0]),
                "open": str(item[1]),
                "high": str(item[2]),
                "low": str(item[3]),
                "close": str(item[4]),
                "base_vol": str(item[5]),
                "quote_vol": str(item[6]),
                "granularity": granularity,
            }
        )
    return rows


def normalize_tickers(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _data_list(payload):
        row = _row_mapping(item)
        rows.append(
            {
                "native_symbol": _text(row, "symbol"),
                "ts_event": _text(row, "ts"),
                "last_price": _text(row, "lastPrice"),
                "bid1_price": _text(row, "bid1Price"),
                "ask1_price": _text(row, "ask1Price"),
                "bid1_size": _text(row, "bid1Size"),
                "ask1_size": _text(row, "ask1Size"),
                "price_change_24h": _text(row, "price24hPcnt"),
                "volume_24h_base": _text(row, "volume24h"),
                "turnover_24h_quote": _text(row, "turnover24h"),
                "index_price": _text(row, "indexPrice"),
                "mark_price": _text(row, "markPrice"),
                "funding_rate": _text(row, "fundingRate"),
                "open_interest_raw": _text(row, "openInterest"),
            }
        )
    return rows


def normalize_candles(
    payload: Mapping[str, Any],
    *,
    candle_type: str,
    interval: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _data_list(payload):
        if not isinstance(item, Sequence) or isinstance(item, str) or len(item) < 7:
            raise ValueError("Bitget candle row must be a sequence with at least 7 fields")
        rows.append(
            {
                "ts_open": str(item[0]),
                "open": str(item[1]),
                "high": str(item[2]),
                "low": str(item[3]),
                "close": str(item[4]),
                "base_volume": str(item[5]),
                "quote_turnover": str(item[6]),
                "candle_type": candle_type,
                "interval": interval,
            }
        )
    return rows


def normalize_open_interest(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    data = _data_mapping(payload)
    raw_rows = data.get("list")
    if not isinstance(raw_rows, list):
        raise ValueError("Bitget open-interest data.list must be a list")
    ts_event = _text(data, "ts")
    rows: list[dict[str, str]] = []
    for item in raw_rows:
        row = _row_mapping(item)
        rows.append(
            {
                "native_symbol": _text(row, "symbol"),
                "open_interest_raw": _text(row, "openInterest"),
                "ts_event": ts_event,
            }
        )
    return rows


def normalize_funding_history(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    data = _data_mapping(payload)
    raw_rows = data.get("resultList")
    if not isinstance(raw_rows, list):
        raise ValueError("Bitget funding-history data.resultList must be a list")
    rows: list[dict[str, str]] = []
    for item in raw_rows:
        row = _row_mapping(item)
        rows.append(
            {
                "native_symbol": _text(row, "symbol"),
                "funding_rate": _text(row, "fundingRate"),
                "ts_event": _text(row, "fundingRateTimestamp"),
            }
        )
    return rows
