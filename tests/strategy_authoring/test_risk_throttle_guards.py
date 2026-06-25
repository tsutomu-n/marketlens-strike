from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.risk_throttle_guards import (
    _risk_throttle_block_reason,
)

from .helpers import load_authoring_spec, template_yaml


def _spec_with_rules(tmp_path, rules_yaml: str):
    spec_path = tmp_path / "risk-throttle-guards.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n" + rules_yaml,
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def test_risk_throttle_block_reason_returns_none_when_disabled(tmp_path) -> None:
    spec = _spec_with_rules(tmp_path, "")

    assert _risk_throttle_block_reason({"strategy_drawdown": -1.0}, spec) is None


def test_risk_throttle_block_reason_preserves_threshold_priority(tmp_path) -> None:
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
            {"strategy_drawdown": -0.2, "daily_pnl": -0.1, "loss_streak": 3}, spec
        )
        == "risk_throttle_max_drawdown"
    )
    assert (
        _risk_throttle_block_reason(
            {"strategy_drawdown": -0.1, "daily_pnl": -0.1, "loss_streak": 3}, spec
        )
        == "risk_throttle_daily_loss"
    )
    assert (
        _risk_throttle_block_reason(
            {"strategy_drawdown": -0.1, "daily_pnl": 0.0, "loss_streak": 3}, spec
        )
        == "risk_throttle_loss_streak"
    )


def test_risk_throttle_block_reason_uses_row_threshold_columns(tmp_path) -> None:
    spec = _spec_with_rules(
        tmp_path,
        "  risk_throttle:\n"
        "    max_drawdown_column: strategy_drawdown\n"
        "    max_drawdown_floor_column: row_drawdown_floor\n"
        "    daily_loss_column: daily_pnl\n"
        "    daily_loss_floor_column: row_daily_loss_floor\n"
        "    loss_streak_column: loss_streak\n"
        "    max_loss_streak_column: row_max_loss_streak\n",
    )

    assert (
        _risk_throttle_block_reason(
            {
                "strategy_drawdown": -0.16,
                "row_drawdown_floor": -0.15,
                "daily_pnl": 0.0,
                "row_daily_loss_floor": -0.05,
                "loss_streak": 0,
                "row_max_loss_streak": 4,
            },
            spec,
        )
        == "risk_throttle_max_drawdown"
    )
    assert (
        _risk_throttle_block_reason(
            {
                "strategy_drawdown": -0.10,
                "row_drawdown_floor": -0.15,
                "daily_pnl": -0.06,
                "row_daily_loss_floor": -0.05,
                "loss_streak": 0,
                "row_max_loss_streak": 4,
            },
            spec,
        )
        == "risk_throttle_daily_loss"
    )
