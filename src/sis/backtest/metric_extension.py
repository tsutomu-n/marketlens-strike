from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
from typing import Any

from sis.backtest.frameworks import framework_adapter_status


@dataclass(frozen=True)
class BacktestMetricExtensionResult:
    metric_extension_path: Path
    returns_series_path: Path
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


def _empyrical_candidate() -> dict[str, Any]:
    for candidate in framework_adapter_status():
        if candidate.get("framework_id") == "empyrical_reloaded":
            return candidate
    return {
        "framework_id": "empyrical_reloaded",
        "adapter_role": "metrics_only_candidate",
        "status": "not_installed",
        "version": None,
    }


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def _scalar(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return _numeric(value)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _scalar(item())
        except Exception:
            return None
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


def _period(frequency: str) -> str:
    return frequency if frequency in {"daily", "weekly", "monthly"} else "daily"


def _metric_value(func: Any, returns: Any, **kwargs: Any) -> float | None:
    if not callable(func):
        return None
    try:
        return _scalar(func(returns, **kwargs))
    except Exception:
        return None


def _base_payload(
    *,
    candidate: dict[str, Any],
    metrics_path: Path,
    returns_series_path: Path,
    frequency: str,
    risk_free_rate: float,
    return_count: int,
    metric_status: str,
    reason_codes: list[str],
    engine_run: bool,
    runner_mode: str,
    sharpe_ratio: float | None = None,
    sortino_ratio: float | None = None,
    max_drawdown: float | None = None,
    annual_return: float | None = None,
    annual_volatility: float | None = None,
    calmar_ratio: float | None = None,
    omega_ratio: float | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_backtest_metric_extension.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "framework_id": "empyrical_reloaded",
        "adapter_role": str(candidate.get("adapter_role") or "metrics_only_candidate"),
        "framework_version": candidate.get("version"),
        "runner_mode": runner_mode,
        "metric_status": metric_status,
        "reason_codes": reason_codes,
        "dependency_added": False,
        "engine_run": engine_run,
        "source_backtest_metrics_path": metrics_path.as_posix(),
        "source_backtest_metrics_hash": _sha256_file(metrics_path),
        "returns_series_path": returns_series_path.as_posix(),
        "returns_series_hash": _sha256_file(returns_series_path),
        "frequency": frequency,
        "risk_free_rate": risk_free_rate,
        "return_count": return_count,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "alpha": None,
        "beta": None,
        "calmar_ratio": calmar_ratio,
        "omega_ratio": omega_ratio,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def _run_empyrical_payload(
    *,
    candidate: dict[str, Any],
    metrics_path: Path,
    returns_series_path: Path,
    returns: list[float],
    frequency: str,
    risk_free_rate: float,
) -> dict[str, Any]:
    try:
        empyrical = importlib.import_module("empyrical")
        pandas = importlib.import_module("pandas")
        returns_series = pandas.Series(returns, dtype="float64")
        period = _period(frequency)
        sharpe_ratio = _metric_value(
            getattr(empyrical, "sharpe_ratio", None),
            returns_series,
            risk_free=risk_free_rate,
            period=period,
        )
        sortino_ratio = _metric_value(
            getattr(empyrical, "sortino_ratio", None),
            returns_series,
            required_return=risk_free_rate,
            period=period,
        )
        max_drawdown = _metric_value(getattr(empyrical, "max_drawdown", None), returns_series)
        annual_return = _metric_value(
            getattr(empyrical, "annual_return", None), returns_series, period=period
        )
        annual_volatility = _metric_value(
            getattr(empyrical, "annual_volatility", None), returns_series, period=period
        )
        calmar_ratio = _metric_value(
            getattr(empyrical, "calmar_ratio", None), returns_series, period=period
        )
        omega_ratio = _metric_value(
            getattr(empyrical, "omega_ratio", None), returns_series, risk_free=risk_free_rate
        )
    except Exception:
        return _base_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            return_count=len(returns),
            metric_status="failed",
            reason_codes=["framework_metric_run_failed"],
            engine_run=False,
            runner_mode="temporary_or_optional_import",
        )
    return _base_payload(
        candidate=candidate,
        metrics_path=metrics_path,
        returns_series_path=returns_series_path,
        frequency=frequency,
        risk_free_rate=risk_free_rate,
        return_count=len(returns),
        metric_status="completed",
        reason_codes=[],
        engine_run=True,
        runner_mode="temporary_or_optional_import",
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        annual_return=annual_return,
        annual_volatility=annual_volatility,
        calmar_ratio=calmar_ratio,
        omega_ratio=omega_ratio,
    )


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Metric Extension",
        "",
        f"- framework_id: {payload['framework_id']}",
        f"- framework_version: {payload['framework_version']}",
        f"- runner_mode: {payload['runner_mode']}",
        f"- metric_status: {payload['metric_status']}",
        f"- engine_run: {payload['engine_run']}",
        f"- source_backtest_metrics_path: `{payload['source_backtest_metrics_path']}`",
        f"- returns_series_path: `{payload['returns_series_path']}`",
        f"- frequency: {payload['frequency']}",
        f"- return_count: {payload['return_count']}",
        f"- sharpe_ratio: {payload['sharpe_ratio']}",
        f"- sortino_ratio: {payload['sortino_ratio']}",
        f"- max_drawdown: {payload['max_drawdown']}",
        f"- annual_return: {payload['annual_return']}",
        f"- annual_volatility: {payload['annual_volatility']}",
        f"- calmar_ratio: {payload['calmar_ratio']}",
        f"- omega_ratio: {payload['omega_ratio']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_metric_extension(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    frequency: str = "daily",
    risk_free_rate: float = 0.0,
) -> BacktestMetricExtensionResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    rows = _returns_rows(metrics_payload)
    returns_series_path = out_dir / "strategy_backtest_returns.jsonl"
    _write_returns_series(
        path=returns_series_path,
        rows=rows,
        source_backtest_metrics_path=metrics_path,
        frequency=frequency,
    )
    returns = [float(row["signal_return"]) for row in rows]
    candidate = _empyrical_candidate()
    if not returns:
        payload = _base_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            return_count=0,
            metric_status="skipped",
            reason_codes=["no_returns_series"],
            engine_run=False,
            runner_mode="not_installed_in_current_env"
            if candidate.get("status") != "installed"
            else "temporary_or_optional_import",
        )
    elif candidate.get("status") != "installed":
        payload = _base_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            return_count=len(returns),
            metric_status="skipped",
            reason_codes=["not_installed_in_current_env"],
            engine_run=False,
            runner_mode="not_installed_in_current_env",
        )
    else:
        payload = _run_empyrical_payload(
            candidate=candidate,
            metrics_path=metrics_path,
            returns_series_path=returns_series_path,
            returns=returns,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    metric_extension_path = out_dir / "strategy_backtest_metric_extension.json"
    metric_extension_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_metric_extension_report.md", payload
    )
    return BacktestMetricExtensionResult(
        metric_extension_path=metric_extension_path,
        returns_series_path=returns_series_path,
        report_path=report_path,
        payload=payload,
    )
