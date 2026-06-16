from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file


BOUNDARY_TRUE_KEYS = {
    "permits_live_order",
    "live_conversion_allowed",
    "live_order_submitted",
    "wallet_used",
    "venue_write_used",
    "signing_used",
    "credentials_used",
    "external_api_used",
    "exchange_write_used",
}


def repo_relative_path(path: Path, repo_root: Path | None = None) -> str:
    root = (repo_root or Path.cwd()).resolve()
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {path}") from exc


def source_hash(path: Path) -> str:
    return sha256_file(path)


def read_source_json(path: Path) -> dict[str, Any]:
    return read_json_object(path)


def boundary_true_paths(payload: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            if key in BOUNDARY_TRUE_KEYS and value is True:
                found.append(current)
            found.extend(boundary_true_paths(value, current))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            current = f"{prefix}[{index}]" if prefix else f"[{index}]"
            found.extend(boundary_true_paths(item, current))
    return found
