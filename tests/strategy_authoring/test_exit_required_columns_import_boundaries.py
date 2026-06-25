from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_exit_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "stop_loss_bps_column",
        "min_stop_loss_bps_column",
        "max_stop_loss_bps_column",
        "take_profit_bps_column",
        "min_take_profit_bps_column",
        "max_take_profit_bps_column",
        "min_reward_risk_ratio_column",
        "trailing_stop_bps_column",
        "trailing_stop_activation_bps_column",
        "partial_take_profit_bps_column",
        "partial_exit_fraction_column",
        "min_holding_minutes_column",
        "max_holding_minutes_column",
        "reduce_fraction_column",
        "add_fraction_column",
        "rebalance_target_fraction_column",
        "rebalance_min_delta_fraction_column",
    }

    assert not any(name in text for name in forbidden)
