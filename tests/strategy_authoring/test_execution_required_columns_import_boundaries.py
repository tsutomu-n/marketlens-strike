from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_execution_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "slippage_bps_column",
        "max_fill_fraction_column",
        "min_fill_fraction_column",
        "max_spread_bps_column",
        "min_depth_usd_column",
        "max_latency_ms_column",
        "min_queue_position_score_column",
        "min_borrow_availability_ratio_column",
        "max_borrow_cost_bps_column",
        "max_tax_drag_bps_column",
        "max_turnover_pressure_column",
        "max_capacity_usage_ratio_column",
        "max_correlation_crowding_score_column",
        "min_fee_edge_bps_column",
    }

    assert not any(name in text for name in forbidden)
