from __future__ import annotations

import gzip
import json
from pathlib import Path

from sis.crypto_perp.segments import (
    recover_committed_segments,
    read_gzip_jsonl,
    write_gzip_jsonl_segment,
)


def test_write_gzip_jsonl_segment_commits_atomically(tmp_path: Path) -> None:
    segment = write_gzip_jsonl_segment(
        tmp_path / "segments" / "part-000001.jsonl.gz",
        [
            {"ts_event": "2026-06-21T04:00:00Z", "value": 1},
            {"ts_event": "2026-06-21T04:00:01Z", "value": 2},
        ],
    )

    assert Path(segment.path).exists()
    assert not Path(segment.path + ".tmp").exists()
    assert segment.row_count == 2
    assert segment.min_ts == "2026-06-21T04:00:00Z"
    assert segment.max_ts == "2026-06-21T04:00:01Z"
    assert read_gzip_jsonl(Path(segment.path))[1]["value"] == 2


def test_recover_committed_segments_ignores_incomplete_tmp_files(tmp_path: Path) -> None:
    committed = write_gzip_jsonl_segment(tmp_path / "part-000001.jsonl.gz", [{"value": 1}])
    tmp_path.joinpath("part-000002.jsonl.gz.tmp").write_bytes(b"incomplete")

    recovered = recover_committed_segments(tmp_path)

    assert [item.path for item in recovered] == [committed.path]


def test_read_gzip_jsonl_reads_plain_json_rows(tmp_path: Path) -> None:
    path = tmp_path / "manual.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"value": "raw-first"}) + "\n")

    assert read_gzip_jsonl(path) == [{"value": "raw-first"}]
