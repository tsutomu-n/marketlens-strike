from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_ranked_rows import (
    _portfolio_exposure_ranked_rows,
)


def test_portfolio_exposure_ranked_rows_sort_rank_descending_and_missing_last() -> None:
    high = {"execution_symbol": "HIGH", "rank_score": 0.9}
    missing = {"execution_symbol": "MISSING"}
    none = {"execution_symbol": "NONE", "rank_score": None}
    low = {"execution_symbol": "LOW", "rank_score": 0.2}

    assert _portfolio_exposure_ranked_rows([missing, high, none, low]) == [
        high,
        low,
        missing,
        none,
    ]
