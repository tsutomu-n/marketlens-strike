from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, cast

RequirementStatus = Literal["pass", "fail", "known_gap"]


def dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def requirement(
    *,
    key: str,
    status: RequirementStatus,
    evidence_path: Path | None,
    details: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "status": status,
        "evidence_path": str(evidence_path) if evidence_path is not None else None,
        "reason": reason,
        "details": details or {},
    }


def nonzero_counts(payload: Any) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    counts: dict[str, int] = {}
    for key, value in payload.items():
        try:
            count = int(value or 0)
        except (TypeError, ValueError):
            continue
        if count > 0:
            counts[str(key)] = count
    return counts
