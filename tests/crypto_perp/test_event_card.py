from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.event_card import build_event_card
from sis.crypto_perp.events import detect_event
from sis.crypto_perp.features import EventDetectorConfig
from sis.crypto_perp.rendering import render_event_card_markdown
from sis.crypto_perp.quality import validate_candle_series
from support.cli import normalized_stdout
from .test_features import make_bars, ticker


runner = CliRunner()


def _event():
    bars = make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296)
    event = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=bars,
        ticker=ticker(),
        quality_report=validate_candle_series(bars, interval="15m"),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=EventDetectorConfig(),
    )
    assert event is not None
    return event


def test_event_card_renders_human_readable_direction_neutral_snapshot() -> None:
    event = _event()

    card = build_event_card(event)
    markdown = render_event_card_markdown(card)

    assert "BTCUSDT" in markdown
    assert "slow_pump_74h_v1" in markdown
    assert "return_74h" in markdown
    assert "funding_rate" in markdown
    assert "open_interest_raw" in markdown
    assert "REVERSAL_SHORT" not in markdown
    assert "CONTINUATION_LONG" not in markdown


def test_watchdeck_cli_renders_event_card(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(_event().model_dump_json(indent=2) + "\n", encoding="utf-8")

    result = runner.invoke(app, ["crypto-perp-watchdeck", "--event", str(event_path)])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "BTCUSDT slow_pump_74h_v1" in stdout
    assert "REVERSAL_SHORT" not in stdout
