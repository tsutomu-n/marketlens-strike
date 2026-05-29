from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import find_dotenv, load_dotenv

from sis.real_market.models import RealMarketBar

ALPACA_DATA_BASE_URL = "https://data.alpaca.markets"
ALPACA_CREDENTIAL_ENV_KEYS = (
    ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY"),
    ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
    ("SIS_ALPACA_API_KEY", "SIS_ALPACA_SECRET_KEY"),
)


class AlpacaProviderUnavailable(RuntimeError):
    pass


class AlpacaNoBarsReturned(AlpacaProviderUnavailable):
    pass


def _credentials(
    api_key: str | None,
    api_secret: str | None,
) -> tuple[str, str]:
    if api_key and api_secret:
        return api_key, api_secret
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)
    for key_name, secret_name in ALPACA_CREDENTIAL_ENV_KEYS:
        key = os.getenv(key_name)
        secret = os.getenv(secret_name)
        if key and secret:
            return key, secret
    raise AlpacaProviderUnavailable(
        "Alpaca credentials are not configured. Set APCA_API_KEY_ID/APCA_API_SECRET_KEY "
        "or pass api_key/api_secret."
    )


def _alpaca_timeframe(timeframe: str) -> str:
    normalized = timeframe.strip()
    mapping = {
        "1m": "1Min",
        "5m": "5Min",
        "15m": "15Min",
        "1h": "1Hour",
        "1d": "1Day",
    }
    return mapping.get(normalized.lower(), normalized)


def _parse_ts(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Alpaca bar timestamp must be a string")
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _bar_duration_seconds(timeframe: str) -> int:
    normalized = timeframe.lower()
    if normalized.endswith("min"):
        return int(normalized.removesuffix("min")) * 60
    if normalized.endswith("hour"):
        return int(normalized.removesuffix("hour")) * 3600
    if normalized.endswith("day"):
        return int(normalized.removesuffix("day")) * 86_400
    return 0


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid price")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise ValueError("value must be numeric")


def _bars_for_symbol(payload: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    bars = payload.get("bars")
    if isinstance(bars, dict):
        symbol_rows = bars.get(symbol)
        if isinstance(symbol_rows, dict):
            return [symbol_rows]
        return (
            [row for row in symbol_rows if isinstance(row, dict)]
            if isinstance(symbol_rows, list)
            else []
        )
    if isinstance(bars, list):
        return [row for row in bars if isinstance(row, dict)]
    return []


def _write_raw_payload(
    path: Path,
    *,
    request_url: str,
    symbol: str,
    timeframe: str,
    feed: str,
    row_count: int,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "provider": "alpaca",
                "request_url": request_url,
                "symbol": symbol,
                "timeframe": timeframe,
                "feed": feed,
                "row_count": row_count,
                "payload": payload,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def fetch_alpaca_bars(
    *,
    symbol: str,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
    feed: str = "iex",
    api_key: str | None = None,
    api_secret: str | None = None,
    base_url: str = ALPACA_DATA_BASE_URL,
    timeout: float = 10.0,
    opener: Callable[..., Any] = urlopen,
    raw_payload_path: Path | None = None,
) -> list[RealMarketBar]:
    key, secret = _credentials(api_key, api_secret)
    alpaca_timeframe = _alpaca_timeframe(timeframe)
    params: dict[str, str | int] = {
        "symbols": symbol,
        "timeframe": alpaca_timeframe,
        "limit": max(1, limit),
        "feed": feed,
    }
    if start is not None:
        params["start"] = start.isoformat()
    if end is not None:
        params["end"] = end.isoformat()
    url = f"{base_url.rstrip('/')}/v2/stocks/bars?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
    )

    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise AlpacaProviderUnavailable(f"Alpaca bars request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise AlpacaProviderUnavailable("Alpaca bars response was not a JSON object")

    duration_seconds = _bar_duration_seconds(alpaca_timeframe)
    now = datetime.now(timezone.utc)
    raw_ref = str(raw_payload_path) if raw_payload_path is not None else None
    rows: list[RealMarketBar] = []
    for item in _bars_for_symbol(payload, symbol):
        ts_start = _parse_ts(item.get("t"))
        ts_end = (
            datetime.fromtimestamp(ts_start.timestamp() + duration_seconds, tz=timezone.utc)
            if duration_seconds
            else ts_start
        )
        rows.append(
            RealMarketBar(
                ts_start=ts_start,
                ts_end=ts_end,
                symbol=symbol,
                timeframe=timeframe,
                open=_as_float(item.get("o")),
                high=_as_float(item.get("h")),
                low=_as_float(item.get("l")),
                close=_as_float(item.get("c")),
                volume=_as_float(item.get("v")) if item.get("v") is not None else None,
                source="alpaca",
                delay_seconds=max((now - ts_end).total_seconds(), 0.0),
                raw_payload_ref=raw_ref,
            )
        )

    if raw_payload_path is not None:
        _write_raw_payload(
            raw_payload_path,
            request_url=url,
            symbol=symbol,
            timeframe=timeframe,
            feed=feed,
            row_count=len(rows),
            payload=payload,
        )
    if not rows:
        raise AlpacaNoBarsReturned(f"Alpaca returned no bars for {symbol} {timeframe}")
    return rows


def fetch_alpaca_latest_bar(
    *,
    symbol: str,
    feed: str = "iex",
    api_key: str | None = None,
    api_secret: str | None = None,
    base_url: str = ALPACA_DATA_BASE_URL,
    timeout: float = 10.0,
    opener: Callable[..., Any] = urlopen,
    raw_payload_path: Path | None = None,
) -> list[RealMarketBar]:
    key, secret = _credentials(api_key, api_secret)
    params: dict[str, str] = {
        "symbols": symbol,
        "feed": feed,
    }
    url = f"{base_url.rstrip('/')}/v2/stocks/bars/latest?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
    )

    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise AlpacaProviderUnavailable(f"Alpaca latest bar request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise AlpacaProviderUnavailable("Alpaca latest bar response was not a JSON object")

    now = datetime.now(timezone.utc)
    raw_ref = str(raw_payload_path) if raw_payload_path is not None else None
    rows: list[RealMarketBar] = []
    for item in _bars_for_symbol(payload, symbol):
        ts_start = _parse_ts(item.get("t"))
        ts_end = datetime.fromtimestamp(ts_start.timestamp() + 60, tz=timezone.utc)
        rows.append(
            RealMarketBar(
                ts_start=ts_start,
                ts_end=ts_end,
                symbol=symbol,
                timeframe="1m",
                open=_as_float(item.get("o")),
                high=_as_float(item.get("h")),
                low=_as_float(item.get("l")),
                close=_as_float(item.get("c")),
                volume=_as_float(item.get("v")) if item.get("v") is not None else None,
                source="alpaca",
                delay_seconds=max((now - ts_end).total_seconds(), 0.0),
                raw_payload_ref=raw_ref,
            )
        )

    if raw_payload_path is not None:
        _write_raw_payload(
            raw_payload_path,
            request_url=url,
            symbol=symbol,
            timeframe="1m",
            feed=feed,
            row_count=len(rows),
            payload=payload,
        )
    if not rows:
        raise AlpacaNoBarsReturned(f"Alpaca returned no latest bar for {symbol}")
    return rows
