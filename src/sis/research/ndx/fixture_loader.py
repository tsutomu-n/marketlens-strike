from __future__ import annotations

from pathlib import Path

import polars as pl


BAR_COLUMNS = ("date", "open", "close", "prev_close", "source_ts")
LEVEL_COLUMNS = ("date", "value", "prev_value", "source_ts")


def load_bar_fixture(input_root: Path, filename: str, *, prefix: str) -> pl.DataFrame:
    frame = _read_fixture(input_root / filename, required_columns=BAR_COLUMNS)
    frame = frame.rename(
        {
            "open": f"{prefix}_open",
            "close": f"{prefix}_close",
            "prev_close": f"{prefix}_prev_close",
            "source_ts": f"{prefix}_source_ts",
        }
    )
    return frame.with_columns(pl.col("date").str.to_date())


def load_level_fixture(input_root: Path, filename: str, *, prefix: str) -> pl.DataFrame:
    frame = _read_fixture(input_root / filename, required_columns=LEVEL_COLUMNS)
    frame = frame.rename(
        {
            "value": f"{prefix}_value",
            "prev_value": f"{prefix}_prev_value",
            "source_ts": f"{prefix}_source_ts",
        }
    )
    return frame.with_columns(pl.col("date").str.to_date())


def _read_fixture(path: Path, *, required_columns: tuple[str, ...]) -> pl.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"required NDX fixture missing: {path}")
    frame = pl.read_csv(path).drop_nulls(subset=["date"])
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} missing required columns: {', '.join(missing)}")
    duplicate_count = frame.select(pl.col("date").is_duplicated().sum()).item()
    if duplicate_count:
        raise ValueError(f"{path} contains duplicate date rows.")
    return frame.select(list(required_columns))
