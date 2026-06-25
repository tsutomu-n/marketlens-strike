from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_portfolio_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "allocation_volatility_column",
        "allocation_beta_column",
        "target_total_position_weight_column",
        "max_total_position_weight_column",
        "max_long_position_weight_column",
        "max_short_position_weight_column",
        "max_abs_net_position_weight_column",
        "max_symbol_position_weight_column",
        "max_group_position_weight_column",
        "max_group_abs_net_position_weight_column",
        "turnover_weight_column",
    }

    assert not any(name in text for name in forbidden)
