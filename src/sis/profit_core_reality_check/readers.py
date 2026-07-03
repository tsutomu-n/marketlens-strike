from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import sha256_file
from sis.profit_core_reality_check.models import SourceRef


class RealityCheckReadError(ValueError):
    pass


def read_json_object_if_present(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RealityCheckReadError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RealityCheckReadError(f"expected JSON object: {path}")
    return payload


def read_jsonl_objects_if_present(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None or not path.exists():
        return None
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RealityCheckReadError(f"invalid JSONL: {path}:{line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise RealityCheckReadError(f"expected JSON object row: {path}:{line_number}")
        rows.append(payload)
    return rows


def source_ref(path: Path, payload: dict[str, Any] | None = None) -> SourceRef:
    schema_version = payload.get("schema_version") if payload else None
    return SourceRef(
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version if isinstance(schema_version, str) else None,
    )
