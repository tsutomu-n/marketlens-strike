from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


def read_mapping_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping in {path}")
    return payload


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_artifact_ref(path: Path, schema_version: str | None = None) -> dict[str, str]:
    ref = {"path": path.as_posix(), "sha256": f"sha256:{file_sha256(path)}"}
    if schema_version is not None:
        ref["schema_version"] = schema_version
    return ref


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text_artifact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
