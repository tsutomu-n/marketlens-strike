from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import ValidationError, validate

from sis.storage.jsonl_store import read_json, read_jsonl


EVIDENCE_CARD_SCHEMA = {
    "type": "object",
    "required": ["run_id", "created_at", "scope", "data", "decision", "criteria", "blockers", "next_actions"],
    "properties": {
        "run_id": {"type": "string"},
        "created_at": {"type": "string"},
        "scope": {
            "type": "object",
            "required": ["venues", "symbols", "timeframes", "scalping_policy"],
        },
        "data": {"type": "object"},
        "decision": {"type": "string"},
        "venue_decisions": {"type": "array"},
        "criteria": {"type": "array"},
        "blockers": {"type": "array"},
        "next_actions": {"type": "array"},
    },
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationSummary:
    checked_files: int
    issues: list[ValidationIssue]


def _load_schema(schema_root: Path, name: str) -> dict:
    return json.loads((schema_root / name).read_text(encoding="utf-8"))


def _iter_files(path_pattern: str) -> list[Path]:
    return sorted(Path(path) for path in glob.glob(path_pattern))


def _latest_file(paths: list[Path]) -> list[Path]:
    return paths[-1:] if paths else []


def _read_json_list(path: Path) -> list[dict]:
    payload = read_json(path)
    return payload if isinstance(payload, list) else []


def _is_json_list(path: Path) -> bool:
    payload = read_json(path)
    return isinstance(payload, list)


def _is_json_dict(path: Path) -> bool:
    payload = read_json(path)
    return isinstance(payload, dict)


def _validate_json(path: Path, schema: dict, issues: list[ValidationIssue]) -> None:
    try:
        payload = read_json(path)
        validate(payload, schema)
    except (json.JSONDecodeError, ValidationError) as exc:
        issues.append(ValidationIssue(path=str(path), message=str(exc)))


def _validate_jsonl(path: Path, schema: dict, issues: list[ValidationIssue]) -> None:
    idx = -1
    try:
        for idx, row in enumerate(read_jsonl(path)):
            validate(row, schema)
    except (json.JSONDecodeError, ValidationError) as exc:
        issues.append(ValidationIssue(path=f"{path}#row={idx}", message=str(exc)))


def validate_artifacts(data_dir: Path, schema_root: Path, strict: bool = False) -> ValidationSummary:
    issues: list[ValidationIssue] = []
    checked_files = 0

    instrument_schema = _load_schema(schema_root, "instrument_registry.schema.json")
    quote_schema = _load_schema(schema_root, "quote_log_v1.schema.json")

    registry_files = [
        data_dir / "registry/gtrade_instrument_registry.json",
        data_dir / "registry/ostium_instrument_registry.json",
    ]
    for path in registry_files:
        if path.exists():
            _validate_json(path, {"type": "array", "items": instrument_schema}, issues)
            checked_files += 1
        elif strict:
            issues.append(ValidationIssue(path=str(path), message="Missing required registry artifact"))

    quote_files = _iter_files(str(data_dir / "raw/quotes/gtrade/*.jsonl")) + _iter_files(
        str(data_dir / "raw/quotes/ostium/*.jsonl")
    )
    if not quote_files and strict:
        issues.append(ValidationIssue(path=str(data_dir / "raw/quotes"), message="No quote JSONL artifacts found"))
    for path in quote_files:
        _validate_jsonl(path, quote_schema, issues)
        checked_files += 1

    backtest_metrics_path = data_dir / "research/backtest_metrics.json"
    if backtest_metrics_path.exists():
        if not _is_json_list(backtest_metrics_path):
            issues.append(
                ValidationIssue(path=str(backtest_metrics_path), message="backtest_metrics.json must be an array")
            )
        checked_files += 1
    elif strict:
        issues.append(ValidationIssue(path=str(backtest_metrics_path), message="Missing backtest_metrics.json"))

    evidence_files = _iter_files(str(data_dir / "evidence/evidence_card_*.json"))
    if not evidence_files and strict:
        issues.append(ValidationIssue(path=str(data_dir / "evidence"), message="No evidence card artifacts found"))
    for path in _latest_file(evidence_files):
        _validate_json(path, EVIDENCE_CARD_SCHEMA, issues)
        checked_files += 1

    execution_summary_files = [
        data_dir / "ops/execution_snapshot_summary.json",
        data_dir / "ops/execution_venue_comparison_summary.json",
        data_dir / "ops/execution_venue_diagnostics_summary.json",
        data_dir / "ops/execution_gap_history_summary.json",
        data_dir / "ops/execution_state_comparison_history_summary.json",
        data_dir / "ops/execution_snapshot_drift_history_summary.json",
        data_dir / "ops/execution_drift_overview_summary.json",
    ]
    for path in execution_summary_files:
        if path.exists():
            if not _is_json_dict(path):
                issues.append(
                    ValidationIssue(path=str(path), message=f"{path.name} must be a JSON object")
                )
            checked_files += 1
        elif strict:
            issues.append(
                ValidationIssue(path=str(path), message=f"Missing required execution summary artifact: {path.name}")
            )

    return ValidationSummary(checked_files=checked_files, issues=issues)
