from __future__ import annotations
from typing import Any

from sis.research.strategy_lab.authoring.compiler.cross_sectional_groups import (
    _cross_sectional_candidate_groups,
)
from sis.research.strategy_lab.authoring.compiler.cross_sectional_rank_application import (
    _apply_cross_sectional_rank_result,
)
from sis.research.strategy_lab.authoring.compiler.cross_sectional_rank_selection import (
    _cross_sectional_rank_selection,
    _cross_sectional_selection_count as _cross_sectional_selection_count,
)
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _score_value,
)
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_cross_sectional_selection(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if not spec.rules.cross_sectional.enabled:
        return rows
    grouped = _cross_sectional_candidate_groups(
        rows,
        group_column=spec.rules.cross_sectional.group_column,
    )
    selected_rows: list[dict[str, Any]] = [
        *grouped.passthrough_rows,
        *(
            _block_trade_row(
                row,
                spec=spec,
                block_reason="cross_sectional_group_missing",
            )
            for row in grouped.missing_group_rows
        ),
    ]
    for timestamp_rows in grouped.candidates_by_key.values():
        scored = [row for row in timestamp_rows if _score_value(row) is not None]
        if (
            spec.rules.cross_sectional.min_candidates is not None
            and len(scored) < spec.rules.cross_sectional.min_candidates
        ):
            selected_rows.extend(
                _block_trade_row(row, spec=spec, block_reason="cross_sectional_min_candidates")
                for row in timestamp_rows
            )
            continue
        rank_selection = _cross_sectional_rank_selection(
            timestamp_rows,
            long_top_n=spec.rules.cross_sectional.long_top_n,
            long_top_fraction=spec.rules.cross_sectional.long_top_fraction,
            short_bottom_n=spec.rules.cross_sectional.short_bottom_n,
            short_bottom_fraction=spec.rules.cross_sectional.short_bottom_fraction,
        )
        for row in timestamp_rows:
            selected_rows.append(
                _apply_cross_sectional_rank_result(
                    row=row,
                    rank_selection=rank_selection,
                    spec=spec,
                )
            )
    return selected_rows
