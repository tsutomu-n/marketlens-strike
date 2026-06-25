from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
    _minutes_value,
)


def _trade_bracket_fields(*, row: dict[str, Any], bracket: Any) -> dict[str, Any]:
    return {
        "bracket_type": bracket.bracket_type if bracket.enabled else "none",
        "bracket_time_stop_minutes": _minutes_value(
            row,
            fixed=bracket.time_stop_minutes if bracket.enabled else None,
            column=bracket.time_stop_minutes_column if bracket.enabled else None,
        ),
        "bracket_break_even_after_bps": _exit_bps(
            row,
            fixed=bracket.break_even_after_bps if bracket.enabled else None,
            column=bracket.break_even_after_bps_column if bracket.enabled else None,
        ),
        "bracket_break_even_after_partial_take_profit": (
            bracket.break_even_after_partial_take_profit if bracket.enabled else False
        ),
    }
