from __future__ import annotations

from pathlib import Path


def test_required_columns_delegates_risk_throttle_column_collection() -> None:
    text = Path("src/sis/research/strategy_lab/authoring/required_columns.py").read_text(
        encoding="utf-8"
    )

    forbidden = {
        "max_drawdown_column",
        "max_drawdown_floor_column",
        "daily_loss_column",
        "daily_loss_floor_column",
        "loss_streak_column",
        "max_loss_streak_column",
    }

    assert not any(name in text for name in forbidden)
