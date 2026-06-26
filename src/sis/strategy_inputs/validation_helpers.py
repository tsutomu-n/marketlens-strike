from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def contract_id_from_payload(payload: dict[str, Any]) -> str:
    value = payload.get("contract_id")
    return value if isinstance(value, str) and value else "unknown"


def idea_id_from_payload(payload: dict[str, Any]) -> str:
    value = payload.get("idea_id")
    return value if isinstance(value, str) and value else "unknown"


def missing_text(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return not isinstance(value, str) or not value.strip()


def missing_non_empty_list(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return not isinstance(value, list) or not value


def missing_mapping(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return not isinstance(value, dict) or not value


def parse_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialize_observed_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
