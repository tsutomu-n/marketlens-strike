from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _CrossSectionalCandidateGroups:
    passthrough_rows: list[dict[str, Any]]
    missing_group_rows: list[dict[str, Any]]
    candidates_by_key: dict[tuple[Any, str | None], list[dict[str, Any]]]


def _cross_sectional_candidate_groups(
    rows: list[dict[str, Any]],
    *,
    group_column: str | None,
) -> _CrossSectionalCandidateGroups:
    passthrough_rows: list[dict[str, Any]] = []
    missing_group_rows: list[dict[str, Any]] = []
    candidates_by_key: dict[tuple[Any, str | None], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("side") == "none":
            passthrough_rows.append(row)
            continue
        group: str | None = None
        if group_column is not None:
            group = str(row.get("_cross_sectional_group") or "").strip()
            if not group:
                missing_group_rows.append(row)
                continue
        candidates_by_key.setdefault((row["ts_signal"], group), []).append(row)
    return _CrossSectionalCandidateGroups(
        passthrough_rows=passthrough_rows,
        missing_group_rows=missing_group_rows,
        candidates_by_key=candidates_by_key,
    )
