from __future__ import annotations

from types import SimpleNamespace

import pytest

from sis.research.strategy_lab.authoring.compiler.trade_order_boolean_fields import (
    _order_boolean_value,
)
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
)


def _order(**overrides):
    defaults = {
        "post_only": False,
        "post_only_column": "row_post_only",
        "reduce_only": False,
        "reduce_only_column": "row_reduce_only",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def test_order_boolean_value_uses_row_column_before_default() -> None:
    value = _order_boolean_value(
        row={"row_post_only": "yes"},
        order=_order(post_only=False),
        order_overrides=None,
        value_attr="post_only",
        column_attr="post_only_column",
    )

    assert value is True


def test_order_boolean_value_uses_explicit_override_and_disables_column() -> None:
    value = _order_boolean_value(
        row={"row_post_only": "no"},
        order=_order(post_only=False),
        order_overrides={"post_only": True},
        value_attr="post_only",
        column_attr="post_only_column",
    )

    assert value is True


def test_order_boolean_value_falls_back_when_row_column_is_blank() -> None:
    assert (
        _order_boolean_value(
            row={"row_reduce_only": " "},
            order=_order(reduce_only=True),
            order_overrides=None,
            value_attr="reduce_only",
            column_attr="reduce_only_column",
        )
        is True
    )


def test_order_boolean_value_rejects_missing_configured_row_column() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported boolean value"):
        _order_boolean_value(
            row={},
            order=_order(reduce_only=False),
            order_overrides=None,
            value_attr="reduce_only",
            column_attr="reduce_only_column",
        )


def test_order_boolean_value_rejects_unsupported_row_boolean() -> None:
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported boolean value"):
        _order_boolean_value(
            row={"row_post_only": "maybe"},
            order=_order(),
            order_overrides=None,
            value_attr="post_only",
            column_attr="post_only_column",
        )
