from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_groups import (
    _portfolio_exposure_groups,
)
from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_timestamp_group import (
    _apply_portfolio_exposure_timestamp_group_limits,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_exposure_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if not portfolio.exposure_limits_enabled:
        return rows
    passthrough, grouped = _portfolio_exposure_groups(rows)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        selected.extend(_apply_portfolio_exposure_timestamp_group_limits(timestamp_rows, spec))
    return selected
