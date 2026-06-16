from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SourceArtifact, SourceArtifactStatus


BOUNDARY_FLAG_KEYS = {
    "permits_live_order",
    "live_conversion_allowed",
    "wallet_used",
    "signing_used",
    "exchange_write_used",
    "venue_write_used",
}

BOUNDARY_TRUE_KEYS = {
    *BOUNDARY_FLAG_KEYS,
    "live_order_submitted",
    "credentials_used",
    "external_api_used",
}


def validate_review_id(review_id: str) -> str:
    if not REVIEW_ID_PATTERN.fullmatch(review_id):
        raise ValueError("review_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    return review_id


def repo_relative_posix_path(path: Path, *, repo_root: Path | None = None) -> str:
    raw = str(path)
    if "\\" in raw:
        raise ValueError(f"path must use POSIX separators: {path}")
    if any(part == ".." for part in Path(raw).parts):
        raise ValueError(f"path must not contain ..: {path}")
    root = (repo_root or Path.cwd()).resolve()
    resolved = path.resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {path}") from exc
    value = relative.as_posix()
    if not value or value == ".":
        raise ValueError(f"path must be repository-relative file path: {path}")
    return value


def repo_relative_path(path: Path, repo_root: Path | None = None) -> str:
    return repo_relative_posix_path(path, repo_root=repo_root)


def compute_sha256_prefixed(path: Path) -> str:
    return sha256_file(path)


def source_hash(path: Path) -> str:
    return compute_sha256_prefixed(path)


def read_source_json(path: Path) -> dict[str, Any]:
    return read_json_object(path)


def build_source_artifact(
    *,
    artifact_key: str,
    path: Path,
    required: bool,
    repo_root: Path | None = None,
) -> SourceArtifact:
    if not path.exists():
        return SourceArtifact(
            artifact_key=artifact_key,
            path=repo_relative_posix_path(path, repo_root=repo_root),
            exists=False,
            required=required,
            status=SourceArtifactStatus.MISSING,
            summary={},
        )
    return SourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_posix_path(path, repo_root=repo_root),
        exists=True,
        required=required,
        status=SourceArtifactStatus.PRESENT,
        sha256=compute_sha256_prefixed(path),
        summary={},
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
