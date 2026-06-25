from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.research.strategy_lab.authoring.compiler.event_window_guards import (
    _event_window_block_reason,
    _feature_timestamp,
    _parse_event_ts,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError

from .helpers import load_authoring_spec, template_yaml


def _spec_with_event_windows(tmp_path):
    spec_path = tmp_path / "event-window-guards.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  event_windows:\n"
            "    - name: fomc\n"
            "      event_ts_column: event_ts\n"
            "      mode: block\n"
            "      before_minutes: 30\n"
            "      after_minutes: 30\n"
            "      block_reason: macro_event\n"
            "    - name: earnings\n"
            "      event_ts_column: earnings_ts\n"
            "      mode: allow\n"
            "      before_minutes: 10\n"
            "      after_minutes: 10\n",
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_parse_event_ts_accepts_datetime_iso_and_missing_values() -> None:
    naive = datetime(2026, 1, 1, 12)
    aware = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)

    assert _parse_event_ts(naive) == aware
    assert _parse_event_ts("2026-01-01T12:00:00Z") == aware
    assert _parse_event_ts(None) is None
    assert _parse_event_ts("") is None


def test_event_window_block_reason_handles_block_allow_and_missing_event(tmp_path) -> None:
    spec = _spec_with_event_windows(tmp_path)

    assert (
        _event_window_block_reason(
            {
                "ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                "event_ts": "2026-01-01T12:15:00Z",
                "earnings_ts": "2026-01-01T12:00:00Z",
            },
            spec,
        )
        == "macro_event"
    )
    assert (
        _event_window_block_reason(
            {
                "ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                "event_ts": "2026-01-01T14:00:00Z",
                "earnings_ts": None,
            },
            spec,
        )
        == "event_window_earnings_missing"
    )
    assert (
        _event_window_block_reason(
            {
                "ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                "event_ts": "2026-01-01T14:00:00Z",
                "earnings_ts": "2026-01-01T12:00:00Z",
            },
            spec,
        )
        is None
    )


def test_feature_timestamp_preserves_existing_invalid_timestamp_errors() -> None:
    assert _feature_timestamp({"ts": "2026-01-01T00:00:00Z"}) == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )
    with pytest.raises(StrategyAuthoringValidationError, match="Invalid event window timestamp"):
        _feature_timestamp({"ts": "not-a-date"})
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported feature ts value"):
        _feature_timestamp({"ts": None})
