from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
import logging
import math
from pathlib import Path
from typing import Any
import warnings

from sis.backtest.artifact_io import (
    read_json_object as _read_json,
    sha256_file as _sha256_file,
    write_json_object,
)
from sis.backtest.boundary import with_no_live_capability_boundary
from sis.backtest.frameworks import framework_adapter_status
from sis.backtest.optional_dependencies import optional_dependency_source
from sis.backtest.reporting import write_markdown_report


@dataclass(frozen=True)
class BacktestReportExtensionResult:
    report_extension_path: Path
    returns_series_path: Path
    quantstats_html_path: Path | None
    report_path: Path
    payload: dict[str, Any]


def _quantstats_candidate() -> dict[str, Any]:
    for candidate in framework_adapter_status():
        if candidate.get("framework_id") == "quantstats":
            return candidate
    return {
        "framework_id": "quantstats",
        "adapter_role": "report_only_candidate",
        "status": "not_installed",
        "version": None,
    }


def _dependency_source(candidate: dict[str, Any]) -> str:
    return optional_dependency_source(
        candidate,
        extra_name="reports",
        dependency_prefixes={"quantstats==", "quantstats>="},
    )


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def _returns_rows(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(summary.get("executed_signal_results") or []):
        if not isinstance(raw, dict):
            continue
        signal_return = _numeric(raw.get("signal_return"))
        if signal_return is None:
            continue
        rows.append(
            {
                "index": index,
                "ts_signal": raw.get("ts_signal"),
                "signal_id": raw.get("signal_id"),
                "canonical_symbol": raw.get("canonical_symbol"),
                "side": raw.get("side"),
                "signal_return": signal_return,
            }
        )
    return rows


def _write_returns_series(
    *,
    path: Path,
    rows: list[dict[str, Any]],
    source_backtest_metrics_path: Path,
    frequency: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {
                        "source_backtest_metrics_path": source_backtest_metrics_path.as_posix(),
                        "frequency": frequency,
                        **row,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return path


def _periods_per_year(frequency: str) -> int:
    return {"daily": 252, "weekly": 52, "monthly": 12}.get(frequency, 252)


def _metrics_row_count(metrics_table: Any) -> int | None:
    shape = getattr(metrics_table, "shape", None)
    if isinstance(shape, tuple) and shape:
        first = shape[0]
        return first if isinstance(first, int) else None
    try:
        return len(metrics_table)
    except TypeError:
        return None


def _framework_warning_rows(
    captured_warnings: list[warnings.WarningMessage],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for captured in captured_warnings:
        row = {
            "category": captured.category.__name__,
            "message": str(captured.message),
        }
        key = (row["category"], row["message"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _show_captured_warnings(captured_warnings: list[warnings.WarningMessage]) -> None:
    for captured in captured_warnings:
        warnings.showwarning(
            captured.message,
            captured.category,
            captured.filename,
            captured.lineno,
            captured.file,
            captured.line,
        )


def _set_logger_level(name: str, level: int) -> int:
    logger = logging.getLogger(name)
    previous_level = logger.level
    logger.setLevel(level)
    return previous_level


def _restore_logger_level(name: str, level: int) -> None:
    logging.getLogger(name).setLevel(level)


def _returns_series(rows: list[dict[str, Any]], returns: list[float], pandas: Any) -> Any:
    timestamps = [row.get("ts_signal") for row in rows]
    index = None
    if timestamps and all(isinstance(ts, str) and ts for ts in timestamps):
        to_datetime = getattr(pandas, "to_datetime", None)
        if callable(to_datetime):
            try:
                index = to_datetime(timestamps, utc=True, errors="coerce")
                tz_convert = getattr(index, "tz_convert", None)
                if callable(tz_convert):
                    index = tz_convert(None)
            except Exception:
                index = None
    if index is None:
        date_range = getattr(pandas, "date_range", None)
        if callable(date_range):
            index = date_range("1970-01-01", periods=len(returns), freq="D")
    return pandas.Series(returns, index=index, dtype="float64")


def _base_payload(
    *,
    candidate: dict[str, Any],
    metrics_path: Path,
    returns_series_path: Path,
    quantstats_html_path: Path | None,
    frequency: str,
    risk_free_rate: float,
    return_count: int,
    report_status: str,
    reason_codes: list[str],
    engine_run: bool,
    runner_mode: str,
    dependency_source: str,
    framework_warnings: list[dict[str, str]] | None = None,
    metrics_table_row_count: int | None = None,
) -> dict[str, Any]:
    selected_warnings = framework_warnings or []
    return with_no_live_capability_boundary(
        {
            "schema_version": "strategy_backtest_report_extension.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "framework_id": "quantstats",
            "adapter_role": str(candidate.get("adapter_role") or "report_only_candidate"),
            "framework_version": candidate.get("version"),
            "runner_mode": runner_mode,
            "dependency_source": dependency_source,
            "report_status": report_status,
            "reason_codes": reason_codes,
            "dependency_added": False,
            "engine_run": engine_run,
            "source_backtest_metrics_path": metrics_path.as_posix(),
            "source_backtest_metrics_hash": _sha256_file(metrics_path),
            "returns_series_path": returns_series_path.as_posix(),
            "returns_series_hash": _sha256_file(returns_series_path),
            "quantstats_html_path": quantstats_html_path.as_posix()
            if quantstats_html_path is not None
            else None,
            "quantstats_html_hash": _sha256_file(quantstats_html_path)
            if quantstats_html_path is not None and quantstats_html_path.exists()
            else None,
            "frequency": frequency,
            "risk_free_rate": risk_free_rate,
            "periods_per_year": _periods_per_year(frequency),
            "return_count": return_count,
            "framework_warning_count": len(selected_warnings),
            "framework_warnings": selected_warnings,
            "metrics_table_row_count": metrics_table_row_count,
        }
    )


def _run_quantstats_payload(
    *,
    candidate: dict[str, Any],
    metrics_path: Path,
    returns_series_path: Path,
    quantstats_html_path: Path,
    rows: list[dict[str, Any]],
    returns: list[float],
    frequency: str,
    risk_free_rate: float,
    suppress_framework_warnings: bool,
) -> dict[str, Any]:
    captured_warnings: list[warnings.WarningMessage] = []
    previous_font_manager_level = _set_logger_level("matplotlib.font_manager", logging.ERROR)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                quantstats = importlib.import_module("quantstats")
                pandas = importlib.import_module("pandas")
                series = _returns_series(rows, returns, pandas)
                periods_per_year = _periods_per_year(frequency)
                quantstats_html_path.parent.mkdir(parents=True, exist_ok=True)
                quantstats.reports.html(
                    series,
                    rf=risk_free_rate,
                    output=str(quantstats_html_path),
                    title="Strategy Backtest QuantStats Report",
                    periods_per_year=periods_per_year,
                )
                metrics_table = quantstats.reports.metrics(
                    series,
                    rf=risk_free_rate,
                    display=False,
                    mode="basic",
                    periods_per_year=periods_per_year,
                )
            finally:
                captured_warnings = list(caught)
    except Exception:
        if not suppress_framework_warnings:
            _show_captured_warnings(captured_warnings)
        return _base_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            quantstats_html_path=quantstats_html_path if quantstats_html_path.exists() else None,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            return_count=len(returns),
            report_status="failed",
            reason_codes=["framework_report_run_failed"],
            engine_run=False,
            runner_mode="temporary_or_optional_import",
            dependency_source=_dependency_source(candidate),
            framework_warnings=_framework_warning_rows(captured_warnings),
        )
    finally:
        _restore_logger_level("matplotlib.font_manager", previous_font_manager_level)
    if not suppress_framework_warnings:
        _show_captured_warnings(captured_warnings)
    return _base_payload(
        candidate=candidate,
        metrics_path=metrics_path,
        returns_series_path=returns_series_path,
        quantstats_html_path=quantstats_html_path,
        frequency=frequency,
        risk_free_rate=risk_free_rate,
        return_count=len(returns),
        report_status="completed",
        reason_codes=[],
        engine_run=True,
        runner_mode="temporary_or_optional_import",
        dependency_source=_dependency_source(candidate),
        framework_warnings=_framework_warning_rows(captured_warnings),
        metrics_table_row_count=_metrics_row_count(metrics_table),
    )


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Report Extension",
        "",
        f"- framework_id: {payload['framework_id']}",
        f"- framework_version: {payload['framework_version']}",
        f"- runner_mode: {payload['runner_mode']}",
        f"- dependency_source: {payload['dependency_source']}",
        f"- report_status: {payload['report_status']}",
        f"- engine_run: {payload['engine_run']}",
        f"- source_backtest_metrics_path: `{payload['source_backtest_metrics_path']}`",
        f"- returns_series_path: `{payload['returns_series_path']}`",
        f"- quantstats_html_path: `{payload['quantstats_html_path']}`",
        f"- frequency: {payload['frequency']}",
        f"- periods_per_year: {payload['periods_per_year']}",
        f"- return_count: {payload['return_count']}",
        f"- framework_warning_count: {payload['framework_warning_count']}",
        f"- metrics_table_row_count: {payload['metrics_table_row_count']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
    ]
    return write_markdown_report(path, lines)


def build_strategy_backtest_report_extension(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    frequency: str = "daily",
    risk_free_rate: float = 0.0,
    suppress_framework_warnings: bool = True,
) -> BacktestReportExtensionResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    rows = _returns_rows(metrics_payload)
    returns_series_path = out_dir / "strategy_backtest_report_returns.jsonl"
    _write_returns_series(
        path=returns_series_path,
        rows=rows,
        source_backtest_metrics_path=metrics_path,
        frequency=frequency,
    )
    returns = [float(row["signal_return"]) for row in rows]
    candidate = _quantstats_candidate()
    quantstats_html_path = out_dir / "strategy_backtest_quantstats_report.html"
    if not returns:
        payload = _base_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            quantstats_html_path=None,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            return_count=0,
            framework_warnings=[],
            report_status="skipped",
            reason_codes=["no_returns_series"],
            engine_run=False,
            runner_mode="not_installed_in_current_env"
            if candidate.get("status") != "installed"
            else "temporary_or_optional_import",
            dependency_source=_dependency_source(candidate),
        )
        selected_html_path = None
    elif candidate.get("status") != "installed":
        payload = _base_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            quantstats_html_path=None,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            return_count=len(returns),
            framework_warnings=[],
            report_status="skipped",
            reason_codes=["not_installed_in_current_env"],
            engine_run=False,
            runner_mode="not_installed_in_current_env",
            dependency_source=_dependency_source(candidate),
        )
        selected_html_path = None
    else:
        payload = _run_quantstats_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            quantstats_html_path=quantstats_html_path,
            rows=rows,
            returns=returns,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            suppress_framework_warnings=suppress_framework_warnings,
        )
        selected_html_path = quantstats_html_path if quantstats_html_path.exists() else None
    out_dir.mkdir(parents=True, exist_ok=True)
    report_extension_path = out_dir / "strategy_backtest_report_extension.json"
    write_json_object(report_extension_path, payload)
    report_path = _write_report(
        reports_dir / "strategy_backtest_report_extension_report.md", payload
    )
    return BacktestReportExtensionResult(
        report_extension_path=report_extension_path,
        returns_series_path=returns_series_path,
        quantstats_html_path=selected_html_path,
        report_path=report_path,
        payload=payload,
    )
