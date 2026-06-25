from __future__ import annotations

from typing import Any, Literal, cast


def _paper_preview_order_fields(*, row: dict[str, Any], selected: bool) -> dict[str, Any]:
    use_row = selected and bool(row)
    return {
        "entry_order_type": cast(
            Literal["market", "limit", "stop_market"],
            row.get("entry_order_type") if use_row else "market",
        ),
        "entry_limit_offset_bps": row.get("entry_limit_offset_bps") if use_row else None,
        "entry_stop_offset_bps": row.get("entry_stop_offset_bps") if use_row else None,
        "entry_timeout_minutes": row.get("entry_timeout_minutes") if use_row else None,
        "entry_time_in_force": cast(
            Literal["gtc", "gtd", "ioc", "fok"],
            row.get("entry_time_in_force") if use_row else "gtc",
        ),
        "entry_post_only": bool(row.get("entry_post_only")) if use_row else False,
        "entry_reduce_only": bool(row.get("entry_reduce_only")) if use_row else False,
    }
