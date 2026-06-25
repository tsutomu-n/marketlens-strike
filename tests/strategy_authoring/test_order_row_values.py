from __future__ import annotations

import pytest

from sis.research.strategy_lab.authoring.compiler.order_row_values import (
    _entry_type_value,
    _optional_bool_from_row,
    _time_in_force_value,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError


def test_order_row_values_parse_supported_entry_type_and_time_in_force() -> None:
    assert _entry_type_value({"entry": "LIMIT"}, fixed="market", column="entry") == "limit"
    assert _entry_type_value({"entry": " "}, fixed="market", column="entry") == "market"
    assert _entry_type_value({}, fixed="stop_market", column=None) == "stop_market"

    assert _time_in_force_value({"tif": "IOC"}, fixed="gtc", column="tif") == "ioc"
    assert _time_in_force_value({"tif": " "}, fixed="gtd", column="tif") == "gtd"
    assert _time_in_force_value({}, fixed="fok", column=None) == "fok"


def test_order_row_values_reject_unsupported_entry_type_and_time_in_force() -> None:
    with pytest.raises(
        StrategyAuthoringValidationError,
        match="Unsupported rules.order.entry_type_column value",
    ):
        _entry_type_value({"entry": "peg"}, fixed="market", column="entry")

    with pytest.raises(
        StrategyAuthoringValidationError,
        match="Unsupported rules.order.time_in_force_column value",
    ):
        _time_in_force_value({"tif": "day"}, fixed="gtc", column="tif")


def test_optional_bool_from_row_preserves_bool_numeric_and_string_semantics() -> None:
    assert _optional_bool_from_row({"flag": True}, "flag") is True
    assert _optional_bool_from_row({"flag": 0}, "flag") is False
    assert _optional_bool_from_row({"flag": "yes"}, "flag") is True
    assert _optional_bool_from_row({"flag": "n"}, "flag") is False
    assert _optional_bool_from_row({"flag": " "}, "flag") is None
    assert _optional_bool_from_row({}, None) is None

    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported boolean value"):
        _optional_bool_from_row({"flag": "maybe"}, "flag")
