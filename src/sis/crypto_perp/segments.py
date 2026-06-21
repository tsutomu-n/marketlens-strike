from __future__ import annotations

from collections.abc import Sequence
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class CaptureSegmentRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    row_count: int
    min_ts: str | None = None
    max_ts: str | None = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ts_values(rows: Sequence[dict[str, Any]]) -> list[str]:
    values = []
    for row in rows:
        value = row.get("ts_event") or row.get("ts_received")
        if value is not None:
            values.append(str(value))
    return sorted(values)


def write_gzip_jsonl_segment(path: Path, rows: Sequence[dict[str, Any]]) -> CaptureSegmentRef:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(path.as_posix() + ".tmp")
    with gzip.open(tmp_path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            )
    tmp_path.replace(path)
    ts_values = _ts_values(rows)
    return CaptureSegmentRef(
        path=path.as_posix(),
        sha256=_sha256_file(path),
        row_count=len(rows),
        min_ts=ts_values[0] if ts_values else None,
        max_ts=ts_values[-1] if ts_values else None,
    )


def read_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("segment rows must be JSON objects")
                rows.append(payload)
    return rows


def recover_committed_segments(root: Path) -> list[CaptureSegmentRef]:
    refs: list[CaptureSegmentRef] = []
    for path in sorted(root.rglob("*.jsonl.gz")):
        rows = read_gzip_jsonl(path)
        ts_values = _ts_values(rows)
        refs.append(
            CaptureSegmentRef(
                path=path.as_posix(),
                sha256=_sha256_file(path),
                row_count=len(rows),
                min_ts=ts_values[0] if ts_values else None,
                max_ts=ts_values[-1] if ts_values else None,
            )
        )
    return refs
