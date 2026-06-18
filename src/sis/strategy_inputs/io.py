from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from sis.backtest.artifact_io import write_json_object


class StrategyInputIOError(ValueError):
    pass


def read_mapping_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StrategyInputIOError(f"failed to read {path}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            payload = json.loads(text)
        else:
            payload = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise StrategyInputIOError(f"invalid YAML/JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StrategyInputIOError(f"expected mapping payload: {path}")
    return payload


def write_json_artifact(path: Path, payload: dict[str, Any]) -> Path:
    tmp_path = path.parent / f".{path.name}.tmp"
    try:
        write_json_object(tmp_path, payload)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path


def write_text_artifact(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path
