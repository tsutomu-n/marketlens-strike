from __future__ import annotations

import math
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
)
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _score_value,
    _tail_bucket,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_cross_sectional_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.cross_sectional.enabled:
        return rows
    passthrough = [row for row in rows if row.get("side") == "none"]
    candidates_by_timestamp: dict[tuple[Any, str | None], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("side") == "none":
            continue
        group: str | None = None
        if spec.rules.cross_sectional.group_column is not None:
            group = str(row.get("_cross_sectional_group") or "").strip()
            if not group:
                passthrough.append(
                    _block_trade_row(
                        row,
                        spec=spec,
                        block_reason="cross_sectional_group_missing",
                    )
                )
                continue
        candidates_by_timestamp.setdefault((row["ts_signal"], group), []).append(row)

    selected_rows: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in candidates_by_timestamp.values():
        scored = [row for row in timestamp_rows if _score_value(row) is not None]
        unscored = [row for row in timestamp_rows if _score_value(row) is None]
        if (
            spec.rules.cross_sectional.min_candidates is not None
            and len(scored) < spec.rules.cross_sectional.min_candidates
        ):
            selected_rows.extend(
                _block_trade_row(row, spec=spec, block_reason="cross_sectional_min_candidates")
                for row in timestamp_rows
            )
            continue
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
            fixed_count=spec.rules.cross_sectional.long_top_n,
            fraction=spec.rules.cross_sectional.long_top_fraction,
        )
        bottom_n = _cross_sectional_selection_count(
            len(scored),
            fixed_count=spec.rules.cross_sectional.short_bottom_n,
            fraction=spec.rules.cross_sectional.short_bottom_fraction,
        )
        unscored_ids = {str(row["signal_id"]) for row in unscored}
        top_ids = {str(row["signal_id"]) for row in sorted_desc[:top_n]}
        bottom_ids = {
            str(row["signal_id"])
            for row in sorted_asc[:bottom_n]
            if str(row["signal_id"]) not in top_ids
        }
        for row in timestamp_rows:
            row_id = str(row["signal_id"])
            if row_id in unscored_ids:
                selected_rows.append(
                    _block_trade_row(
                        row,
                        spec=spec,
                        block_reason="cross_sectional_score_missing",
                    )
                )
                continue
            updated = dict(row)
            percentile = percentile_by_id[row_id]
            updated["rank_score"] = percentile
            updated["percentile_rank"] = percentile
            updated["tail_bucket"] = _tail_bucket(percentile)
            if row_id in top_ids:
                if (
                    spec.rules.cross_sectional.min_long_score is not None
                    and (_score_value(row) or 0.0) < spec.rules.cross_sectional.min_long_score
                ):
                    selected_rows.append(
                        _block_trade_row(
                            updated,
                            spec=spec,
                            block_reason="cross_sectional_long_score_threshold",
                        )
                    )
                    continue
                updated["side"] = "long"
                updated["signal_id"] = _compiled_signal_id(spec, updated, side="long")
                updated["reason_codes"] = [
                    *list(row.get("reason_codes") or []),
                    "cross_sectional_top",
                ]
                selected_rows.append(updated)
            elif row_id in bottom_ids:
                if (
                    spec.rules.cross_sectional.max_short_score is not None
                    and (_score_value(row) or 0.0) > spec.rules.cross_sectional.max_short_score
                ):
                    selected_rows.append(
                        _block_trade_row(
                            updated,
                            spec=spec,
                            block_reason="cross_sectional_short_score_threshold",
                        )
                    )
                    continue
                updated["side"] = "short"
                updated["signal_id"] = _compiled_signal_id(spec, updated, side="short")
                updated["reason_codes"] = [
                    *list(row.get("reason_codes") or []),
                    "cross_sectional_bottom",
                ]
                selected_rows.append(updated)
            else:
                selected_rows.append(
                    _block_trade_row(
                        updated,
                        spec=spec,
                        block_reason="cross_sectional_rank_filter",
                    )
                )
    return selected_rows


def _cross_sectional_selection_count(
    candidate_count: int, *, fixed_count: int | None, fraction: float | None
) -> int:
    if fixed_count is not None:
        return fixed_count
    if fraction is None or candidate_count <= 0:
        return 0
    return max(1, math.ceil(candidate_count * fraction))
