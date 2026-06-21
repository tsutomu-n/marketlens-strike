from __future__ import annotations

from typing import Any

from sis.strategy_review.operator_review import (
    OperatorReviewRecordResult,
    OperatorStrategyReview,
    record_operator_review,
    validate_existing_operator_review,
)

__all__ = [
    "OperatorReviewRecordResult",
    "OperatorStrategyReview",
    "StrategyReviewBuildResult",
    "build_strategy_review",
    "record_operator_review",
    "validate_existing_operator_review",
]


def __getattr__(name: str) -> Any:
    if name in {"StrategyReviewBuildResult", "build_strategy_review"}:
        from sis.strategy_review.service import StrategyReviewBuildResult, build_strategy_review

        return {
            "StrategyReviewBuildResult": StrategyReviewBuildResult,
            "build_strategy_review": build_strategy_review,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
