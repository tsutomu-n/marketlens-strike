from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc_aware(field_name: str, value: datetime | str) -> datetime:
    if isinstance(value, str):
        text = value.strip()
        if not text.endswith("Z"):
            raise ValueError(f"{field_name} must be UTC aware and serialized with Z")
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    else:
        parsed = value

    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must be UTC aware")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def serialize_utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be UTC aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
