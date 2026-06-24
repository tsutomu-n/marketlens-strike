from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sis.reports.loaders import safe_read_json_dict, safe_read_json_dict_list

RunStatus = str


def parse_run_status(log_path: Path) -> RunStatus:
    if not log_path.exists():
        return "running"
    text = log_path.read_text(encoding="utf-8")
    if "Live evidence refresh completed" in text:
        return "completed"
    if "ERROR:" in text or "Traceback" in text or "Missing required" in text:
        return "failed"
    return "running"


def parse_manifest_status(manifest_path: Path | None) -> RunStatus | None:
    payload = safe_read_json_dict(manifest_path)
    status = payload.get("status")
    if isinstance(status, str):
        return status
    return None


def load_manifest_payload(manifest_path: Path | None) -> dict[str, Any]:
    return safe_read_json_dict(manifest_path)


def summary_from_payload(payload: dict[str, Any], key: str) -> dict[str, Any]:
    summary = payload.get(key)
    return summary if isinstance(summary, dict) else {}


def summary_from_manifest_or_evidence(
    manifest: dict[str, Any],
    evidence_payload: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    return summary_from_payload(manifest, key) or summary_from_payload(evidence_payload, key)


def extract_timestamp(line: str) -> str | None:
    if line.startswith("[") and "]" in line:
        return line[1 : line.index("]")]
    return None


def latest_evidence_card(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "evidence").glob("evidence_card_*.json"))
    return paths[-1] if paths else None


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_cost_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_backtest_metrics(path: Path) -> list[dict]:
    return safe_read_json_dict_list(path)


def started_finished(log_lines: list[str]) -> tuple[str | None, str | None]:
    started = None
    finished = None
    for line in log_lines:
        if "Scheduled live evidence run starting" in line and started is None:
            started = extract_timestamp(line)
        if "Live evidence refresh completed" in line:
            finished = extract_timestamp(line)
    return started, finished


def default_markdown_output_path(log_path: Path) -> Path:
    stem = log_path.stem.replace("live_evidence_", "")
    return Path("docs/live_evidence_reports") / f"live_evidence_report_{stem}.md"
