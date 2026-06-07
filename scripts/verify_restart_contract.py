#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_git(
    repo_root: Path, args: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        capture_output=True,
        text=True,
    )


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    return _run_git(repo_root, args).stdout


def _refresh_index(repo_root: Path) -> None:
    _run_git(repo_root, ["update-index", "--refresh", "-q"], check=False)


def _status_entries(repo_root: Path) -> list[tuple[str, str]]:
    raw = _git_stdout(
        repo_root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    tokens = [token for token in raw.split("\0") if token]
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        status = token[:2]
        path = token[3:]
        entries.append((status, path))
        index += 1
        if ("R" in status or "C" in status) and index < len(tokens):
            index += 1
    return entries


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tracked_diff_sha256(repo_root: Path, path: str) -> str:
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", path],
        cwd=repo_root,
        check=True,
        capture_output=True,
    ).stdout
    return _sha256_bytes(diff)


def _file_sha256(repo_root: Path, path: str) -> str:
    return _sha256_bytes((repo_root / path).read_bytes())


def current_contract(repo_root: Path, ignored_paths: set[str] | None = None) -> dict[str, Any]:
    _refresh_index(repo_root)
    ignored_paths = ignored_paths or set()
    branch_output = _git_stdout(
        repo_root,
        ["status", "--short", "--branch", "--untracked-files=all"],
    )
    branch_line = branch_output.splitlines()[0] if branch_output.splitlines() else ""
    contract: dict[str, Any] = {
        "schema_version": 1,
        "head_short": _git_stdout(repo_root, ["rev-parse", "--short", "HEAD"]).strip(),
        "branch_line": branch_line,
        "tracked_dirty_files": [],
        "untracked_files": [],
        "ignored_dirty_files": [],
        "ignored_untracked_files": [],
    }

    tracked_dirty_files: list[dict[str, str]] = []
    untracked_files: list[dict[str, str]] = []
    for status, path in _status_entries(repo_root):
        if path in ignored_paths:
            continue
        if status == "??":
            untracked_files.append({"path": path, "sha256": _file_sha256(repo_root, path)})
        else:
            tracked_dirty_files.append(
                {"path": path, "diff_sha256": _tracked_diff_sha256(repo_root, path)}
            )

    contract["tracked_dirty_files"] = sorted(tracked_dirty_files, key=lambda item: item["path"])
    contract["untracked_files"] = sorted(untracked_files, key=lambda item: item["path"])
    return contract


def _frontmatter_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing YAML frontmatter")
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            return "\n".join(lines[1:index])
    raise ValueError(f"{path}: unterminated YAML frontmatter")


def load_contract(path: Path) -> dict[str, Any]:
    frontmatter = yaml.safe_load(_frontmatter_text(path)) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    if "restart_contract_json" in frontmatter:
        contract = json.loads(str(frontmatter["restart_contract_json"]))
    else:
        contract = frontmatter.get("restart_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{path}: missing restart_contract_json or restart_contract")
    return contract


def _fingerprint_map(
    files: object,
    fingerprint_key: str,
    ignored_paths: set[str],
) -> dict[str, str]:
    if not isinstance(files, list):
        return {}
    result: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        fingerprint = item.get(fingerprint_key)
        if isinstance(path, str) and isinstance(fingerprint, str) and path not in ignored_paths:
            result[path] = fingerprint
    return result


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def verify_contract(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if expected.get("schema_version") != 1:
        errors.append("schema_version_mismatch: expected schema_version=1")
    if expected.get("head_short") != actual.get("head_short"):
        errors.append(
            f"head_mismatch: expected {expected.get('head_short')} got {actual.get('head_short')}"
        )
    if expected.get("branch_line") != actual.get("branch_line"):
        errors.append(
            f"branch_line_mismatch: expected {expected.get('branch_line')} "
            f"got {actual.get('branch_line')}"
        )

    ignored_dirty = _string_set(expected.get("ignored_dirty_files"))
    ignored_untracked = _string_set(expected.get("ignored_untracked_files"))
    expected_dirty = _fingerprint_map(
        expected.get("tracked_dirty_files"),
        "diff_sha256",
        ignored_dirty,
    )
    actual_dirty = _fingerprint_map(
        actual.get("tracked_dirty_files"),
        "diff_sha256",
        ignored_dirty,
    )
    expected_untracked = _fingerprint_map(
        expected.get("untracked_files"),
        "sha256",
        ignored_untracked,
    )
    actual_untracked = _fingerprint_map(
        actual.get("untracked_files"),
        "sha256",
        ignored_untracked,
    )

    errors.extend(_compare_file_maps(expected_dirty, actual_dirty, "dirty"))
    errors.extend(_compare_file_maps(expected_untracked, actual_untracked, "untracked"))
    return errors


def _compare_file_maps(
    expected: dict[str, str],
    actual: dict[str, str],
    kind: str,
) -> list[str]:
    errors: list[str] = []
    for path in sorted(expected.keys() - actual.keys()):
        errors.append(f"expected_{kind}_missing: {path}")
    for path in sorted(actual.keys() - expected.keys()):
        errors.append(f"unexpected_{kind}_present: {path}")
    for path in sorted(expected.keys() & actual.keys()):
        if expected[path] != actual[path]:
            errors.append(f"fingerprint_mismatch: {path}")
    return errors


def _json_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True)


def _remove_top_level_key(lines: list[str], key: str) -> list[str]:
    prefix = f"{key}:"
    result: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith(prefix):
            index += 1
            while index < len(lines) and (lines[index].startswith(" ") or not lines[index]):
                index += 1
            continue
        result.append(line)
        index += 1
    return result


def _replace_scalar(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"{key}:"
    replacement = f"{key}: {json.dumps(value)}"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return [*lines[:index], replacement, *lines[index + 1 :]]
    return [replacement, *lines]


def refresh_handoff_contract(path: Path, contract: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing YAML frontmatter")
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            end = index
            break
    if end is None:
        raise ValueError(f"{path}: unterminated YAML frontmatter")

    frontmatter = lines[1:end]
    body = lines[end + 1 :]
    frontmatter = _remove_top_level_key(frontmatter, "restart_contract")
    frontmatter = _remove_top_level_key(frontmatter, "restart_contract_json")
    timestamp = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d_%H:%M JST")
    frontmatter = _replace_scalar(frontmatter, "updated_at_jst", timestamp)
    frontmatter.append("restart_contract_json: |")
    frontmatter.extend(f"  {line}" for line in _json_contract(contract).splitlines())

    new_text = "\n".join(["---", *frontmatter, "---", *body]) + "\n"
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(new_text, encoding="utf-8")
    os.replace(temp_path, path)


def _handoff_repo_path(repo_root: Path, handoff_path: Path) -> str | None:
    resolved = handoff_path.resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return None


def _ignore_handoff_file(
    contract: dict[str, Any],
    repo_root: Path,
    handoff_path: Path,
) -> dict[str, Any]:
    relative_path = _handoff_repo_path(repo_root, handoff_path)
    if relative_path is None:
        return contract
    result = dict(contract)
    ignored_dirty = list(_string_set(result.get("ignored_dirty_files")))
    ignored_untracked = list(_string_set(result.get("ignored_untracked_files")))
    if relative_path not in ignored_dirty:
        ignored_dirty.append(relative_path)
    if relative_path not in ignored_untracked:
        ignored_untracked.append(relative_path)
    result["ignored_dirty_files"] = sorted(ignored_dirty)
    result["ignored_untracked_files"] = sorted(ignored_untracked)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or refresh the repo restart contract.")
    parser.add_argument("--handoff", type=Path, default=Path(".ai_memory/HANDOFF.md"))
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--print-current-contract", action="store_true")
    parser.add_argument("--refresh-contract", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    handoff_path = args.handoff if args.handoff.is_absolute() else Path.cwd() / args.handoff
    handoff_repo_path = _handoff_repo_path(repo_root, handoff_path)
    ignored_paths = {handoff_repo_path} if handoff_repo_path else set()
    actual = current_contract(repo_root, ignored_paths=ignored_paths)
    if args.print_current_contract:
        print(_json_contract(actual))
        return 0
    if args.refresh_contract:
        refresh_handoff_contract(handoff_path, actual)
        print(f"refreshed restart contract: {handoff_path}")
        return 0

    expected = _ignore_handoff_file(load_contract(handoff_path), repo_root, handoff_path)
    errors = verify_contract(expected, actual)
    if errors:
        print("restart contract failed:")
        print("\n".join(errors))
        return 1
    print(
        "restart contract ok: "
        f"head={actual['head_short']}, "
        f"tracked_dirty={len(actual['tracked_dirty_files'])}, "
        f"untracked={len(actual['untracked_files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
