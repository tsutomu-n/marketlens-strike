from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.build_risk_throttle import (
    _risk_throttle_block_for_row,
)

from .helpers import load_authoring_spec, template_yaml


def _risk_throttle_spec(tmp_path):
    spec_path = tmp_path / "risk-throttle-build.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            "    max_drawdown_floor: -0.15\n"
            "    cooldown_minutes: 90",
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_risk_throttle_block_for_row_sets_cooldown_after_new_block(tmp_path) -> None:
    spec = _risk_throttle_spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cooldowns = {}

    reason = _risk_throttle_block_for_row(
        row={"ts": start, "strategy_drawdown": -0.20},
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )

    assert reason == "risk_throttle_max_drawdown"
    assert cooldowns == {"QQQ": start + timedelta(minutes=90)}


def test_risk_throttle_block_for_row_uses_existing_cooldown_without_extending_it(
    tmp_path,
) -> None:
    spec = _risk_throttle_spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cooldown_until = start + timedelta(minutes=90)
    cooldowns = {"QQQ": cooldown_until}

    reason = _risk_throttle_block_for_row(
        row={"ts": start + timedelta(minutes=30), "strategy_drawdown": -0.05},
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )

    assert reason == "risk_throttle_cooldown"
    assert cooldowns == {"QQQ": cooldown_until}


def test_risk_throttle_block_for_row_keeps_expired_cooldown_state_when_unblocked(
    tmp_path,
) -> None:
    spec = _risk_throttle_spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cooldown_until = start + timedelta(minutes=90)
    cooldowns = {"QQQ": cooldown_until}

    reason = _risk_throttle_block_for_row(
        row={"ts": start + timedelta(minutes=120), "strategy_drawdown": -0.05},
        spec=spec,
        symbol="QQQ",
        cooldown_until_by_symbol=cooldowns,
    )

    assert reason is None
    assert cooldowns == {"QQQ": cooldown_until}
