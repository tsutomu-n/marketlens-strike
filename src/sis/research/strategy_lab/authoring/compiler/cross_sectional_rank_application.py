from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import _block_trade_row
from sis.research.strategy_lab.authoring.compiler.cross_sectional_rank_selection import (
    _CrossSectionalRankSelection,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _score_value,
    _tail_bucket,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_cross_sectional_rank_result(
    *,
    row: dict[str, Any],
    rank_selection: _CrossSectionalRankSelection,
    spec: StrategyAuthoringSpec,
) -> dict[str, Any]:
    row_id = str(row["signal_id"])
    if row_id in rank_selection.unscored_ids:
        return _block_trade_row(
            row,
            spec=spec,
            block_reason="cross_sectional_score_missing",
        )

    updated = dict(row)
    percentile = rank_selection.percentile_by_id[row_id]
    updated["rank_score"] = percentile
    updated["percentile_rank"] = percentile
    updated["tail_bucket"] = _tail_bucket(percentile)
    if row_id in rank_selection.top_ids:
        if (
            spec.rules.cross_sectional.min_long_score is not None
            and (_score_value(row) or 0.0) < spec.rules.cross_sectional.min_long_score
        ):
            return _block_trade_row(
                updated,
                spec=spec,
                block_reason="cross_sectional_long_score_threshold",
            )
        updated["side"] = "long"
        updated["signal_id"] = _compiled_signal_id(spec, updated, side="long")
        updated["reason_codes"] = [
            *list(row.get("reason_codes") or []),
            "cross_sectional_top",
        ]
        return updated
    if row_id in rank_selection.bottom_ids:
        if (
            spec.rules.cross_sectional.max_short_score is not None
            and (_score_value(row) or 0.0) > spec.rules.cross_sectional.max_short_score
        ):
            return _block_trade_row(
                updated,
                spec=spec,
                block_reason="cross_sectional_short_score_threshold",
            )
        updated["side"] = "short"
        updated["signal_id"] = _compiled_signal_id(spec, updated, side="short")
        updated["reason_codes"] = [
            *list(row.get("reason_codes") or []),
            "cross_sectional_bottom",
        ]
        return updated
    return _block_trade_row(
        updated,
        spec=spec,
        block_reason="cross_sectional_rank_filter",
    )
