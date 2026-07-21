from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_local_retention.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("audit_local_retention", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_and_verify_manifest_excludes_output_and_sorts_paths(
    tmp_path: Path,
) -> None:
    module = _load_script()
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "z.txt").write_text("last", encoding="utf-8")
    (root / "nested").mkdir()
    (root / "nested/a.bin").write_bytes(b"first")
    output = root / "LOCAL_RETENTION_MANIFEST.json"

    manifest = module.build_manifest(
        root=root,
        classification="unique-raw-evidence",
        output=output,
        generated_at="2026-07-21T21:44:00Z",
    )

    assert manifest["schema_version"] == "local_retention_manifest.v1"
    assert manifest["classification"] == "unique-raw-evidence"
    assert manifest["summary"] == {"file_count": 2, "total_bytes": 9}
    assert [entry["path"] for entry in manifest["files"]] == [
        "nested/a.bin",
        "z.txt",
    ]
    assert all(len(entry["sha256"]) == 64 for entry in manifest["files"])
    assert "LOCAL_RETENTION_MANIFEST.json" not in {entry["path"] for entry in manifest["files"]}
    assert json.loads(output.read_text(encoding="utf-8")) == manifest
    assert module.verify_manifest(root=root, manifest_path=output) == []


@pytest.mark.parametrize("drift", ["add", "change", "delete"])
def test_verify_manifest_reports_content_set_drift(
    tmp_path: Path,
    drift: str,
) -> None:
    module = _load_script()
    root = tmp_path / "evidence"
    root.mkdir()
    source = root / "source.bin"
    source.write_bytes(b"original")
    output = root / "LOCAL_RETENTION_MANIFEST.json"
    module.build_manifest(
        root=root,
        classification="historical-archive",
        output=output,
        generated_at="2026-07-21T21:44:00Z",
    )

    if drift == "add":
        (root / "added.bin").write_bytes(b"added")
    elif drift == "change":
        source.write_bytes(b"changed")
    else:
        source.unlink()

    errors = module.verify_manifest(root=root, manifest_path=output)

    assert errors
    assert drift in errors[0]


def test_build_manifest_rejects_symlinks(tmp_path: Path) -> None:
    module = _load_script()
    root = tmp_path / "evidence"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("do not follow", encoding="utf-8")
    (root / "link.txt").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        module.build_manifest(
            root=root,
            classification="historical-archive",
            output=root / "LOCAL_RETENTION_MANIFEST.json",
            generated_at="2026-07-21T21:44:00Z",
        )
