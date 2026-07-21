#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "local_retention_manifest.v1"
DEFAULT_MANIFEST_NAME = "LOCAL_RETENTION_MANIFEST.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_files(root: Path, excluded: set[Path]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        resolved = path.resolve()
        if resolved in excluded:
            continue
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed in retention roots: {path}")
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"special file is not allowed in retention roots: {path}")
        files.append(path)
    return files


def _entries(root: Path, excluded: set[Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in _regular_files(root, excluded):
        file_stat = path.stat()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": file_stat.st_size,
                "mtime_ns": file_stat.st_mtime_ns,
                "sha256": _sha256(path),
            }
        )
    return entries


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_manifest(
    *,
    root: Path,
    classification: str,
    output: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    if not root.is_dir():
        raise ValueError(f"retention root is not a directory: {root}")
    if output != root and root not in output.parents:
        raise ValueError("manifest output must be inside the retention root")

    files = _entries(root, {output})
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _timestamp(),
        "root": str(root),
        "classification": classification,
        "policy": {
            "git_tracked": False,
            "deletion_default": "deny-until-reviewed",
            "integrity": "sha256",
        },
        "summary": {
            "file_count": len(files),
            "total_bytes": sum(entry["size_bytes"] for entry in files),
        },
        "files": files,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        json.dump(manifest, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(output)
    return manifest


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported manifest schema: {payload.get('schema_version')!r}")
    if not isinstance(payload.get("files"), list):
        raise ValueError("manifest files must be an array")
    return payload


def verify_manifest(*, root: Path, manifest_path: Path) -> list[str]:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    manifest = _load_manifest(manifest_path)
    if Path(manifest.get("root", "")).resolve() != root:
        raise ValueError("manifest root does not match requested retention root")

    current = {entry["path"]: entry for entry in _entries(root, {manifest_path})}
    expected = {entry["path"]: entry for entry in manifest["files"]}
    errors: list[str] = []

    for path in sorted(current.keys() - expected.keys()):
        errors.append(f"add: {path}")
    for path in sorted(current.keys() & expected.keys()):
        actual = current[path]
        recorded = expected[path]
        if actual["size_bytes"] != recorded.get("size_bytes") or actual["sha256"] != recorded.get(
            "sha256"
        ):
            errors.append(f"change: {path}")
    for path in sorted(expected.keys() - current.keys()):
        errors.append(f"delete: {path}")
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify a local-only SHA-256 retention manifest."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--classification", required=True)
    build.add_argument(
        "--out",
        type=Path,
        help=f"Defaults to ROOT/{DEFAULT_MANIFEST_NAME}.",
    )

    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument(
        "--manifest",
        type=Path,
        help=f"Defaults to ROOT/{DEFAULT_MANIFEST_NAME}.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = args.root.resolve()
    try:
        if args.command == "build":
            output = (args.out or root / DEFAULT_MANIFEST_NAME).resolve()
            manifest = build_manifest(
                root=root,
                classification=args.classification,
                output=output,
            )
            print(
                json.dumps(
                    {
                        "status": "built",
                        "manifest": str(output),
                        **manifest["summary"],
                    },
                    separators=(",", ":"),
                )
            )
            return 0

        manifest_path = (args.manifest or root / DEFAULT_MANIFEST_NAME).resolve()
        errors = verify_manifest(root=root, manifest_path=manifest_path)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        manifest = _load_manifest(manifest_path)
        print(
            json.dumps(
                {
                    "status": "verified",
                    "manifest": str(manifest_path),
                    **manifest["summary"],
                },
                separators=(",", ":"),
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
