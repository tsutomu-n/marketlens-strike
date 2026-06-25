from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.row_values import (
    _entry_type_value,
    _minutes_value,
    _non_negative_bps_value,
    _optional_bool_from_row,
    _optional_float_from_row,
    _positive_integer_value,
    _sizing_value,
    _time_in_force_value,
    _unit_interval_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def test_optional_float_from_row_accepts_numbers_and_non_empty_strings() -> None:
    row = {"number": 1, "text": "2.5", "blank": " "}

    assert _optional_float_from_row(row, "number") == 1.0
    assert _optional_float_from_row(row, "text") == 2.5
    assert _optional_float_from_row(row, "blank") is None
    assert _optional_float_from_row(row, None) is None


def test_sizing_value_prefers_dynamic_value_then_fixed_value() -> None:
    row = {"dynamic": "0.75"}

    assert _sizing_value(row, fixed=0.5, column="dynamic") == 0.75
    assert _sizing_value(row, fixed=0.5, column="missing") == 0.5


def test_non_negative_and_unit_interval_validators_reject_invalid_values() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="rules.exit.stop_loss_bps"):
        _non_negative_bps_value(
            {"stop": -1.0},
            fixed=None,
            column="stop",
            field_name="rules.exit.stop_loss_bps",
        )
    with pytest.raises(StrategyAuthoringValidationError, match="rules.confidence"):
        _unit_interval_value(
            {"confidence": 1.1},
            fixed=None,
            column="confidence",
            field_name="rules.confidence",
        )


def test_integer_helpers_preserve_existing_dynamic_error_messages() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="timeout must be an integer"):
        _minutes_value({"timeout": 1.5}, fixed=None, column="timeout")
    with pytest.raises(StrategyAuthoringValidationError, match="rules.temporal.cooldown_minutes"):
        _positive_integer_value(
            {"cooldown": 0},
            fixed=None,
            column="cooldown",
            field_name="rules.temporal.cooldown_minutes",
        )


def test_entry_type_and_time_in_force_parse_supported_values() -> None:
    assert _entry_type_value({"entry": "LIMIT"}, fixed="market", column="entry") == "limit"
    assert _entry_type_value({"entry": " "}, fixed="market", column="entry") == "market"
    assert _time_in_force_value({"tif": "IOC"}, fixed="gtc", column="tif") == "ioc"


def test_optional_bool_from_row_preserves_bool_numeric_and_string_semantics() -> None:
    assert _optional_bool_from_row({"flag": True}, "flag") is True
    assert _optional_bool_from_row({"flag": 0}, "flag") is False
    assert _optional_bool_from_row({"flag": "yes"}, "flag") is True
    assert _optional_bool_from_row({"flag": " "}, "flag") is None
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported boolean value"):
        _optional_bool_from_row({"flag": "maybe"}, "flag")
