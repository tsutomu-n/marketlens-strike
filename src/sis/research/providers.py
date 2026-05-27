from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from urllib.request import urlopen

import polars as pl


@dataclass(frozen=True)
class ResearchFetchRequest:
    symbols: list[str]
    start: date
    end: date
    interval: str


class PriceProvider:
    name: str

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        raise NotImplementedError


class MacroProvider:
    name: str

    def fetch_series(self, series_ids: list[str], start: date, end: date) -> pl.DataFrame:
        raise NotImplementedError


def _normalize_price_frame(frame: pl.DataFrame, provider: str) -> pl.DataFrame:
    required = {"ts", "symbol", "open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Price provider output missing columns: {sorted(missing)}")

    available = set(frame.columns)
    value_columns = [name for name in ("open", "high", "low", "close") if name in available]
    normalized = frame.with_columns(
        pl.col("ts").cast(pl.Datetime(time_unit="us", time_zone="UTC")),
        pl.col("symbol").cast(pl.Utf8).str.to_uppercase(),
        *(pl.col(name).cast(pl.Float64) for name in value_columns),
        pl.lit(provider).alias("provider"),
        pl.when(pl.col("provider_symbol").is_null())
        .then(pl.col("symbol"))
        .otherwise(pl.col("provider_symbol"))
        .alias("provider_symbol")
        if "provider_symbol" in available
        else pl.col("symbol").alias("provider_symbol"),
        pl.lit("none").alias("adjustment")
        if "adjustment" not in available
        else pl.col("adjustment").cast(pl.Utf8),
        pl.lit("").alias("interval")
        if "interval" not in available
        else pl.col("interval").cast(pl.Utf8),
        pl.lit(None).cast(pl.Float64).alias("volume")
        if "volume" not in available
        else pl.col("volume").cast(pl.Float64),
    )
    return normalized.select(
        "ts",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "provider",
        "provider_symbol",
        "interval",
        "adjustment",
    )


def _normalize_macro_frame(frame: pl.DataFrame, provider: str) -> pl.DataFrame:
    required = {"date", "series_id", "value"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Macro provider output missing columns: {sorted(missing)}")

    available = set(frame.columns)
    normalized = frame.with_columns(
        pl.col("date").cast(pl.Date),
        pl.col("series_id").cast(pl.Utf8),
        pl.col("value").cast(pl.Float64),
        pl.lit(provider).alias("provider"),
        pl.lit("latest").alias("vintage_mode")
        if "vintage_mode" not in available
        else pl.col("vintage_mode").cast(pl.Utf8),
        pl.lit(None).cast(pl.Date).alias("realtime_start")
        if "realtime_start" not in available
        else pl.col("realtime_start").cast(pl.Date),
        pl.lit(None).cast(pl.Date).alias("realtime_end")
        if "realtime_end" not in available
        else pl.col("realtime_end").cast(pl.Date),
    )
    return normalized.select(
        "date",
        "series_id",
        "value",
        "provider",
        "vintage_mode",
        "realtime_start",
        "realtime_end",
    )


class YahooFinancePriceProvider(PriceProvider):
    name = "yfinance"

    def __init__(self, downloader: Callable[..., Any] | None = None) -> None:
        if downloader is None:
            try:
                import yfinance as yf
            except ImportError as exc:
                raise RuntimeError("yfinance is required for YahooFinancePriceProvider") from exc
            downloader = yf.download
        self._downloader = downloader

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        for symbol in request.symbols:
            raw = self._downloader(
                symbol,
                start=request.start.isoformat(),
                end=request.end.isoformat(),
                interval=request.interval,
                auto_adjust=False,
                progress=False,
            )
            if raw is None or getattr(raw, "empty", False):
                continue
            if getattr(raw.columns, "nlevels", 1) > 1:
                raw = raw.copy()
                raw.columns = [
                    item[0] if isinstance(item, tuple) and item else item
                    for item in raw.columns.to_list()
                ]
            pandas_frame = raw.reset_index()
            renamed = pandas_frame.rename(
                columns={
                    "index": "ts",
                    "Datetime": "ts",
                    "Date": "ts",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )
            frame = pl.from_pandas(renamed).with_columns(
                pl.lit(symbol.upper()).alias("symbol"),
                pl.lit(symbol).alias("provider_symbol"),
                pl.lit(request.interval).alias("interval"),
                pl.lit("none").alias("adjustment"),
            )
            frames.append(frame)
        if not frames:
            return pl.DataFrame(schema={"ts": pl.Datetime(time_zone="UTC"), "symbol": pl.Utf8})
        return _normalize_price_frame(pl.concat(frames, how="vertical_relaxed"), self.name)


class YahooQueryPriceProvider(PriceProvider):
    name = "yahooquery"

    def __init__(self, ticker_factory: Callable[..., Any] | None = None) -> None:
        if ticker_factory is None:
            try:
                from yahooquery import Ticker
            except ImportError as exc:
                raise RuntimeError("yahooquery is required for YahooQueryPriceProvider") from exc
            ticker_factory = Ticker
        self._ticker_factory = ticker_factory

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        ticker = self._ticker_factory(request.symbols, asynchronous=False)
        history = ticker.history(
            start=request.start.isoformat(), end=request.end.isoformat(), interval=request.interval
        )
        if history is None or getattr(history, "empty", False):
            return pl.DataFrame(schema={"ts": pl.Datetime(time_zone="UTC"), "symbol": pl.Utf8})
        pandas_frame = history.reset_index().rename(
            columns={
                "symbol": "provider_symbol",
                "date": "ts",
            }
        )
        frame = pl.from_pandas(pandas_frame).with_columns(
            pl.col("provider_symbol").cast(pl.Utf8).str.to_uppercase().alias("symbol"),
            pl.lit(request.interval).alias("interval"),
            pl.lit("none").alias("adjustment"),
        )
        return _normalize_price_frame(frame, self.name)


class FredMacroProvider(MacroProvider):
    name = "fredapi"

    def __init__(
        self, api_key: str | None = None, fred_factory: Callable[..., Any] | None = None
    ) -> None:
        if fred_factory is None:
            try:
                from fredapi import Fred
            except ImportError as exc:
                raise RuntimeError("fredapi is required for FredMacroProvider") from exc
            fred_factory = Fred
        self._fred = fred_factory(api_key=api_key) if api_key else fred_factory()

    def fetch_series(self, series_ids: list[str], start: date, end: date) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        for series_id in series_ids:
            series = self._fred.get_series(series_id, observation_start=start, observation_end=end)
            if series is None or getattr(series, "empty", False):
                continue
            pandas_frame = series.rename("value").reset_index().rename(columns={"index": "date"})
            frame = pl.from_pandas(pandas_frame).with_columns(
                pl.lit(series_id).alias("series_id"),
                pl.lit("latest").alias("vintage_mode"),
                pl.lit(None).cast(pl.Date).alias("realtime_start"),
                pl.lit(None).cast(pl.Date).alias("realtime_end"),
            )
            frames.append(frame)
        if not frames:
            return pl.DataFrame(schema={"date": pl.Date, "series_id": pl.Utf8, "value": pl.Float64})
        return _normalize_macro_frame(pl.concat(frames, how="vertical_relaxed"), self.name)


class FredGraphCsvMacroProvider(MacroProvider):
    name = "fredgraph_csv"

    def fetch_series(self, series_ids: list[str], start: date, end: date) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        for series_id in series_ids:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            with urlopen(url, timeout=20) as response:
                frame = pl.read_csv(response)
            if "observation_date" not in frame.columns or series_id not in frame.columns:
                continue
            frame = (
                frame.rename({"observation_date": "date", series_id: "value"})
                .with_columns(
                    pl.col("date").str.strptime(pl.Date, "%Y-%m-%d", strict=False),
                    pl.col("value").cast(pl.Float64, strict=False),
                    pl.lit(series_id).alias("series_id"),
                    pl.lit("latest").alias("vintage_mode"),
                    pl.lit(None).cast(pl.Date).alias("realtime_start"),
                    pl.lit(None).cast(pl.Date).alias("realtime_end"),
                )
                .filter(pl.col("date").is_between(start, end), pl.col("value").is_not_null())
            )
            frames.append(frame)
        if not frames:
            return pl.DataFrame(schema={"date": pl.Date, "series_id": pl.Utf8, "value": pl.Float64})
        return _normalize_macro_frame(pl.concat(frames, how="vertical_relaxed"), self.name)


class PandasDataReaderMacroProvider(MacroProvider):
    name = "pandas_datareader"

    def __init__(self, reader: Callable[..., Any] | None = None) -> None:
        if reader is None:
            try:
                from pandas_datareader import data as web
            except ImportError as exc:
                raise RuntimeError(
                    "pandas-datareader is required for PandasDataReaderMacroProvider"
                ) from exc
            reader = web.DataReader
        self._reader = reader

    def fetch_series(self, series_ids: list[str], start: date, end: date) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        for series_id in series_ids:
            raw = self._reader(series_id, "fred", start, end)
            if raw is None or getattr(raw, "empty", False):
                continue
            pandas_frame = raw.reset_index().rename(
                columns={"DATE": "date", "Date": "date", series_id: "value"}
            )
            frame = pl.from_pandas(pandas_frame).with_columns(
                pl.lit(series_id).alias("series_id"),
                pl.lit("latest").alias("vintage_mode"),
                pl.lit(None).cast(pl.Date).alias("realtime_start"),
                pl.lit(None).cast(pl.Date).alias("realtime_end"),
            )
            frames.append(frame)
        if not frames:
            return pl.DataFrame(schema={"date": pl.Date, "series_id": pl.Utf8, "value": pl.Float64})
        return _normalize_macro_frame(pl.concat(frames, how="vertical_relaxed"), self.name)
