from __future__ import annotations

from typing import Any

import polars as pl


def _paper_preview_selected_rows(frame: pl.DataFrame) -> list[dict[str, Any]]:
    return [
        row
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower() in {"long", "short"}
        and not list(row.get("block_reasons") or [])
    ][:1]
