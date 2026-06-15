from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, cast

import polars as pl

from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.research.strategy_lab.authoring.backtest import run_authoring_backtest
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.io import load_authoring_spec


@dataclass(frozen=True)
class BacktestNoLookaheadDiffResult:
    diff_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _resolve_data_path(raw: str, data_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return data_dir.parent / path
    return path


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _stable_signal_rows(frame: pl.DataFrame, *, cutoff: datetime) -> list[dict[str, Any]]:
    ignored = {"generated_at", "parameter_hash"}
    rows: list[dict[str, Any]] = []
    for row in frame.sort(["ts_signal", "signal_id"]).to_dicts():
        ts_signal = _timestamp(row.get("ts_signal"))
        if ts_signal is None or ts_signal > cutoff:
            continue
        rows.append({key: _jsonable(value) for key, value in row.items() if key not in ignored})
    return rows


def _stable_backtest_rows(summary: dict[str, Any], *, cutoff: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_rows = summary.get("executed_signal_results")
    if not isinstance(raw_rows, list):
        return rows
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        row = cast(dict[str, Any], raw)
        ts_signal = _timestamp(row.get("ts_signal"))
        if ts_signal is None or ts_signal > cutoff:
            continue
        rows.append({str(key): _jsonable(value) for key, value in sorted(row.items())})
    return sorted(rows, key=lambda item: (str(item.get("ts_signal")), str(item.get("signal_id"))))


def _fingerprint(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _mutate_future_features(frame: pl.DataFrame, *, cutoff: datetime) -> pl.DataFrame:
    expressions: list[pl.Expr] = []
    future = pl.col("ts") > pl.lit(cutoff)
    for name, dtype in zip(frame.columns, frame.dtypes, strict=True):
        if name in {"ts", "canonical_symbol"}:
            continue
        if dtype.is_numeric():
            expressions.append(
                pl.when(future)
                .then((pl.col(name).cast(pl.Float64) * -17.0) + 12345.0)
                .otherwise(pl.col(name))
                .alias(name)
            )
        elif dtype == pl.Boolean:
            expressions.append(
                pl.when(future).then(~pl.col(name)).otherwise(pl.col(name)).alias(name)
            )
    return frame.with_columns(expressions) if expressions else frame


def _spec_with_feature_panel(
    spec: StrategyAuthoringSpec, feature_panel_path: Path
) -> StrategyAuthoringSpec:
    payload = spec.model_dump(mode="json")
    payload["data"]["feature_panel_path"] = feature_panel_path.as_posix()
    return StrategyAuthoringSpec.model_validate(payload)


def _runtime_future_mutation_checks(
    *,
    spec_path: Path,
    data_dir: Path,
    out_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    spec = load_authoring_spec(spec_path)
    feature_path = _resolve_data_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        raise FileNotFoundError(f"feature_panel_path not found: {feature_path}")
    feature = pl.read_parquet(feature_path).sort("ts")
    if "ts" not in feature.columns:
        raise ValueError("feature panel must include ts column for no-lookahead replay")
    timestamps = [_timestamp(value) for value in feature.get_column("ts").to_list()]
    normalized = [value for value in timestamps if value is not None]
    if len(normalized) < 4:
        return (
            [
                {
                    "check_id": "runtime_future_mutation_replay_skipped_insufficient_rows",
                    "passed": True,
                    "message": "feature panel has fewer than 4 timestamp rows; runtime replay is not applicable",
                }
            ],
            [],
            {
                "spec_path": spec_path.as_posix(),
                "spec_hash": _sha256_file(spec_path),
                "runtime_future_mutation_replay": False,
            },
        )
    cutoff = normalized[(len(normalized) // 2) - 1]
    replay_dir = out_dir / "runtime_replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    mutated_feature_path = replay_dir / "future_mutated_feature_panel.parquet"
    _mutate_future_features(feature, cutoff=cutoff).write_parquet(mutated_feature_path)

    baseline_frame, _baseline_manifest = build_authoring_signals(spec, data_dir=data_dir)
    _baseline_metrics, baseline_summary = run_authoring_backtest(
        spec, baseline_frame, data_dir=data_dir
    )
    mutated_spec = _spec_with_feature_panel(spec, mutated_feature_path)
    mutated_frame, _mutated_manifest = build_authoring_signals(mutated_spec, data_dir=data_dir)
    _mutated_metrics, mutated_summary = run_authoring_backtest(
        mutated_spec, mutated_frame, data_dir=data_dir
    )

    baseline_signals = _stable_signal_rows(baseline_frame, cutoff=cutoff)
    mutated_signals = _stable_signal_rows(mutated_frame, cutoff=cutoff)
    baseline_backtest = _stable_backtest_rows(baseline_summary, cutoff=cutoff)
    mutated_backtest = _stable_backtest_rows(mutated_summary, cutoff=cutoff)
    baseline_signal_hash = _fingerprint(baseline_signals)
    mutated_signal_hash = _fingerprint(mutated_signals)
    baseline_backtest_hash = _fingerprint(baseline_backtest)
    mutated_backtest_hash = _fingerprint(mutated_backtest)
    checks = [
        {
            "check_id": "runtime_future_mutation_replay",
            "passed": True,
            "message": "reran Strategy Authoring with future feature rows mutated",
        },
        {
            "check_id": "past_signal_rows_unchanged",
            "passed": baseline_signal_hash == mutated_signal_hash,
            "message": "signals at or before cutoff must not change when future feature rows mutate",
        },
        {
            "check_id": "past_executed_backtest_rows_unchanged",
            "passed": baseline_backtest_hash == mutated_backtest_hash,
            "message": "executed backtest rows at or before cutoff must not change when future feature rows mutate",
        },
    ]
    scenarios = [
        {
            "scenario_id": "future_feature_rows_numeric_bool_mutation",
            "cutoff_ts": cutoff.isoformat(),
            "feature_panel_path": feature_path.as_posix(),
            "mutated_feature_panel_path": mutated_feature_path.as_posix(),
            "mutated_feature_panel_hash": _sha256_file(mutated_feature_path),
            "baseline_past_signal_count": len(baseline_signals),
            "mutated_past_signal_count": len(mutated_signals),
            "baseline_past_signal_hash": baseline_signal_hash,
            "mutated_past_signal_hash": mutated_signal_hash,
            "baseline_past_backtest_count": len(baseline_backtest),
            "mutated_past_backtest_count": len(mutated_backtest),
            "baseline_past_backtest_hash": baseline_backtest_hash,
            "mutated_past_backtest_hash": mutated_backtest_hash,
        }
    ]
    meta = {
        "spec_path": spec_path.as_posix(),
        "spec_hash": _sha256_file(spec_path),
        "runtime_future_mutation_replay": True,
    }
    return checks, scenarios, meta


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest No-Lookahead Diff",
        "",
        f"- status: {payload['status']}",
        f"- check_count: {payload['summary']['check_count']}",
        f"- failed_count: {payload['summary']['failed_count']}",
        f"- diff_mode: {payload['diff_mode']}",
        f"- runtime_future_mutation_replay: {payload['summary']['runtime_future_mutation_replay']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Check | Passed | Message |",
        "|---|---:|---|",
    ]
    for row in payload["checks"]:
        lines.append(f"| {row['check_id']} | {row['passed']} | {row['message']} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_no_lookahead_diff(
    *,
    metrics_path: Path,
    signals_path: Path,
    quotes_path: Path,
    spec_path: Path | None = None,
    data_dir: Path | None = None,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestNoLookaheadDiffResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    executed_rows = summary.get("executed_signal_results")
    checks = [
        {
            "check_id": "metrics_source_exists",
            "passed": metrics_path.exists(),
            "message": "native metrics artifact exists",
        },
        {
            "check_id": "signals_source_exists",
            "passed": signals_path.exists(),
            "message": "signals artifact exists",
        },
        {
            "check_id": "quotes_source_exists",
            "passed": quotes_path.exists(),
            "message": "quotes artifact exists",
        },
        {
            "check_id": "executed_results_are_row_level",
            "passed": isinstance(executed_rows, list),
            "message": "native metrics expose row-level executed_signal_results for future differential replay",
        },
    ]
    scenarios: list[dict[str, Any]] = []
    runtime_meta: dict[str, Any] = {"runtime_future_mutation_replay": False}
    diff_mode = "static_artifact_guard_v0"
    if spec_path is not None and data_dir is not None:
        runtime_checks, scenarios, runtime_meta = _runtime_future_mutation_checks(
            spec_path=spec_path,
            data_dir=data_dir,
            out_dir=out_dir,
        )
        checks.extend(runtime_checks)
        diff_mode = "runtime_future_feature_mutation_v1"
    else:
        checks.append(
            {
                "check_id": "future_mutation_runtime_replay_skipped",
                "passed": True,
                "message": "runtime replay skipped because spec_path/data_dir were not provided",
            }
        )
    failed_count = sum(1 for row in checks if row["passed"] is not True)
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_no_lookahead_diff.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pass" if failed_count == 0 else "fail",
            "diff_mode": diff_mode,
            "source_backtest_metrics_path": metrics_path.as_posix(),
            "source_backtest_metrics_hash": _sha256_file(metrics_path),
            "source_signals_path": signals_path.as_posix(),
            "source_signals_hash": _sha256_file(signals_path) if signals_path.exists() else None,
            "source_quotes_path": quotes_path.as_posix(),
            "source_quotes_hash": _sha256_file(quotes_path) if quotes_path.exists() else None,
            "source_spec_path": spec_path.as_posix() if spec_path is not None else None,
            "source_spec_hash": _sha256_file(spec_path)
            if spec_path is not None and spec_path.exists()
            else None,
            "summary": {
                "check_count": len(checks),
                "failed_count": failed_count,
                "runtime_future_mutation_replay": runtime_meta["runtime_future_mutation_replay"],
            },
            "checks": checks,
            "mutation_scenarios": scenarios,
            "dependency_added": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_path = out_dir / "strategy_backtest_no_lookahead_diff.json"
    diff_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_no_lookahead_diff_report.md", payload
    )
    return BacktestNoLookaheadDiffResult(
        diff_path=diff_path, report_path=report_path, payload=payload
    )
