from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_selection import _score_value


@dataclass(frozen=True)
class _CrossSectionalRankSelection:
    percentile_by_id: dict[str, float]
    top_ids: set[str]
    bottom_ids: set[str]
    unscored_ids: set[str]


def _cross_sectional_rank_selection(
    timestamp_rows: list[dict[str, Any]],
    *,
    long_top_n: int | None,
    long_top_fraction: float | None,
    short_bottom_n: int | None,
    short_bottom_fraction: float | None,
) -> _CrossSectionalRankSelection:
    scored = [row for row in timestamp_rows if _score_value(row) is not None]
    unscored = [row for row in timestamp_rows if _score_value(row) is None]
    sorted_desc = sorted(scored, key=lambda item: _score_value(item) or 0.0, reverse=True)
    sorted_asc = list(reversed(sorted_desc))
    percentile_by_id: dict[str, float] = {}
    denominator = max(len(sorted_desc) - 1, 1)
    for index, row in enumerate(sorted_desc):
        percentile_by_id[str(row["signal_id"])] = (
            1.0 if len(sorted_desc) == 1 else 1.0 - (index / denominator)
        )

    top_n = _cross_sectional_selection_count(
        len(scored),
        fixed_count=long_top_n,
        fraction=long_top_fraction,
    )
    bottom_n = _cross_sectional_selection_count(
        len(scored),
        fixed_count=short_bottom_n,
        fraction=short_bottom_fraction,
    )
    top_ids = {str(row["signal_id"]) for row in sorted_desc[:top_n]}
    return _CrossSectionalRankSelection(
        percentile_by_id=percentile_by_id,
        top_ids=top_ids,
        bottom_ids={
            str(row["signal_id"])
            for row in sorted_asc[:bottom_n]
            if str(row["signal_id"]) not in top_ids
        },
        unscored_ids={str(row["signal_id"]) for row in unscored},
    )


def _cross_sectional_selection_count(
    candidate_count: int, *, fixed_count: int | None, fraction: float | None
) -> int:
    if fixed_count is not None:
        return fixed_count
    if fraction is None or candidate_count <= 0:
        return 0
    return max(1, math.ceil(candidate_count * fraction))
