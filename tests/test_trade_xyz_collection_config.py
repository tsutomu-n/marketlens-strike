from pathlib import Path

import pytest

from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config


def test_load_trade_xyz_data_collection_config_defaults() -> None:
    config = load_trade_xyz_data_collection_config(Path("configs/trade_xyz_data_collection.yaml"))

    assert config.symbols == (
        "AAPL",
        "AMD",
        "AMZN",
        "EWJ",
        "GOOGL",
        "META",
        "MSFT",
        "NVDA",
        "SP500",
        "TSLA",
        "XYZ100",
    )
    assert config.duration_minutes == 1440
    assert config.interval_seconds == 60
    assert config.usable_start_date == "2026-05-31"
    assert config.signal_candle_intervals == ("30m", "4h", "1d", "3d")
    assert config.signal_candle_period_days == 1
    assert config.archive_start_date == "2026-05-31"


def test_load_trade_xyz_data_collection_config_rejects_empty_symbols(tmp_path) -> None:
    path = tmp_path / "collection.yaml"
    path.write_text(
        """
schema_version: trade_xyz_data_collection_config.v1
symbols: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="symbols must not be empty"):
        load_trade_xyz_data_collection_config(path)
