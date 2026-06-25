from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.strategy_review.manifest import StrategyReviewManifest
from sis.strategy_review.provenance import read_source_json


DEFAULT_BENCHMARK_RELATIVE_PATH = Path(
    "data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json"
)
DEFAULT_METRIC_EXTENSION_PATH = Path(
    "data/research/backtest_metric_extension/strategy_backtest_metric_extension.json"
)
DEFAULT_REPORT_EXTENSION_PATH = Path(
    "data/research/backtest_report_extension/strategy_backtest_report_extension.json"
)
DEFAULT_STRESS_PATH = Path("data/research/backtest_stress/strategy_backtest_stress.json")
DEFAULT_REGIME_SPLIT_PATH = Path(
    "data/research/backtest_regime_split/strategy_backtest_regime_split.json"
)
DEFAULT_ROLLING_STABILITY_PATH = Path(
    "data/research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
)
DEFAULT_DATA_AVAILABILITY_PATH = Path(
    "data/research/backtest_data_availability/backtest_data_availability_ledger.json"
)
DEFAULT_BASELINE_COMPARISON_PATH = Path(
    "data/research/backtest_baseline_comparison/strategy_backtest_baseline_comparison.json"
)
DEFAULT_TRIAL_LEDGER_PATH = Path(
    "data/research/backtest_trial_ledger/strategy_backtest_trial_ledger.json"
)
DEFAULT_ASSUMPTION_LEDGER_PATH = Path(
    "data/research/backtest_assumption_ledger/strategy_backtest_assumption_ledger.json"
)
DEFAULT_NO_LOOKAHEAD_PATH = Path(
    "data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json"
)
DEFAULT_EXECUTION_SIMULATION_PATH = Path(
    "data/research/backtest_execution_simulation/strategy_backtest_execution_simulation.json"
)
DEFAULT_COMPARISON_PATH = Path("data/research/backtest_compare/strategy_backtest_comparison.json")


def created_at_value(created_at: datetime | str | None) -> str:
    if isinstance(created_at, str):
        return created_at
    value = created_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_path(path: Path) -> Path:
    return path if path.is_absolute() else (Path.cwd() / path)


def summary_paths(pack_path: Path, validation_path: Path) -> dict[str, Path]:
    framework_run_path = pack_path.parent / "strategy_backtest_framework_run.json"
    if pack_path.parent.name == "backtest_pack" and pack_path.parent.parent.name == "research":
        framework_run_path = (
            pack_path.parent.parent / "backtest_framework_run/strategy_backtest_framework_run.json"
        )
    return {
        "pack_path": pack_path,
        "validation_path": validation_path,
        "framework_run_path": framework_run_path,
        "benchmark_relative_path": default_path(DEFAULT_BENCHMARK_RELATIVE_PATH),
        "metric_extension_path": default_path(DEFAULT_METRIC_EXTENSION_PATH),
        "report_extension_path": default_path(DEFAULT_REPORT_EXTENSION_PATH),
        "stress_path": default_path(DEFAULT_STRESS_PATH),
        "regime_split_path": default_path(DEFAULT_REGIME_SPLIT_PATH),
        "rolling_stability_path": default_path(DEFAULT_ROLLING_STABILITY_PATH),
        "data_availability_path": default_path(DEFAULT_DATA_AVAILABILITY_PATH),
        "baseline_comparison_path": default_path(DEFAULT_BASELINE_COMPARISON_PATH),
        "trial_ledger_path": default_path(DEFAULT_TRIAL_LEDGER_PATH),
        "assumption_ledger_path": default_path(DEFAULT_ASSUMPTION_LEDGER_PATH),
        "no_lookahead_path": default_path(DEFAULT_NO_LOOKAHEAD_PATH),
        "execution_simulation_path": default_path(DEFAULT_EXECUTION_SIMULATION_PATH),
        "comparison_path": default_path(DEFAULT_COMPARISON_PATH),
    }


def derive_authoring_spec_path(pack_path: Path) -> Path | None:
    if not pack_path.exists():
        return None
    try:
        payload = read_source_json(pack_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    raw_path = payload.get("spec_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else Path.cwd() / path


def manifest_json_payload(manifest: StrategyReviewManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    for artifact in payload["source_artifacts"]:
        for field_name in ("sha256", "bytes", "detected_schema_version", "error"):
            if artifact.get(field_name) is None:
                artifact.pop(field_name, None)
    return payload
