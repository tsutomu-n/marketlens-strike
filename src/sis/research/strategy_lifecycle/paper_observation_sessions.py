from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def latest_session(sessions: list[dict[str, Any]]) -> dict[str, Any] | None:
    return sessions[-1] if sessions else None


def session_sort_key(session: dict[str, Any]) -> tuple[datetime, str]:
    created_at = str(session.get("created_at") or "")
    try:
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed, str(session.get("session_id") or "")


def session_decision(session: dict[str, Any] | None) -> str:
    return str(session.get("review_decision") or "") if session else ""


def session_id(session: dict[str, Any] | None) -> str:
    return str(session.get("session_id") or "") if session else ""


def latest_normal_requirement_gaps(session: dict[str, Any] | None) -> dict[str, Any]:
    if session is None:
        return {
            "session_id": "",
            "available": False,
            "fills": count_gap(observed=0, required=0),
            "trading_days": count_gap(observed=0, required=0),
            "timestamp_quality": {
                "observed": "",
                "required": "complete",
                "met": False,
            },
        }
    thresholds = dict_field(session, "thresholds")
    metrics = dict_field(session, "metrics")
    required_fills = int_field(thresholds, "min_fills_for_pass")
    required_days = int_field(thresholds, "min_trading_days_for_pass")
    observed_fills = int_field(metrics, "fills_count")
    observed_days = int_field(metrics, "trading_day_count")
    timestamp_quality = str(metrics.get("timestamp_quality") or "")
    return {
        "session_id": session_id(session),
        "available": True,
        "fills": count_gap(observed=observed_fills, required=required_fills),
        "trading_days": count_gap(observed=observed_days, required=required_days),
        "timestamp_quality": {
            "observed": timestamp_quality,
            "required": "complete",
            "met": timestamp_quality == "complete",
        },
    }


def count_gap(*, observed: int, required: int) -> dict[str, int | bool]:
    return {
        "observed": observed,
        "required": required,
        "remaining": max(required - observed, 0),
        "met": required > 0 and observed >= required,
    }


def string_field(payload: dict[str, Any] | None, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get(key)
    return str(value) if value is not None else ""


def string_list(payload: dict[str, Any] | None, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def dict_field(payload: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def int_field(payload: dict[str, Any] | None, key: str) -> int:
    if not isinstance(payload, dict):
        return 0
    value = payload.get(key)
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return 0
    else:
        return 0
    return max(parsed, 0)
