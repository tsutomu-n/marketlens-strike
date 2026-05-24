from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from sis.research.providers import FredMacroProvider, MacroProvider, PandasDataReaderMacroProvider

DEFAULT_MACRO_SERIES = ["DGS10", "DGS2", "T10Y2Y", "FEDFUNDS"]


def build_macro_panel(
    data_dir: Path,
    *,
    provider: MacroProvider | None = None,
    series_ids: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> Path:
    selected_provider = provider or FredMacroProvider()
    selected_series = series_ids or DEFAULT_MACRO_SERIES
    selected_start = start or (date.today() - timedelta(days=365 * 3))
    selected_end = end or date.today()
    try:
        frame = selected_provider.fetch_series(selected_series, selected_start, selected_end)
    except Exception:
        if provider is not None:
            raise
        fallback = PandasDataReaderMacroProvider()
        frame = fallback.fetch_series(selected_series, selected_start, selected_end)
    if frame.is_empty():
        raise ValueError("No research macro rows fetched.")

    raw_path = data_dir / "research/raw/fred_macro.parquet"
    macro_panel_path = data_dir / "research/macro_panel.parquet"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    frame = frame.sort(["series_id", "date"])
    frame.write_parquet(raw_path)
    frame.write_parquet(macro_panel_path)
    return macro_panel_path
