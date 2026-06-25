from __future__ import annotations

from sis.research.strategy_lab.authoring.bracket_required_columns import (
    _bracket_required_columns,
)
from sis.research.strategy_lab.authoring.contracts.core import Condition, ConfirmationPanel
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.data_guard_required_columns import (
    _data_guard_required_columns,
)
from sis.research.strategy_lab.authoring.execution_required_columns import (
    _execution_required_columns,
)
from sis.research.strategy_lab.authoring.exit_required_columns import _exit_required_columns
from sis.research.strategy_lab.authoring.multi_leg_required_columns import (
    _multi_leg_required_columns,
)
from sis.research.strategy_lab.authoring.order_required_columns import _order_required_columns
from sis.research.strategy_lab.authoring.portfolio_required_columns import (
    _portfolio_required_columns,
)
from sis.research.strategy_lab.authoring.risk_throttle_required_columns import (
    _risk_throttle_required_columns,
)
from sis.research.strategy_lab.authoring.sizing_required_columns import _sizing_required_columns


def _prefixed_confirmation_columns(panel: ConfirmationPanel, columns: set[str]) -> set[str]:
    return {
        f"{panel.prefix}_{column}" for column in columns if column not in {"ts", "canonical_symbol"}
    }


def _required_columns(spec: StrategyAuthoringSpec) -> set[str]:
    columns = {"ts", "canonical_symbol"}
    derived_names = {feature.name for feature in spec.rules.derived_features}

    def add_column(column: str) -> None:
        if column not in derived_names:
            columns.add(column)

    def add_condition_columns(conditions: list[Condition]) -> None:
        for cond in conditions:
            add_column(cond.column)
            if cond.value_column is not None:
                add_column(cond.value_column)

    for feature in spec.rules.derived_features:
        for column in feature.columns:
            add_column(column)

    add_condition_columns([*spec.rules.entry.all, *spec.rules.entry.any, *spec.rules.entry.none])
    for entry in (spec.rules.long_entry, spec.rules.short_entry):
        if entry is not None:
            add_condition_columns([*entry.all, *entry.any, *entry.none])
    if spec.rules.hold is not None:
        add_condition_columns([*spec.rules.hold.all, *spec.rules.hold.any, *spec.rules.hold.none])
    if spec.rules.close is not None:
        add_condition_columns(
            [*spec.rules.close.all, *spec.rules.close.any, *spec.rules.close.none]
        )
    if spec.rules.reduce is not None:
        add_condition_columns(
            [*spec.rules.reduce.all, *spec.rules.reduce.any, *spec.rules.reduce.none]
        )
    if spec.rules.add is not None:
        add_condition_columns([*spec.rules.add.all, *spec.rules.add.any, *spec.rules.add.none])
    if spec.rules.rebalance is not None:
        add_condition_columns(
            [*spec.rules.rebalance.all, *spec.rules.rebalance.any, *spec.rules.rebalance.none]
        )
    for regime in spec.rules.regime_overrides:
        add_condition_columns([*regime.when.all, *regime.when.any, *regime.when.none])
    for term in spec.rules.score.weighted_sum:
        add_column(term.column)
    if spec.rules.score.model_score is not None:
        for term in spec.rules.score.model_score.coefficients:
            add_column(term.column)
    if spec.rules.side_column is not None:
        add_column(spec.rules.side_column)
    columns.update(_order_required_columns(spec.rules.order))
    columns.update(_exit_required_columns(spec.rules.exit))
    columns.update(_sizing_required_columns(spec.rules.sizing))
    columns.update(_bracket_required_columns(spec.rules.bracket, derived_names))
    columns.update(_execution_required_columns(spec.rules.execution))
    columns.update(_portfolio_required_columns(spec.rules.portfolio))
    if spec.rules.cross_sectional.group_column is not None:
        columns.add(spec.rules.cross_sectional.group_column)
    columns.update(_risk_throttle_required_columns(spec.rules.risk_throttle))
    columns.update(_data_guard_required_columns(spec.rules.data_guard))
    for event_window in spec.rules.event_windows:
        columns.add(event_window.event_ts_column)
    columns.update(_multi_leg_required_columns(spec.rules.multi_leg.legs))
    return columns


def _all_conditions(spec: StrategyAuthoringSpec) -> list[Condition]:
    groups = [
        spec.rules.entry,
        spec.rules.long_entry,
        spec.rules.short_entry,
        spec.rules.hold,
        spec.rules.close,
        spec.rules.reduce,
        spec.rules.add,
        spec.rules.rebalance,
        *(regime.when for regime in spec.rules.regime_overrides),
    ]
    conditions: list[Condition] = []
    for group in groups:
        if group is not None:
            conditions.extend([*group.all, *group.any, *group.none])
    return conditions
