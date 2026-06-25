from __future__ import annotations

from typing import Any, Literal

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.core import EntryRules, ScoreRules
from sis.research.strategy_lab.authoring.contracts.spec import AuthoringRules
from sis.research.strategy_lab.authoring.features import _condition_passes
from sis.research.strategy_lab.authoring.compiler.signal_model_score import _model_score_value


def _entry_passes(row: dict[str, Any], entry: EntryRules) -> bool:
    all_pass = all(_condition_passes(row, condition) for condition in entry.all)
    any_pass = (
        True if not entry.any else any(_condition_passes(row, condition) for condition in entry.any)
    )
    none_pass = not any(_condition_passes(row, condition) for condition in entry.none)
    return all_pass and any_pass and none_pass


def _score(row: dict[str, Any], score: ScoreRules) -> float | None:
    if not score.enabled:
        return None
    total = 0.0
    used = False
    for term in score.weighted_sum:
        value = row.get(term.column)
        if isinstance(value, int | float):
            total += float(value) * term.weight
            used = True
    if score.model_score is not None:
        model_value = _model_score_value(row, score.model_score)
        if model_value is not None:
            total += model_value
            used = True
    return total if used else None


def _rank_score(raw_score: float | None) -> float | None:
    if raw_score is None:
        return None
    return max(0.0, min(1.0, raw_score))


def _tail_bucket(rank_score: float | None) -> str:
    if rank_score is None:
        return "none"
    if rank_score >= 0.8:
        return "top"
    if rank_score <= 0.2:
        return "bottom"
    return "middle"


def _score_value(row: dict[str, Any]) -> float | None:
    value = row.get("raw_score")
    return float(value) if isinstance(value, int | float) else None


def _side_from_column(row: dict[str, Any], column: str) -> Literal["long", "short", "none"]:
    value = str(row.get(column) or "").strip().lower()
    if value in {"buy", "bull", "long"}:
        return "long"
    if value in {"sell", "bear", "short"}:
        return "short"
    if value in {"", "hold", "none", "skip", "flat"}:
        return "none"
    raise StrategyAuthoringValidationError(f"Unsupported side value in {column}: {value}")


def _selected_side(
    row: dict[str, Any], rules: AuthoringRules
) -> tuple[Literal["long", "short", "none"] | None, str | None]:
    long_pass = _entry_passes(row, rules.long_entry) if rules.long_entry is not None else False
    short_pass = _entry_passes(row, rules.short_entry) if rules.short_entry is not None else False
    if long_pass and short_pass:
        return "none", "ambiguous_side"
    if long_pass:
        return "long", None
    if short_pass:
        return "short", None
    if rules.side_column is not None:
        if not _entry_passes(row, rules.entry):
            return None, None
        side = _side_from_column(row, rules.side_column)
        return (side, None) if side != "none" else ("none", "side_column_hold")
    if _entry_passes(row, rules.entry):
        if rules.side == "auto":
            if rules.cross_sectional.enabled:
                return "long", None
            return None, None
        return rules.side, None
    return None, None
