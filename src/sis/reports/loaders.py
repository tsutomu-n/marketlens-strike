from __future__ import annotations

from pathlib import Path
from typing import Callable

from sis.storage.jsonl_store import read_json


def safe_read_json_dict(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def safe_read_json_dict_list(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    payload = read_json(path)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def normalized_summary(path: Path | None, normalizer: Callable[[dict], dict]) -> dict:
    return normalizer(safe_read_json_dict(path))
