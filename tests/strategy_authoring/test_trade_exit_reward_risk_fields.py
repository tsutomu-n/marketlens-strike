from __future__ import annotations

from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_exit_reward_risk_fields import (
    _trade_exit_reward_risk_fields,
)


def _exit(**overrides):
    defaults = {
        "min_reward_risk_ratio": None,
        "min_reward_risk_ratio_column": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _regime(**overrides):
    defaults = {"min_reward_risk_ratio": None}
    return SimpleNamespace(**{**defaults, **overrides})


def test_trade_exit_reward_risk_fields_resolve_defaults() -> None:
    assert _trade_exit_reward_risk_fields(row={}, exit_rules=_exit()) == {
        "min_reward_risk_ratio": None,
        "reward_risk_ratio": None,
    }


def test_trade_exit_reward_risk_fields_use_row_column_regime_and_override() -> None:
    fields = _trade_exit_reward_risk_fields(
        row={"row_min_rr": 1.5},
        exit_rules=_exit(min_reward_risk_ratio_column="row_min_rr"),
        regime=_regime(min_reward_risk_ratio=2.0),
        exit_overrides={},
    )

    assert fields == {
        "min_reward_risk_ratio": 1.5,
        "reward_risk_ratio": None,
    }

    fields = _trade_exit_reward_risk_fields(
        row={"row_min_rr": 1.5},
        exit_rules=_exit(min_reward_risk_ratio_column="row_min_rr"),
        regime=_regime(min_reward_risk_ratio=2.0),
        exit_overrides={"min_reward_risk_ratio": 2.5},
    )

    assert fields == {
        "min_reward_risk_ratio": 2.5,
        "reward_risk_ratio": None,
    }
