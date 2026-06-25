from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_timestamp_limit_values import (
    _portfolio_timestamp_limit_value,
)


@dataclass(frozen=True)
class _PortfolioLimitSpec:
    fixed_attr: str
    value_key: str
    field_name: str


_PORTFOLIO_LIMIT_SPECS: dict[str, _PortfolioLimitSpec] = {
    "max_total_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_total_position_weight",
        value_key="_portfolio_max_total_position_weight",
        field_name="rules.portfolio.max_total_position_weight_column",
    ),
    "max_long_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_long_position_weight",
        value_key="_portfolio_max_long_position_weight",
        field_name="rules.portfolio.max_long_position_weight_column",
    ),
    "max_short_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_short_position_weight",
        value_key="_portfolio_max_short_position_weight",
        field_name="rules.portfolio.max_short_position_weight_column",
    ),
    "max_abs_net_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_abs_net_position_weight",
        value_key="_portfolio_max_abs_net_position_weight",
        field_name="rules.portfolio.max_abs_net_position_weight_column",
    ),
    "max_symbol_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_symbol_position_weight",
        value_key="_portfolio_max_symbol_position_weight",
        field_name="rules.portfolio.max_symbol_position_weight_column",
    ),
    "max_group_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_group_position_weight",
        value_key="_portfolio_max_group_position_weight",
        field_name="rules.portfolio.max_group_position_weight_column",
    ),
    "max_group_abs_net_position_weight": _PortfolioLimitSpec(
        fixed_attr="max_group_abs_net_position_weight",
        value_key="_portfolio_max_group_abs_net_position_weight",
        field_name="rules.portfolio.max_group_abs_net_position_weight_column",
    ),
}


def _portfolio_timestamp_limit(
    rows: list[dict[str, Any]],
    *,
    fixed: float | None,
    value_key: str,
    field_name: str,
) -> float | None:
    value = _portfolio_timestamp_limit_value(rows, value_key=value_key, field_name=field_name)
    return fixed if value is None else value


def _portfolio_limit_value(
    rows: list[dict[str, Any]], *, portfolio: Any, spec: _PortfolioLimitSpec
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=getattr(portfolio, spec.fixed_attr),
        value_key=spec.value_key,
        field_name=spec.field_name,
    )
