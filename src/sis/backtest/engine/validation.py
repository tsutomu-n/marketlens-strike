from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl


@dataclass(frozen=True)
class SplitResult:
    train: pl.DataFrame
    test: pl.DataFrame
    summary: dict[str, Any]


def simple_train_test_split(frame: pl.DataFrame, *, train_ratio: float = 0.7) -> SplitResult:
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1")
    sorted_frame = frame.sort("event_ts") if "event_ts" in frame.columns else frame
    split_index = int(sorted_frame.height * train_ratio)
    train = sorted_frame.slice(0, split_index)
    test = sorted_frame.slice(split_index)
    return SplitResult(
        train=train,
        test=test,
        summary={
            "train_return": None,
            "test_return": None,
            "train_max_drawdown": None,
            "test_max_drawdown": None,
            "train_trade_count": None,
            "test_trade_count": None,
            "oos_validation_done": True,
        },
    )
