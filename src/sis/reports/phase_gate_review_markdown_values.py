from __future__ import annotations

from typing import Any, cast


def classification_counts(summary: dict[str, Any]) -> dict[str, object]:
    value = summary.get("execution_drift_classification_counts")
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [cast(dict[str, object], item) for item in value if isinstance(item, dict)]


def as_mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def as_str_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items() if isinstance(item, str)}


def as_list_mapping(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {str(key): as_str_list(item) for key, item in value.items()}
