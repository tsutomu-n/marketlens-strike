from __future__ import annotations

from typing import Any


def _portfolio_exposure_ranked_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
        reverse=True,
    )
