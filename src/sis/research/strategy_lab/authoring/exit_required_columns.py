from __future__ import annotations

from sis.research.strategy_lab.authoring.contracts.trade_controls import ExitRules


def _exit_required_columns(exit_rules: ExitRules) -> set[str]:
    columns: set[str] = set()
    for column_name in (
        exit_rules.stop_loss_bps_column,
        exit_rules.min_stop_loss_bps_column,
        exit_rules.max_stop_loss_bps_column,
        exit_rules.take_profit_bps_column,
        exit_rules.min_take_profit_bps_column,
        exit_rules.max_take_profit_bps_column,
        exit_rules.min_reward_risk_ratio_column,
        exit_rules.trailing_stop_bps_column,
        exit_rules.trailing_stop_activation_bps_column,
        exit_rules.partial_take_profit_bps_column,
        exit_rules.partial_exit_fraction_column,
        exit_rules.min_holding_minutes_column,
        exit_rules.max_holding_minutes_column,
        exit_rules.reduce_fraction_column,
        exit_rules.add_fraction_column,
        exit_rules.rebalance_target_fraction_column,
        exit_rules.rebalance_min_delta_fraction_column,
    ):
        if column_name is not None:
            columns.add(column_name)
    return columns
