from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_sizing_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "position_weight_column",
        "notional_usd_column",
        "volatility_column",
    }

    assert not any(name in text for name in forbidden)
