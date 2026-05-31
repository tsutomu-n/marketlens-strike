from __future__ import annotations

import hashlib
import json

EXIT_PRIORITY_ITEMS = (
    "break_even_stop",
    "stop_loss",
    "partial_take_profit",
    "take_profit",
    "trailing_stop",
    "time_stop",
)
DEFAULT_EXIT_PRIORITY = ",".join(EXIT_PRIORITY_ITEMS)

ALLOWED_OPERATORS = {
    "gt",
    "gte",
    "lt",
    "lte",
    "eq",
    "neq",
    "is_true",
    "is_false",
    "between",
    "in",
    "not_in",
    "crosses_above",
    "crosses_below",
    "rising",
    "falling",
    "consecutive_gt",
    "consecutive_gte",
    "consecutive_lt",
    "consecutive_lte",
    "consecutive_eq",
    "consecutive_neq",
}
VALID_THROUGH = {"signals", "backtest", "paper-preview"}


def _stable_digest(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class StrategyAuthoringValidationError(ValueError):
    pass
