from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from sis.backtest.artifact_io import (
    artifact_row,
    json_artifact_payload,
    read_json_object,
    sha256_file,
    write_json_object,
)


def test_write_json_object_preserves_pack_artifact_formatting(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "artifact.json"
    payload = {"z": 1, "name": "日本語", "day": date(2026, 6, 15)}

    result = write_json_object(path, payload)

    assert result == path
    assert path.read_text(encoding="utf-8") == (
        '{\n  "day": "2026-06-15",\n  "name": "日本語",\n  "z": 1\n}\n'
    )


def test_read_json_object_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1, 2]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="expected JSON object"):
        read_json_object(path)


def test_artifact_row_reports_missing_and_existing_paths(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    assert artifact_row(missing) == {
        "path": missing.as_posix(),
        "exists": False,
        "sha256": None,
    }

    existing = tmp_path / "artifact.json"
    existing.write_text('{"ok": true}\n', encoding="utf-8")

    row = artifact_row(existing)

    assert row == {
        "path": existing.as_posix(),
        "exists": True,
        "sha256": sha256_file(existing),
    }
    assert row["sha256"].startswith("sha256:")


def test_json_artifact_payload_returns_object_or_none(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps({"ok": True}), encoding="utf-8")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    non_object = tmp_path / "non_object.json"
    non_object.write_text("[]", encoding="utf-8")
    text = tmp_path / "artifact.txt"
    text.write_text('{"ok": true}', encoding="utf-8")

    assert json_artifact_payload(valid) == {"ok": True}
    assert json_artifact_payload(invalid) is None
    assert json_artifact_payload(non_object) is None
    assert json_artifact_payload(text) is None
    assert json_artifact_payload(tmp_path / "missing.json") is None
