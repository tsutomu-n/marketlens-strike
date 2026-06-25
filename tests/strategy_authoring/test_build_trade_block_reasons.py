from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.build_trade_block_reasons import (
    _trade_block_reason_for_row,
)

from .helpers import load_authoring_spec, template_yaml


def _spec(tmp_path):
    spec_path = tmp_path / "build-trade-block-reasons.yaml"
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
            "  data_guard:\n"
            "    max_feature_age_minutes: 30\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            "    max_drawdown_floor: -0.15\n"
            "    cooldown_minutes: 90",
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_trade_block_reason_prioritizes_event_and_data_before_risk(tmp_path) -> None:
    spec = _spec(tmp_path)
    start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    cooldowns = {}

    event_reason = _trade_block_reason_for_row(
        row={
            "ts": start,
            "event_ts": start,
            "feature_age_minutes": 99,
            "strategy_drawdown": -0.20,
        },
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )
    data_reason = _trade_block_reason_for_row(
        row={
            "ts": start,
            "event_ts": start + timedelta(hours=2),
            "feature_age_minutes": 99,
            "strategy_drawdown": -0.20,
        },
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )

    assert event_reason == "macro_event"
    assert data_reason == "data_guard_feature_age_too_old"
    assert cooldowns == {}


def test_trade_block_reason_uses_risk_throttle_cooldown_state(tmp_path) -> None:
    spec = _spec(tmp_path)
    start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    cooldowns = {}

    first_reason = _trade_block_reason_for_row(
        row={
            "ts": start,
            "event_ts": start + timedelta(hours=2),
            "feature_age_minutes": 0,
            "strategy_drawdown": -0.20,
        },
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )
    second_reason = _trade_block_reason_for_row(
        row={
            "ts": start + timedelta(minutes=30),
            "event_ts": start + timedelta(hours=2),
            "feature_age_minutes": 0,
            "strategy_drawdown": -0.01,
        },
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )
    no_reason = _trade_block_reason_for_row(
        row={
            "ts": start + timedelta(minutes=120),
            "event_ts": start + timedelta(hours=3),
            "feature_age_minutes": 0,
            "strategy_drawdown": -0.01,
        },
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )

    assert first_reason == "risk_throttle_max_drawdown"
    assert second_reason == "risk_throttle_cooldown"
    assert no_reason is None
    assert cooldowns == {"QQQ": start + timedelta(minutes=90)}
