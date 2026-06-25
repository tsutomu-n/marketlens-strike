from __future__ import annotations

from pathlib import Path
from typing import Any


def write_validation_report(
    path: Path,
    *,
    payload: dict[str, Any],
    decision_path: Path,
    dag_id: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = payload.get("metrics", {})
    combined = metrics.get("combined", {}) if isinstance(metrics, dict) else {}
    path.write_text(
        "# NDX Layer 2.4 Residual Validation Report\n\n"
        f"- dag_id: {dag_id}\n"
        f"- decision: {payload['decision']}\n"
        f"- reason_codes: {', '.join(payload['reason_codes']) or 'none'}\n"
        f"- residual_row_count: {metrics.get('row_count', 'unknown') if isinstance(metrics, dict) else 'unknown'}\n"
        f"- combined_variance_retention: {combined.get('variance_retention', 'unknown')}\n"
        f"- permits_strategy_lab_research_only_export: {payload['decision'] == 'APPROVE_STRATEGY_LAB_EXPORT'}\n"
        f"- decision_artifact: {decision_path}\n"
        "- strategy_signals_written: false\n"
        "- backtest_run: false\n"
        "- paper_or_live_allowed: false\n",
        encoding="utf-8",
    )
    return path


def write_counter_dag_report(
    path: Path,
    *,
    payload: dict[str, Any],
    dag_id: str,
    counter_dag_ids: list[str],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = payload.get("counter_dags", {})
    lines = [
        "# NDX Layer 2.4 Counter-DAG Refutation Report",
        "",
        f"- dag_id: {dag_id}",
        f"- decision: {payload['decision']}",
        "",
        "| counter_dag | status | reason |",
        "| --- | --- | --- |",
    ]
    if isinstance(rows, dict) and rows:
        for key in counter_dag_ids:
            item = rows.get(key, {})
            lines.append(
                f"| {key} | {item.get('status', 'missing')} | {item.get('reason_code', 'missing')} |"
            )
    else:
        lines.append(
            "| unavailable | not_applicable | validation did not reach counter-DAG scoring |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
