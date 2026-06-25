from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_order_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "entry_type_column",
        "limit_offset_bps_column",
        "stop_offset_bps_column",
        "timeout_minutes_column",
        "time_in_force_column",
        "post_only_column",
        "reduce_only_column",
    }

    assert not any(name in text for name in forbidden)
