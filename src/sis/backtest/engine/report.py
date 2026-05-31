from __future__ import annotations

from html import escape
from typing import Any


REQUIRED_REPORT_SECTIONS = [
    "Run Summary",
    "Scope and Non-Scope",
    "Config Summary",
    "Data Manifest",
    "Data Quality",
    "Strategy Summary",
    "Performance Summary",
    "Benchmark Comparison",
    "Scenario Sensitivity",
    "Split Validation",
    "Parameter Sweep",
    "Trade List Summary",
    "Blocked Events",
    "Session / Market Status Breakdown",
    "Cost Breakdown",
    "Open Position at End",
    "Warnings / Known Limitations",
    "Artifact Paths",
]


def render_backtest_markdown(
    *,
    metrics: dict[str, Any],
    artifacts: dict[str, str],
    data_quality: dict[str, Any] | None = None,
    benchmark_results: dict[str, Any] | None = None,
    scenario_summary: dict[str, Any] | None = None,
    split_summary: dict[str, Any] | None = None,
    parameter_summary: dict[str, Any] | None = None,
    run_meta: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> str:
    lines = ["# Trade[XYZ] Backtest Report", ""]
    data_quality = data_quality or {}
    benchmark_results = benchmark_results or {}
    scenario_summary = scenario_summary or {}
    split_summary = split_summary or {}
    parameter_summary = parameter_summary or {}
    run_meta = run_meta or {}
    for section in REQUIRED_REPORT_SECTIONS:
        lines.extend([f"## {section}", ""])
        if section == "Run Summary":
            for key in (
                "run_id",
                "strategy_id",
                "symbol",
                "timeframe",
                "close_source",
                "event_time_source",
                "input_data_ref",
            ):
                if key in run_meta:
                    lines.append(f"- `{key}`: {run_meta[key]}")
        elif section == "Scope and Non-Scope":
            lines.extend(
                [
                    "- Trade[XYZ] pure backtest v0.1",
                    "- no live order, wallet, signing, or exchange write",
                    "- long-only single-symbol market-like taker fill",
                ]
            )
        elif section == "Config Summary":
            for key in (
                "fee_model_ref",
                "funding_policy",
                "fill_model",
                "end_position_policy",
                "leverage_mode",
            ):
                if key in run_meta:
                    lines.append(f"- `{key}`: {run_meta[key]}")
        elif section == "Data Manifest":
            if "data_manifest" in artifacts:
                lines.append(f"- `data_manifest`: `{artifacts['data_manifest']}`")
        elif section == "Data Quality":
            for key, value in sorted(data_quality.items()):
                if key in {
                    "status",
                    "input_row_count",
                    "filtered_row_count",
                    "bar_count",
                    "evaluation_bar_count",
                    "coverage_seconds",
                    "median_event_gap_seconds",
                    "max_event_gap_seconds",
                    "insufficient_coverage_for_strategy",
                    "required_min_rows",
                    "required_min_bars",
                    "cadence_gap_count",
                    "unknown_fee_mode_count",
                    "null_taker_fee_count",
                    "null_maker_fee_count",
                    "funding_rate_without_interval_count",
                    "warnings",
                    "errors",
                }:
                    lines.append(f"- `{key}`: {value}")
        elif section == "Strategy Summary":
            lines.append(f"- `strategy_id`: {run_meta.get('strategy_id', 'unknown')}")
        elif section == "Performance Summary":
            for key, value in sorted(metrics.items()):
                lines.append(f"- `{key}`: {value}")
        elif section == "Benchmark Comparison":
            for key, value in sorted(benchmark_results.items()):
                lines.append(f"- `{key}`: {value}")
        elif section == "Scenario Sensitivity":
            for key, value in sorted(scenario_summary.items()):
                lines.append(f"- `{key}`: {value}")
        elif section == "Split Validation":
            for key, value in sorted(split_summary.items()):
                lines.append(f"- `{key}`: {value}")
        elif section == "Parameter Sweep":
            for key, value in sorted(parameter_summary.items()):
                lines.append(f"- `{key}`: {value}")
        elif section == "Trade List Summary":
            lines.append(f"- `trade_count`: {metrics.get('trade_count')}")
        elif section == "Blocked Events":
            lines.append(f"- `blocked_reason_counts`: {metrics.get('blocked_reason_counts')}")
        elif section == "Session / Market Status Breakdown":
            lines.append(f"- `session_breakdown`: {metrics.get('session_breakdown')}")
            lines.append(f"- `market_status_breakdown`: {metrics.get('market_status_breakdown')}")
        elif section == "Cost Breakdown":
            for key in (
                "fee_impact",
                "fee_source_counts",
                "fee_row_resolved_rate",
                "fee_config_fallback_rate",
                "fee_unresolved_rate_runtime",
                "funding_impact",
                "slippage_impact",
                "cost_drag_bps",
            ):
                lines.append(f"- `{key}`: {metrics.get(key)}")
        elif section == "Open Position at End":
            lines.append(f"- `open_position_at_end`: {metrics.get('open_position_at_end')}")
            lines.append(f"- `end_position_policy`: {metrics.get('end_position_policy')}")
            lines.append(f"- `end_open_position_count`: {metrics.get('end_open_position_count')}")
            lines.append(f"- `end_unrealized_pnl`: {metrics.get('end_unrealized_pnl')}")
        elif section == "Warnings / Known Limitations":
            for warning in warnings or []:
                lines.append(f"- {warning}")
        elif section == "Artifact Paths":
            for key, value in sorted(artifacts.items()):
                lines.append(f"- `{key}`: `{value}`")
        if lines[-1] == "":
            lines.append("- None")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_backtest_html(markdown: str) -> str:
    body_lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            body_lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body_lines.append(f"<p>{escape(line)}</p>")
        elif line:
            body_lines.append(f"<p>{escape(line)}</p>")
    return "<!doctype html>\n<html><body>\n" + "\n".join(body_lines) + "\n</body></html>\n"
