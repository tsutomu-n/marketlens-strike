from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class BacktestExecutionSimulationResult:
    simulation_path: Path
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


def _count_rows(rows: list[Any], key: str) -> int:
    count = 0
    for row in rows:
        if isinstance(row, dict) and row.get(key) not in (None, "", False):
            count += 1
    return count


def _value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _fill_status(fill_fraction: Any) -> str:
    if not isinstance(fill_fraction, int | float):
        return "unknown"
    if fill_fraction >= 1.0:
        return "filled"
    if fill_fraction > 0:
        return "partial"
    return "unfilled"


def _event_rows(rows: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    order_intents: list[dict[str, Any]] = []
    fill_events: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        row = cast(dict[str, Any], raw)
        event_id = f"native_execution_row_{index:06d}"
        signal_id = _value(row, "signal_id")
        fill_fraction = _value(row, "fill_fraction", "effective_fill_fraction")
        order_intents.append(
            {
                "event_id": event_id,
                "signal_id": signal_id,
                "ts_signal": _value(row, "ts_signal"),
                "side": _value(row, "side"),
                "order_type": _value(row, "order_type", "entry_order_type") or "market",
                "time_in_force": _value(row, "time_in_force", "entry_time_in_force"),
                "post_only": bool(_value(row, "post_only", "entry_post_only") or False),
                "reduce_only": bool(_value(row, "reduce_only", "entry_reduce_only") or False),
                "notional_usd": _value(row, "notional_usd"),
                "paper_only": True,
            }
        )
        fill_events.append(
            {
                "event_id": event_id,
                "signal_id": signal_id,
                "ts_signal": _value(row, "ts_signal"),
                "fill_status": _fill_status(fill_fraction),
                "fill_fraction": fill_fraction,
                "slippage_bps": _value(row, "slippage_bps"),
                "cost_drag_bps": _value(row, "cost_drag_bps"),
                "signal_return": _value(row, "signal_return"),
                "exit_reason": _value(row, "exit_reason"),
                "market_impact_claimed": False,
                "paper_only": True,
            }
        )
    return order_intents, fill_events


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    summary = payload["summary"]
    lines = [
        "# Strategy Backtest Execution Simulation",
        "",
        f"- status: {payload['status']}",
        f"- execution_mode: {payload['execution_mode']}",
        f"- executed_count: {summary['executed_count']}",
        f"- blocked_count: {summary['blocked_count']}",
        f"- order_intent_count: {summary['order_intent_count']}",
        f"- fill_event_count: {summary['fill_event_count']}",
        f"- unsupported_venue_realism_count: {summary['unsupported_venue_realism_count']}",
        "- market_impact_claimed: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Feature | Count |",
        "|---|---:|",
    ]
    for key, value in payload["feature_counts"].items():
        lines.append(f"| {key} | {value} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_execution_simulation(
    *,
    metrics_path: Path,
    signals_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestExecutionSimulationResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    executed_rows = summary.get("executed_signal_results")
    rows = executed_rows if isinstance(executed_rows, list) else []
    order_intents, fill_events = _event_rows(rows)
    partial_fill_count = sum(1 for row in fill_events if row["fill_status"] == "partial")
    feature_counts = {
        "row_level_result_count": len(rows),
        "slippage_rows": _count_rows(rows, "slippage_bps"),
        "partial_fill_rows": _count_rows(rows, "fill_fraction"),
        "limit_or_order_type_rows": max(
            _count_rows(rows, "order_type"), _count_rows(rows, "entry_order_type")
        ),
        "post_only_rows": _count_rows(rows, "post_only"),
        "time_in_force_rows": _count_rows(rows, "time_in_force"),
        "latency_rows": _count_rows(rows, "latency_ms"),
        "spread_rows": _count_rows(rows, "spread_bps"),
        "depth_rows": _count_rows(rows, "depth_usd"),
        "queue_position_rows": _count_rows(rows, "queue_position"),
    }
    unsupported = [
        {
            "assumption_id": "venue_rate_limit_degrade",
            "status": "not_modeled",
            "reason": "direct venue schema and live exchange constraints are future scope",
        },
        {
            "assumption_id": "cancel_modify_race",
            "status": "not_modeled",
            "reason": "requires venue-specific event stream and order state machine",
        },
        {
            "assumption_id": "unknown_order_state",
            "status": "not_modeled",
            "reason": "requires live/order replay state reconciliation",
        },
        {
            "assumption_id": "market_impact",
            "status": "not_claimed",
            "reason": "replay-style simulation cannot prove market impact",
        },
    ]
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_execution_simulation.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "execution_mode": "native_metrics_order_fill_events_v1",
        "source_backtest_metrics_path": metrics_path.as_posix(),
        "source_backtest_metrics_hash": _sha256_file(metrics_path),
        "source_signals_path": signals_path.as_posix(),
        "source_signals_hash": _sha256_file(signals_path) if signals_path.exists() else None,
        "summary": {
            "signals_considered": summary.get("signals_considered"),
            "executed_count": summary.get("executed_count"),
            "blocked_count": summary.get("blocked_count"),
            "order_intent_count": len(order_intents),
            "fill_event_count": len(fill_events),
            "partial_fill_count": partial_fill_count,
            "unsupported_venue_realism_count": len(unsupported),
            "market_impact_claimed": False,
        },
        "feature_counts": feature_counts,
        "order_intents": order_intents,
        "fill_events": fill_events,
        "unsupported_venue_realism": unsupported,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    simulation_path = out_dir / "strategy_backtest_execution_simulation.json"
    simulation_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_execution_simulation_report.md", payload
    )
    return BacktestExecutionSimulationResult(
        simulation_path=simulation_path, report_path=report_path, payload=payload
    )
