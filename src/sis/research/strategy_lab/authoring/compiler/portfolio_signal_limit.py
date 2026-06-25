from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_signal_limit(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    if spec.rules.portfolio.max_signals_per_timestamp is None:
        return rows
    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for item in rows:
        if item["side"] == "none":
            passthrough.append(item)
            continue
        grouped.setdefault(item["ts_signal"], []).append(item)
    limited: list[dict[str, Any]] = passthrough[:]
    limit = spec.rules.portfolio.max_signals_per_timestamp
    for timestamp_rows in grouped.values():
        limited.extend(
            sorted(
                timestamp_rows,
                key=lambda item: (
                    item.get("rank_score") if item.get("rank_score") is not None else -1.0
                ),
                reverse=True,
            )[:limit]
        )
    return limited
