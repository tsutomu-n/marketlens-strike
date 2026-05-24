from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.strategies.qqq_trend_rates_vix import build_qqq_trend_rates_vix_signals


def build_signals(data_dir: Path) -> Path:
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    if not feature_panel_path.exists():
        raise FileNotFoundError(f"Research feature panel not found: {feature_panel_path}")

    frame = pl.read_parquet(feature_panel_path)
    if frame.is_empty():
        raise ValueError("Feature panel is empty.")

    signals = build_qqq_trend_rates_vix_signals(frame)

    out = data_dir / "research/signals.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    signals.write_csv(out)
    return out
