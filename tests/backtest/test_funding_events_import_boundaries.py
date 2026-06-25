from __future__ import annotations

from pathlib import Path


def test_runner_delegates_funding_event_normalization() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    funding_events_text = Path("src/sis/backtest/engine/funding_events.py").read_text(
        encoding="utf-8"
    )

    assert "build_funding_event_rows" in runner_text
    assert "_normalize_funding_events" not in runner_text
    assert "funding_event_ts" not in runner_text
    assert "oracle_price_at_funding" not in runner_text
    assert "_normalize_funding_events" in funding_events_text
    assert "funding_event_ts" in funding_events_text
    assert "oracle_price_at_funding" in funding_events_text
