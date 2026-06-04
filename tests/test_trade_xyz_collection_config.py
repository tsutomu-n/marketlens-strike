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
    assert config.signal_candle_request_delay_seconds == 1.5
    assert config.archive_start_date == "2026-05-31"
    assert config.ws_enabled is False
    assert config.ws_url == "wss://api.hyperliquid.xyz/ws"
    assert config.ws_default_subscriptions == ("bbo", "trades", "activeAssetCtx")
    assert config.ws_duration_minutes == 60
    assert config.ws_heartbeat_seconds == 30
    assert config.ws_server_timeout_seconds == 60
    assert config.ws_reconnect_max_attempts == 5
    assert config.ws_reconnect_initial_delay_seconds == 1.0
    assert config.ws_reconnect_max_delay_seconds == 30.0
    assert config.ws_output_root == "raw/ws/trade_xyz"
    assert config.ws_write_control_messages is True


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


def test_load_trade_xyz_data_collection_config_rejects_invalid_ws_subscriptions(
    tmp_path,
) -> None:
    path = tmp_path / "collection.yaml"
    path.write_text(
        """
schema_version: trade_xyz_data_collection_config.v1
symbols: [SP500]
websocket_collection:
  default_subscriptions:
    - bbo
    - unknown_subscription
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported values"):
        load_trade_xyz_data_collection_config(path)


def test_load_trade_xyz_data_collection_config_rejects_invalid_signal_candle_delay(
    tmp_path,
) -> None:
    path = tmp_path / "collection.yaml"
    path.write_text(
        """
schema_version: trade_xyz_data_collection_config.v1
symbols: [SP500]
signal_candles:
  request_delay_seconds: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="signal_candles.request_delay_seconds"):
        load_trade_xyz_data_collection_config(path)
