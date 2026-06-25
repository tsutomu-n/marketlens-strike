from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.row_numeric_values import (
    _exit_bps,
    _minutes_value,
    _non_negative_bps_value,
    _non_negative_value,
    _optional_float_from_row,
    _positive_integer_value,
    _sizing_value,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def test_optional_float_from_row_accepts_numbers_and_non_empty_strings() -> None:
    row = {"number": 1, "float": 1.25, "text": "2.5", "blank": " ", "none": None}

    assert _optional_float_from_row(row, "number") == 1.0
    assert _optional_float_from_row(row, "float") == 1.25
    assert _optional_float_from_row(row, "text") == 2.5
    assert _optional_float_from_row(row, "blank") is None
    assert _optional_float_from_row(row, "none") is None
    assert _optional_float_from_row(row, "missing") is None
    assert _optional_float_from_row(row, None) is None


def test_exit_bps_and_sizing_values_prefer_dynamic_value_then_fixed_value() -> None:
    row = {"exit": "12.5", "size": 0.75}

    assert _exit_bps(row, fixed=5.0, column="exit") == 12.5
    assert _exit_bps(row, fixed=5.0, column="missing") == 5.0
    assert _sizing_value(row, fixed=0.5, column="size") == 0.75
    assert _sizing_value(row, fixed=0.5, column="missing") == 0.5


def test_non_negative_validators_reject_negative_dynamic_values() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="rules.exit.stop_loss_bps"):
        _non_negative_bps_value(
            {"stop": -1.0},
            fixed=None,
            column="stop",
            field_name="rules.exit.stop_loss_bps",
        )

    with pytest.raises(StrategyAuthoringValidationError, match="rules.sizing.max_weight"):
        _non_negative_value(
            {"weight": -0.1},
            fixed=None,
            column="weight",
            field_name="rules.sizing.max_weight",
        )


def test_unit_interval_value_rejects_values_outside_zero_to_one() -> None:
    assert (
        _unit_interval_value(
            {"confidence": "0.6"},
            fixed=None,
            column="confidence",
            field_name="rules.confidence",
        )
        == 0.6
    )

    with pytest.raises(StrategyAuthoringValidationError, match="rules.confidence"):
        _unit_interval_value(
            {"confidence": 1.1},
            fixed=None,
            column="confidence",
            field_name="rules.confidence",
        )


def test_integer_helpers_preserve_dynamic_error_messages() -> None:
    assert _minutes_value({"timeout": "3"}, fixed=None, column="timeout") == 3
    assert _minutes_value({"timeout": " "}, fixed=4, column="timeout") == 4

    with pytest.raises(StrategyAuthoringValidationError, match="timeout must be an integer"):
        _minutes_value({"timeout": 1.5}, fixed=None, column="timeout")

    assert (
        _positive_integer_value(
            {"cooldown": "2"},
            fixed=None,
            column="cooldown",
            field_name="rules.temporal.cooldown_minutes",
        )
        == 2
    )

    with pytest.raises(StrategyAuthoringValidationError, match="must be an integer value"):
        _positive_integer_value(
            {"cooldown": 2.5},
            fixed=None,
            column="cooldown",
            field_name="rules.temporal.cooldown_minutes",
        )

    with pytest.raises(StrategyAuthoringValidationError, match="must be positive"):
        _positive_integer_value(
            {"cooldown": 0},
            fixed=None,
            column="cooldown",
            field_name="rules.temporal.cooldown_minutes",
        )
