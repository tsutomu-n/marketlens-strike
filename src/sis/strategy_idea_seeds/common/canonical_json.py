from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
from typing import Any


CANONICALIZATION_VERSION = "seed-domain-canonicalization-v1"


def normalize_canonical(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and Infinity are not canonical values")
        return _decimal_string(Decimal(str(value)))
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("NaN and Infinity are not canonical values")
        return _decimal_string(value)
    if isinstance(value, datetime):
        timestamp = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return (
            timestamp.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(key): normalize_canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list | tuple):
        return [normalize_canonical(item) for item in value]
    if isinstance(value, set | frozenset):
        normalized = [normalize_canonical(item) for item in value]
        return sorted(normalized, key=canonical_json)
    if hasattr(value, "model_dump"):
        return normalize_canonical(value.model_dump(mode="json", exclude_none=True))
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        normalize_canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"-0", ""} else text
