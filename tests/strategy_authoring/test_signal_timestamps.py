from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.research.strategy_lab.authoring.compiler.signal_timestamps import _signal_timestamp
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def test_signal_timestamp_passes_datetime_through() -> None:
    ts_signal = datetime(2026, 1, 1, 4, tzinfo=timezone.utc)

    assert _signal_timestamp({"ts_signal": ts_signal}) is ts_signal


def test_signal_timestamp_parses_z_suffix_as_utc_offset() -> None:
    assert _signal_timestamp({"ts_signal": "2026-01-01T04:00:00Z"}) == datetime(
        2026, 1, 1, 4, tzinfo=timezone.utc
    )


def test_signal_timestamp_parses_iso_offset_strings() -> None:
    assert _signal_timestamp({"ts_signal": "2026-01-01T04:00:00+09:00"}) == datetime.fromisoformat(
        "2026-01-01T04:00:00+09:00"
    )


def test_signal_timestamp_rejects_unsupported_values() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported ts_signal value: 123"):
        _signal_timestamp({"ts_signal": 123})
