from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, cast

import polars as pl
import typer

from sis.research.signal_builder import build_signals
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    read_strategy_signal_manifest,
    run_id_from_trial_group,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
)
from sis.research.strategy_lab.signal_registry import default_signal_generator_registry
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord


def _build_signals_or_exit(data_dir: Path, *, generator_id: str) -> Path:
    try:
        return build_signals(data_dir, generator_id=generator_id)
    except KeyError as exc:
        registered = ", ".join(default_signal_generator_registry().registered_ids())
        typer.echo(f"{exc.args[0]}; registered_generator_ids={registered}")
        raise typer.Exit(2) from exc


def _read_signal_manifest(data_dir: Path) -> StrategySignalManifest | None:
    path = strategy_signal_manifest_path(data_dir)
    return read_strategy_signal_manifest(path) if path.exists() else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _ndx_operator_promotion_evidence(data_dir: Path) -> dict[str, str | None]:
    path = data_dir / "research/ndx/operator_promotion_decision.json"
    return {
        "operator_promotion_path": path.as_posix() if path.exists() else None,
        "operator_promotion_hash": _sha256_file(path) if path.exists() else None,
    }


def _require_unique_signal_ids(frame: pl.DataFrame) -> None:
    if frame.is_empty():
        return
    if "signal_id" not in frame.columns:
        raise ValueError("Strategy signal artifact missing signal_id column.")
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in frame.get_column("signal_id").to_list():
        signal_id = str(value or "").strip()
        if not signal_id:
            raise ValueError("Strategy signal artifact contains empty signal_id.")
        if signal_id in seen and signal_id not in duplicates:
            duplicates.append(signal_id)
        seen.add(signal_id)
    if duplicates:
        sample = ", ".join(duplicates[:5])
        raise ValueError(f"Strategy signal artifact contains duplicate signal_id values: {sample}")


def _current_signal_context(
    data_dir: Path,
) -> tuple[pl.DataFrame, StrategySignalManifest | None, str]:
    signals_path = data_dir / "research/strategy_signals.parquet"
    if not signals_path.exists():
        raise FileNotFoundError(f"Strategy signal artifact not found: {signals_path}")
    frame = pl.read_parquet(signals_path)
    _require_unique_signal_ids(frame)
    manifest = _read_signal_manifest(data_dir)
    if frame.is_empty():
        if manifest is None:
            raise ValueError(
                "Empty strategy signal artifact requires strategy_signal_manifest.json."
            )
        return frame, manifest, manifest.signal_artifact_run_id
    run_id = signal_artifact_run_id(frame)
    if manifest is not None:
        if manifest.signal_count != frame.height:
            raise ValueError(
                "Strategy signal manifest signal_count does not match artifact: "
                f"{manifest.signal_count} != {frame.height}"
            )
        if manifest.signal_artifact_run_id != run_id:
            raise ValueError(
                "Strategy signal manifest run_id does not match artifact: "
                f"{manifest.signal_artifact_run_id} != {run_id}"
            )
    return frame, manifest, run_id


def _record_run_id(record: TrialRecord) -> str:
    value = record.metrics.get("signal_artifact_run_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return run_id_from_trial_group(record.trial_group_id)


def _default_trial_group_id_for_current_signal(
    records: list[TrialRecord], *, current_run_id: str
) -> str:
    if not current_run_id:
        return records[-1].trial_group_id
    matching_records = [record for record in records if _record_run_id(record) == current_run_id]
    if not matching_records:
        raise ValueError(
            f"No trial group matches current strategy signal artifact run_id: {current_run_id}"
        )
    return matching_records[-1].trial_group_id


def _latest_records_by_trial_id(records: list[TrialRecord]) -> list[TrialRecord]:
    by_id: dict[str, TrialRecord] = {}
    for record in records:
        by_id[record.trial_id] = record
    return sorted(by_id.values(), key=lambda item: (item.trial_index, item.trial_id))


def _scorecard_summary_from_trial_group(data_dir: Path, trial_group_id: str) -> dict[str, Any]:
    ledger = TrialLedger(data_dir / "research/trial_ledger.jsonl")
    records = [record for record in ledger.read_all() if record.trial_group_id == trial_group_id]
    if not records:
        return {}
    latest = _latest_records_by_trial_id(records)[-1]
    scorecard = latest.metrics.get("strategy_scorecard")
    if not isinstance(scorecard, dict):
        return {}
    keys = (
        "schema_version",
        "derived_feature_count",
        "signal_count",
        "side_counts",
        "block_reason_counts",
        "execution_block_reason_counts",
        "exit_reason_counts",
        "passed_thresholds",
        "failed_thresholds",
        "backtest_passed",
        "paper_only",
        "live_order_submitted",
    )
    return {key: scorecard[key] for key in keys if key in scorecard}


def _parse_rank_thresholds(value: str) -> list[float | None]:
    text = value.strip()
    if not text:
        return [None]
    thresholds: list[float | None] = []
    for item in text.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        threshold = float(candidate)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("rank thresholds must be between 0.0 and 1.0")
        thresholds.append(threshold)
    return thresholds or [None]


def _parameter_hash(
    *,
    run_id: str,
    rank_threshold: float | None,
    candidate_limit: int,
    split_method: str,
    era_unit: str,
) -> str:
    if (
        rank_threshold is None
        and candidate_limit == 1
        and split_method == "single_window"
        and era_unit == "trading_day"
    ):
        return f"generator-default-{run_id}"
    payload = json.dumps(
        {
            "rank_threshold": rank_threshold,
            "candidate_limit": candidate_limit,
            "split_method": split_method,
            "era_unit": era_unit,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _trial_id_for_parameters(run_id: str, parameter_hash: str) -> str:
    default_hash = f"generator-default-{run_id}"
    return (
        f"trial-{run_id}" if parameter_hash == default_hash else f"trial-{run_id}-{parameter_hash}"
    )


def _thresholded_signal_frame(frame: pl.DataFrame, rank_threshold: float | None) -> pl.DataFrame:
    if frame.is_empty() or rank_threshold is None:
        return frame
    return frame.filter(pl.col("rank_score").fill_null(-1.0) >= rank_threshold)


def _selected_signal_rows(frame: pl.DataFrame, *, candidate_limit: int) -> list[dict[str, Any]]:
    if frame.is_empty():
        return []
    sorted_frame = frame.sort(["ts_signal", "signal_id"], descending=[True, False])
    if candidate_limit > 0:
        sorted_frame = sorted_frame.head(candidate_limit)
    return sorted_frame.to_dicts()


def _candidate_selection_policy(candidate_limit: int) -> str:
    if candidate_limit == 1:
        return "latest_signal_by_ts"
    if candidate_limit == 0:
        return "all_threshold_passing_by_ts_desc"
    return f"top_{candidate_limit}_signals_by_ts_desc"


def _signal_rows_by_id(frame: pl.DataFrame) -> dict[str, dict[str, Any]]:
    if frame.is_empty():
        return {}
    return {str(row["signal_id"]): row for row in frame.to_dicts()}


def _signal_rows_for_record(frame: pl.DataFrame, record: TrialRecord) -> list[dict[str, Any]]:
    signal_by_id = _signal_rows_by_id(frame)
    selected_ids = record.metrics.get("selected_signal_ids")
    if not isinstance(selected_ids, list):
        fallback = record.metrics.get("selected_signal_id")
        selected_ids = [fallback] if isinstance(fallback, str) and fallback else []
    rows: list[dict[str, Any]] = []
    for signal_id in selected_ids:
        row = signal_by_id.get(str(signal_id))
        if row is not None:
            rows.append(row)
    return rows


def _era_key(value: object, era_unit: str) -> str:
    if isinstance(value, datetime):
        ts = value
    else:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if era_unit in {"session", "trading_day"}:
        return ts.date().isoformat()
    if era_unit == "week":
        year, week, _ = ts.isocalendar()
        return f"{year}-W{week:02d}"
    if era_unit == "month":
        return f"{ts.year:04d}-{ts.month:02d}"
    return ts.date().isoformat()


def _era_signal_counts(frame: pl.DataFrame, era_unit: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    if frame.is_empty():
        return counts
    for row in frame.select("ts_signal").to_dicts():
        key = _era_key(row["ts_signal"], era_unit)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _float_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _tail_bucket_value(
    value: object, *, selected: bool
) -> Literal["top", "middle", "bottom", "none"]:
    fallback = "top" if selected else "none"
    text = str(value or fallback)
    if text in {"top", "middle", "bottom", "none"}:
        return cast(Literal["top", "middle", "bottom", "none"], text)
    return "none"
