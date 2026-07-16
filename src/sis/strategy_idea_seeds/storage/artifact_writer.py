from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable


def write_json_atomic(path: Path, payload: Any) -> Path:
    text = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
            allow_nan=False,
        )
        + "\n"
    )
    return write_text_atomic(path, text)


def write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> Path:
    text = "".join(
        json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
            allow_nan=False,
        )
        + "\n"
        for row in rows
    )
    return write_text_atomic(path, text)


def write_text_atomic(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return path


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
