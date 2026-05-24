from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import polars as pl

from sis.research.event_calendar import build_event_calendar
from sis.research.feature_panel import build_feature_panel
from sis.research.macro_ingest import build_macro_panel
from sis.research.price_ingest import build_market_panel
from sis.research.providers import MacroProvider, PriceProvider, ResearchFetchRequest
from sis.research.research_quality import build_research_quality_report
from sis.research.signal_builder import build_signals


class FakePriceProvider(PriceProvider):
    name = "fake_price"

    def fetch_ohlcv(self, request: ResearchFetchRequest) -> pl.DataFrame:
        rows: list[dict] = []
        start_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        symbols = ["QQQ", "SPY", "GLD", "^VIX", "UUP", "USDJPY=X", "EURUSD=X"]
        for symbol_index, symbol in enumerate(symbols):
            for day_index in range(8):
                close = 100.0 + symbol_index * 10 + day_index
                if symbol == "QQQ":
                    close = 100.0 + day_index * 2
                if symbol == "^VIX":
                    close = 20.0 + day_index
                if symbol == "UUP":
                    close = 30.0 + day_index * 0.5
                rows.append(
                    {
                        "ts": start_ts + timedelta(days=day_index),
                        "symbol": symbol,
                        "open": close - 0.5,
                        "high": close + 1.0,
                        "low": close - 1.0,
                        "close": close,
                        "volume": 1_000 + day_index,
                        "provider_symbol": symbol,
                        "interval": request.interval,
                        "adjustment": "none",
                    }
                )
        return pl.DataFrame(rows)


class FakeMacroProvider(MacroProvider):
    name = "fake_macro"

    def fetch_series(self, series_ids: list[str], start: date, end: date) -> pl.DataFrame:
        rows: list[dict] = []
        for day_index in range(8):
            current = date(2026, 1, 1) + timedelta(days=day_index)
            for series_id, value in {
                "DGS10": 4.0 + day_index * 0.1,
                "DGS2": 3.0 + day_index * 0.05,
                "T10Y2Y": 1.0 + day_index * 0.02,
                "FEDFUNDS": 5.0,
            }.items():
                rows.append(
                    {
                        "date": current,
                        "series_id": series_id,
                        "value": value,
                        "provider": self.name,
                        "vintage_mode": "latest",
                        "realtime_start": None,
                        "realtime_end": None,
                    }
                )
        return pl.DataFrame(rows)


def test_research_pipeline_builds_reproducible_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    market_panel = build_market_panel(data_dir, provider=FakePriceProvider())
    macro_panel = build_macro_panel(data_dir, provider=FakeMacroProvider())

    event_csv = data_dir / "research/event_calendar.csv"
    event_csv.parent.mkdir(parents=True, exist_ok=True)
    event_csv.write_text(
        "event_ts,event_name,event_class,importance,before_minutes,after_minutes,action\n"
        "2026-01-20T18:00:00+00:00,FOMC,central_bank,high,180,120,BLOCK\n",
        encoding="utf-8",
    )
    event_panel = build_event_calendar(data_dir)
    feature_panel = build_feature_panel(data_dir)
    signals_path = build_signals(data_dir)
    quality_report = build_research_quality_report(data_dir)

    assert market_panel.exists()
    assert macro_panel.exists()
    assert event_panel.exists()
    assert feature_panel.exists()
    assert signals_path.exists()
    assert quality_report.exists()

    feature = pl.read_parquet(feature_panel)
    assert "canonical_symbol" in feature.columns
    assert "dgs10" in feature.columns
    assert "vix_level" in feature.columns
    assert "trade_allowed" in feature.columns

    signals = pl.read_csv(signals_path, try_parse_dates=True)
    assert signals.height > 0
    assert set(signals.columns) == {
        "ts_signal",
        "canonical_symbol",
        "side",
        "timeframe",
        "signal_strength",
        "strategy_name",
        "reason",
    }
    assert set(signals.get_column("canonical_symbol").to_list()) == {"QQQ"}
    assert set(signals.get_column("timeframe").to_list()) == {"4h"}


def test_build_event_calendar_requires_required_columns(tmp_path) -> None:
    csv_path = tmp_path / "data/research/event_calendar.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text("event_ts,event_name\n2026-01-01T00:00:00+00:00,CPI\n", encoding="utf-8")

    try:
        build_event_calendar(tmp_path / "data")
    except ValueError as exc:
        assert "Event calendar CSV missing columns" in str(exc)
    else:
        raise AssertionError("Expected build_event_calendar to fail on missing columns")
