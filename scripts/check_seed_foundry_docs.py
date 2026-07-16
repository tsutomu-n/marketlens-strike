#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = REPO_ROOT / "資料/strategy-idea-seed-foundry-core-v1"
PLAN_PATH = BASE_DIR / "00_overview/core_v1_engineering_execution_plan.md"
CHECKLIST_PATH = BASE_DIR / "00_overview/core_v1_task_checklist.yaml"
CHECKPOINT_DIRS = {
    "A1": BASE_DIR / "A1_technical_walking_product/README.md",
    "A2": BASE_DIR / "A2_identity_archive_storage/README.md",
    "A3": BASE_DIR / "A3_ml_data_truth/README.md",
    "A4": BASE_DIR / "A4_ml_discovery_lane/README.md",
    "A5": BASE_DIR / "A5_llm_seed_lane/README.md",
    "A6": BASE_DIR / "A6_mutation_counterfactual_cross_lane/README.md",
    "A7": BASE_DIR / "A7_unified_archive_review/README.md",
    "A8": BASE_DIR / "A8_operational_release/README.md",
}
TASK_ROW_RE = re.compile(r"^\|\s*(A[1-8]-\d{2})\s*\|\s*(.*?)\s*\|")


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a YAML object")
    return payload


def _task_rows(path: Path, checkpoint_id: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = TASK_ROW_RE.match(line)
        if match is None or not match.group(1).startswith(f"{checkpoint_id}-"):
            continue
        task_id = match.group(1)
        title = match.group(2).strip()
        if task_id in seen:
            raise ValueError(f"{path.relative_to(REPO_ROOT)} contains duplicate task id: {task_id}")
        seen.add(task_id)
        rows.append((task_id, title))
    return rows


def _checklist_rows(payload: dict[str, Any], checkpoint_id: str) -> list[tuple[str, str]]:
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, list):
        raise ValueError("checkpoints must be a list")
    matches = [
        item for item in checkpoints if isinstance(item, dict) and item.get("id") == checkpoint_id
    ]
    if len(matches) != 1:
        raise ValueError(f"checklist must contain exactly one {checkpoint_id} checkpoint")
    tasks = matches[0].get("tasks")
    if not isinstance(tasks, list):
        raise ValueError(f"{checkpoint_id}.tasks must be a list")
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in tasks:
        if not isinstance(item, dict):
            raise ValueError(f"{checkpoint_id}.tasks entries must be objects")
        task_id = item.get("id")
        title = item.get("title")
        if not isinstance(task_id, str) or not isinstance(title, str):
            raise ValueError(f"{checkpoint_id}.tasks require string id and title")
        if task_id in seen:
            raise ValueError(f"checklist contains duplicate task id: {task_id}")
        seen.add(task_id)
        rows.append((task_id, title.strip()))
    return rows


def check_seed_foundry_docs() -> list[str]:
    errors: list[str] = []
    required_paths = [PLAN_PATH, CHECKLIST_PATH, *CHECKPOINT_DIRS.values()]
    for path in required_paths:
        if not path.is_file():
            errors.append(f"missing required Seed Foundry document: {path.relative_to(REPO_ROOT)}")
    if errors:
        return errors

    try:
        checklist = _read_yaml(CHECKLIST_PATH)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [f"invalid Seed Foundry checklist: {exc}"]

    expected_document = PLAN_PATH.relative_to(REPO_ROOT).as_posix()
    if checklist.get("document") != expected_document:
        errors.append(
            "Seed Foundry checklist document must point to canonical plan: "
            f"expected {expected_document!r}, got {checklist.get('document')!r}"
        )

    raw_checkpoints = checklist.get("checkpoints")
    if not isinstance(raw_checkpoints, list):
        errors.append("Seed Foundry checklist 'checkpoints' must be a list")
        return errors
    checkpoint_ids = [item.get("id") for item in raw_checkpoints if isinstance(item, dict)]
    if checkpoint_ids != list(CHECKPOINT_DIRS):
        errors.append(f"Seed Foundry checkpoints must be ordered A1..A8: got {checkpoint_ids!r}")

    for checkpoint_id, chunk_path in CHECKPOINT_DIRS.items():
        try:
            chunk_rows = _task_rows(chunk_path, checkpoint_id)
            checklist_rows = _checklist_rows(checklist, checkpoint_id)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue

        if not chunk_rows:
            errors.append(f"chunk README has no task rows for {checkpoint_id}")
            continue
        if chunk_rows != checklist_rows:
            errors.append(
                f"{checkpoint_id} task rows differ between chunk README and checklist: "
                f"chunk={chunk_rows!r}, checklist={checklist_rows!r}"
            )

    return errors


def main() -> None:
    errors = check_seed_foundry_docs()
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print("Seed Foundry Core v1 plan, chunk READMEs, and checklist are consistent")


if __name__ == "__main__":
    main()
