from __future__ import annotations

import json
import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

import yaml

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SourceArtifact, SourceArtifactStatus


BOUNDARY_FLAG_KEYS = (
    "permits_live_order",
    "live_conversion_allowed",
    "wallet_used",
    "signing_used",
    "exchange_write_used",
    "venue_write_used",
)

BOUNDARY_TRUE_KEYS = {
    *BOUNDARY_FLAG_KEYS,
    "live_order_submitted",
    "credentials_used",
    "external_api_used",
}
SECRET_PATH_SEGMENTS = {
    ".env",
    ".env.local",
    ".envrc",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credential",
    "secrets",
    "secret",
}
URL_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def validate_review_id(review_id: str) -> str:
    if not REVIEW_ID_PATTERN.fullmatch(review_id):
        raise ValueError("review_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    return review_id


def _validate_relative_path_text(path_text: str) -> str:
    raw = path_text.strip()
    if raw in {"", "."}:
        raise ValueError("path must not be empty")
    if "\\" in raw:
        raise ValueError(f"path must use POSIX separators: {path_text}")
    if raw.startswith("/"):
        raise ValueError(f"path must be repository-relative: {path_text}")
    if URL_SCHEME_PATTERN.match(raw):
        raise ValueError(f"path must not include a URL scheme: {path_text}")
    path = PurePosixPath(raw)
    parts = path.parts
    if not parts:
        raise ValueError("path must not be empty")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"path must not contain dot or parent segments: {path_text}")
    for part in parts:
        lowered = part.lower()
        if part.startswith("."):
            raise ValueError(f"path must not include hidden path segments: {path_text}")
        if lowered in SECRET_PATH_SEGMENTS:
            raise ValueError(f"path must not include secret path segments: {path_text}")
    return path.as_posix()


def normalize_repo_relative_posix_path(path: str | Path, *, repo_root: Path | None = None) -> str:
    value = _validate_relative_path_text(str(path))
    root = (repo_root or Path.cwd()).resolve()
    resolved = (root / value).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {path}") from exc
    return value


def repo_relative_posix_path(path: Path, *, repo_root: Path | None = None) -> str:
    raw = str(path)
    if "\\" in raw:
        raise ValueError(f"path must use POSIX separators: {path}")
    root = (repo_root or Path.cwd()).resolve()
    if path.is_absolute():
        resolved = path.resolve(strict=False)
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path is outside repository: {path}") from exc
        return normalize_repo_relative_posix_path(relative.as_posix(), repo_root=root)
    return normalize_repo_relative_posix_path(raw, repo_root=root)


def repo_relative_path(path: Path, repo_root: Path | None = None) -> str:
    return repo_relative_posix_path(path, repo_root=repo_root)


def compute_sha256(path: Path) -> str:
    return sha256_file(path)


def compute_sha256_prefixed(path: Path) -> str:
    return compute_sha256(path)


def source_hash(path: Path) -> str:
    return compute_sha256(path)


def read_source_json(path: Path) -> dict[str, Any]:
    return read_json_object(path)


def detect_json_schema_version(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        if path.suffix.lower() == ".json":
            payload = read_json_object(path)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                return None
            payload = loaded
        else:
            return None
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError):
        return None
    value = payload.get("schema_version")
    return value if isinstance(value, str) else None


def collect_source_artifact(
    *,
    artifact_key: str,
    path: Path,
    required: bool,
    repo_root: Path | None = None,
    summary: dict[str, Any] | None = None,
) -> SourceArtifact:
    normalized_path = repo_relative_posix_path(path, repo_root=repo_root)
    if not path.exists():
        return SourceArtifact(
            artifact_key=artifact_key,
            path=normalized_path,
            exists=False,
            required=required,
            status=SourceArtifactStatus.MISSING,
            summary=summary or {},
        )
    digest = compute_sha256(path)
    byte_count = path.stat().st_size
    detected_schema_version = detect_json_schema_version(path)
    if path.suffix.lower() == ".json":
        try:
            read_json_object(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            invalid_summary = {**(summary or {}), "error": str(exc)}
            return SourceArtifact(
                artifact_key=artifact_key,
                path=normalized_path,
                exists=True,
                required=required,
                status=SourceArtifactStatus.INVALID,
                sha256=digest,
                bytes=byte_count,
                detected_schema_version=detected_schema_version,
                error=str(exc),
                summary=invalid_summary,
            )
    return SourceArtifact(
        artifact_key=artifact_key,
        path=normalized_path,
        exists=True,
        required=required,
        status=SourceArtifactStatus.PRESENT,
        sha256=digest,
        bytes=byte_count,
        detected_schema_version=detected_schema_version,
        summary=summary or {},
    )


def build_source_artifact(
    *,
    artifact_key: str,
    path: Path,
    required: bool,
    repo_root: Path | None = None,
) -> SourceArtifact:
    return collect_source_artifact(
        artifact_key=artifact_key,
        path=path,
        required=required,
        repo_root=repo_root,
    )


def observed_boundary_flags(payload: Any) -> dict[str, bool]:
    observed = dict.fromkeys(BOUNDARY_FLAG_KEYS, False)
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in observed and value is True:
                observed[key] = True
            child = observed_boundary_flags(value)
            for child_key, child_value in child.items():
                observed[child_key] = observed[child_key] or child_value
    elif isinstance(payload, list):
        for item in payload:
            child = observed_boundary_flags(item)
            for child_key, child_value in child.items():
                observed[child_key] = observed[child_key] or child_value
    return observed


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
