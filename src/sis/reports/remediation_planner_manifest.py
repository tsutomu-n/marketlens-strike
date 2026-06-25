from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.storage.jsonl_store import read_jsonl


def latest_planner_manifest(operation_chain_path: Path | None) -> dict[str, Any]:
    if operation_chain_path is None or not operation_chain_path.exists():
        return {}
    latest: dict[str, Any] = {}
    for item in read_jsonl(operation_chain_path):
        if isinstance(item, dict) and item.get("operation") == "remediation_planner_dry_run":
            latest = cast(dict[str, Any], item)
    return latest
