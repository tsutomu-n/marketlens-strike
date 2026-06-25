from __future__ import annotations

from typing import Any


def _portfolio_exposure_groups(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[Any, list[dict[str, Any]]]]:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)
    return passthrough, grouped
