from __future__ import annotations

from collections.abc import Callable, Sequence
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, TextIO

from pydantic import BaseModel, ConfigDict


class CaptureSegmentRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    row_count: int
    min_ts: str | None = None
    max_ts: str | None = None


def _fsync_parent(path: Path) -> None:
    try:
        directory_fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ts_values(rows: Sequence[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = row.get("ts_event") or row.get("ts_received")
        if value is not None:
            values.append(str(value))
    return sorted(values)


def write_gzip_jsonl_segment(
    path: Path,
    rows: Sequence[dict[str, Any]],
) -> CaptureSegmentRef:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(path.as_posix() + ".tmp")
    with gzip.open(tmp_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
    with tmp_path.open("rb") as committed:
        os.fsync(committed.fileno())
    os.replace(tmp_path, path)
    _fsync_parent(path)
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
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
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


class RotatingGzipJsonlWriter:
    """Small single-process rotating writer for public WebSocket capture rows."""

    def __init__(
        self,
        *,
        output_root: Path,
        capture_id: str,
        segment_seconds: int = 60,
        max_rows_per_segment: int = 10_000,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if segment_seconds <= 0:
            raise ValueError("segment_seconds must be positive")
        if max_rows_per_segment <= 0:
            raise ValueError("max_rows_per_segment must be positive")
        if not capture_id.strip():
            raise ValueError("capture_id must not be empty")
        self.output_root = output_root
        self.capture_id = capture_id
        self.segment_seconds = segment_seconds
        self.max_rows_per_segment = max_rows_per_segment
        self.monotonic_fn = monotonic_fn
        self.segment_refs: list[CaptureSegmentRef] = []
        self.bytes_written = 0
        self._segment_index = 0
        self._segment_started_monotonic: float | None = None
        self._segment_path: Path | None = None
        self._tmp_path: Path | None = None
        self._handle: TextIO | None = None
        self._row_count = 0
        self._ts_values_current: list[str] = []

    @property
    def current_row_count(self) -> int:
        return self._row_count

    def _start_segment(self, now: float) -> None:
        self._segment_index += 1
        directory = self.output_root / f"capture_id={self.capture_id}"
        directory.mkdir(parents=True, exist_ok=True)
        self._segment_path = directory / f"part-{self._segment_index:06d}.jsonl.gz"
        self._tmp_path = Path(self._segment_path.as_posix() + ".tmp")
        self._handle = gzip.open(self._tmp_path, "wt", encoding="utf-8")
        self._segment_started_monotonic = now
        self._row_count = 0
        self._ts_values_current = []

    def _should_rotate(self, now: float) -> bool:
        if self._handle is None or self._segment_started_monotonic is None:
            return False
        return (
            self._row_count >= self.max_rows_per_segment
            or now - self._segment_started_monotonic >= self.segment_seconds
        )

    def append(self, row: dict[str, Any]) -> None:
        now = self.monotonic_fn()
        if self._handle is None:
            self._start_segment(now)
        elif self._should_rotate(now):
            self.rotate()
            self._start_segment(now)
        assert self._handle is not None
        encoded = json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self._handle.write(encoded + "\n")
        self._row_count += 1
        ts_value = row.get("ts_event") or row.get("ts_received")
        if ts_value is not None:
            self._ts_values_current.append(str(ts_value))

    def rotate(self) -> CaptureSegmentRef | None:
        if self._handle is None:
            return None
        assert self._segment_path is not None
        assert self._tmp_path is not None
        self._handle.close()
        self._handle = None
        with self._tmp_path.open("rb") as committed:
            os.fsync(committed.fileno())
        os.replace(self._tmp_path, self._segment_path)
        _fsync_parent(self._segment_path)
        self.bytes_written += self._segment_path.stat().st_size
        ts_values = sorted(self._ts_values_current)
        ref = CaptureSegmentRef(
            path=self._segment_path.as_posix(),
            sha256=_sha256_file(self._segment_path),
            row_count=self._row_count,
            min_ts=ts_values[0] if ts_values else None,
            max_ts=ts_values[-1] if ts_values else None,
        )
        self.segment_refs.append(ref)
        self._segment_started_monotonic = None
        self._segment_path = None
        self._tmp_path = None
        self._row_count = 0
        self._ts_values_current = []
        return ref

    def close(self) -> list[CaptureSegmentRef]:
        self.rotate()
        return list(self.segment_refs)

    def __enter__(self) -> RotatingGzipJsonlWriter:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
