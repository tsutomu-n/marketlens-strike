from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sis.research.strategy_lab.authoring.compiler.guard_block_reasons import (
    _data_guard_block_reason,
    _event_window_block_reason,
    _feature_timestamp,
    _risk_throttle_block_reason,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError

from .helpers import load_authoring_spec, template_yaml


def _spec_with_rules(tmp_path, rules_yaml: str):
    spec_path = tmp_path / "guard-spec.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n" + rules_yaml,
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_event_window_block_reason_handles_block_and_allow_modes(tmp_path) -> None:
    spec = _spec_with_rules(
        tmp_path,
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
    )

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


def test_data_guard_block_reason_preserves_order_and_missing_behavior(tmp_path) -> None:
    spec = _spec_with_rules(
        tmp_path,
        "  data_guard:\n"
        "    max_feature_age_minutes: 30\n"
        "    min_source_confidence: 0.8\n"
        "    min_venue_quality_score: 0.7\n"
        "    max_staleness_bps: 5\n"
        "    max_regime_transition_score: 0.4\n",
    )

    assert _data_guard_block_reason({}, spec) == "data_guard_feature_age_missing"
    assert (
        _data_guard_block_reason({"feature_age_minutes": 31}, spec)
        == "data_guard_feature_age_too_old"
    )
    assert (
        _data_guard_block_reason(
            {
                "feature_age_minutes": 10,
                "source_confidence": 0.75,
                "venue_quality_score": 0.9,
                "staleness_bps": 1.0,
                "regime_transition_score": 0.1,
            },
            spec,
        )
        == "data_guard_source_confidence_too_low"
    )
    assert (
        _data_guard_block_reason(
            {
                "feature_age_minutes": 10,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
                "staleness_bps": 1.0,
                "regime_transition_score": 0.1,
            },
            spec,
        )
        is None
    )


def test_risk_throttle_block_reason_preserves_threshold_boundaries(tmp_path) -> None:
    spec = _spec_with_rules(
        tmp_path,
        "  risk_throttle:\n"
        "    max_drawdown_column: strategy_drawdown\n"
        "    max_drawdown_floor: -0.2\n"
        "    daily_loss_column: daily_pnl\n"
        "    daily_loss_floor: -0.1\n"
        "    loss_streak_column: loss_streak\n"
        "    max_loss_streak: 3\n",
    )

    assert (
        _risk_throttle_block_reason(
            {"strategy_drawdown": -0.2, "daily_pnl": 0, "loss_streak": 0}, spec
        )
        == "risk_throttle_max_drawdown"
    )
    assert (
        _risk_throttle_block_reason(
            {"strategy_drawdown": -0.1, "daily_pnl": -0.1, "loss_streak": 0}, spec
        )
        == "risk_throttle_daily_loss"
    )
    assert (
        _risk_throttle_block_reason(
            {"strategy_drawdown": -0.1, "daily_pnl": 0, "loss_streak": 3}, spec
        )
        == "risk_throttle_loss_streak"
    )
    assert (
        _risk_throttle_block_reason(
            {"strategy_drawdown": -0.1, "daily_pnl": 0, "loss_streak": 2}, spec
        )
        is None
    )


def test_feature_timestamp_parses_iso_strings_and_rejects_invalid_values() -> None:
    parsed = _feature_timestamp({"ts": "2026-01-01T00:00:00Z"})

    assert parsed == datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(StrategyAuthoringValidationError, match="Invalid event window timestamp"):
        _feature_timestamp({"ts": "not-a-date"})
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported feature ts value"):
        _feature_timestamp({"ts": None})
