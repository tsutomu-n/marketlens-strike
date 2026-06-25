from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_authoring_bundle_outputs(payload: dict[str, Any], *, data_dir: Path) -> dict[str, Path]:
    result_path = data_dir / "research/strategy_authoring_bundle_result.json"
    report_path = data_dir / "reports/strategy_authoring_bundle_report.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    rows = "\n".join(
        "| {strategy_id} | {weight:.4f} | {trades} | {total_return:.6f} | {passed} |".format(
            strategy_id=member["strategy_id"],
            weight=float(member["effective_allocation_weight"]),
            trades=member["summary"]["aggregate_metrics"].get("trade_count") or 0,
            total_return=float(member["summary"]["aggregate_metrics"].get("total_return") or 0.0),
            passed=member["summary"].get("backtest_passed"),
        )
        for member in payload["members"]
    )
    group_metrics = (payload.get("aggregate_metrics") or {}).get("multi_leg_group_metrics") or {}
    group_section = ""
    if int(group_metrics.get("group_count") or 0) > 0:
        group_count = int(group_metrics.get("group_count") or 0)
        complete_group_count = int(group_metrics.get("complete_group_count") or 0)
        group_completion_rate = complete_group_count / group_count if group_count else 0.0

        def _format_optional_float(value: Any) -> str:
            if value is None:
                return "null"
            return f"{float(value):.6f}"

        group_rows = "\n".join(
            (
                "| {strategy_id} | {groups} | {complete} | {completion_rate:.6f} | "
                "{weighted_return:.6f} | {weighted_notional_return} | {total_notional_usd} | "
                "{weighted_win_rate} | {weighted_max_drawdown} | "
                "{weighted_profit_factor} | "
                "{weighted_leg_imbalance} |"
            ).format(
                strategy_id=member["strategy_id"],
                groups=int(member["summary"]["multi_leg_group_metrics"].get("group_count") or 0),
                complete=int(
                    member["summary"]["multi_leg_group_metrics"].get("complete_group_count") or 0
                ),
                completion_rate=(
                    int(
                        member["summary"]["multi_leg_group_metrics"].get("complete_group_count")
                        or 0
                    )
                    / int(member["summary"]["multi_leg_group_metrics"].get("group_count") or 1)
                ),
                weighted_return=float(
                    member["summary"]["multi_leg_group_metrics"].get("total_return") or 0.0
                )
                * float(member["effective_allocation_weight"]),
                weighted_notional_return=_format_optional_float(
                    float(
                        member["summary"]["multi_leg_group_metrics"][
                            "notional_weighted_total_return"
                        ]
                    )
                    * float(member["effective_allocation_weight"])
                    if member["summary"]["multi_leg_group_metrics"].get(
                        "notional_weighted_total_return"
                    )
                    is not None
                    else None
                ),
                total_notional_usd=_format_optional_float(
                    member["summary"]["multi_leg_group_metrics"].get("total_notional_usd")
                ),
                weighted_win_rate=_format_optional_float(
                    float(member["summary"]["multi_leg_group_metrics"]["win_rate"])
                    * float(member["effective_allocation_weight"])
                    if member["summary"]["multi_leg_group_metrics"].get("win_rate") is not None
                    else None
                ),
                weighted_max_drawdown=_format_optional_float(
                    float(member["summary"]["multi_leg_group_metrics"]["max_drawdown"])
                    * float(member["effective_allocation_weight"])
                    if member["summary"]["multi_leg_group_metrics"].get("max_drawdown") is not None
                    else None
                ),
                weighted_profit_factor=_format_optional_float(
                    float(member["summary"]["multi_leg_group_metrics"]["profit_factor"])
                    * float(member["effective_allocation_weight"])
                    if member["summary"]["multi_leg_group_metrics"].get("profit_factor") is not None
                    else None
                ),
                weighted_leg_imbalance=_format_optional_float(
                    float(member["summary"]["multi_leg_group_metrics"]["avg_leg_return_imbalance"])
                    * float(member["effective_allocation_weight"])
                    if member["summary"]["multi_leg_group_metrics"].get("avg_leg_return_imbalance")
                    is not None
                    else None
                ),
            )
            for member in payload["members"]
            if int(member["summary"].get("multi_leg_group_metrics", {}).get("group_count") or 0) > 0
        )
        group_section = (
            "\n## Multi-Leg Group Metrics\n\n"
            f"- group_count: {group_metrics.get('group_count', 0)}\n"
            f"- complete_group_count: {group_metrics.get('complete_group_count', 0)}\n"
            f"- incomplete_group_count: {group_metrics.get('incomplete_group_count', 0)}\n"
            f"- expected_leg_count: {group_metrics.get('expected_leg_count', 0)}\n"
            f"- executed_leg_count: {group_metrics.get('executed_leg_count', 0)}\n"
            f"- weighted_total_return: {float(group_metrics.get('weighted_total_return') or 0.0):.6f}\n"
            f"- total_notional_usd: {_format_optional_float(group_metrics.get('total_notional_usd'))}\n"
            f"- weighted_notional_return: {_format_optional_float(group_metrics.get('weighted_notional_return'))}\n"
            f"- weighted_cost_drag_bps: {float(group_metrics.get('weighted_cost_drag_bps') or 0.0):.6f}\n\n"
            f"- group_completion_rate: {group_completion_rate:.6f}\n"
            f"- weighted_win_rate: {_format_optional_float(group_metrics.get('weighted_win_rate'))}\n"
            f"- worst_group_return: {_format_optional_float(group_metrics.get('worst_group_return'))}\n"
            f"- weighted_max_drawdown: {_format_optional_float(group_metrics.get('weighted_max_drawdown'))}\n"
            f"- weighted_profit_factor: {_format_optional_float(group_metrics.get('weighted_profit_factor'))}\n"
            f"- weighted_avg_leg_return_imbalance: {_format_optional_float(group_metrics.get('weighted_avg_leg_return_imbalance'))}\n\n"
            "| Strategy | Groups | Complete | Completion Rate | Weighted Group Return | "
            "Weighted Notional Return | Total Notional USD | Weighted Win Rate | "
            "Weighted Max Drawdown | Weighted Profit Factor | "
            "Weighted Leg Imbalance |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
            f"{group_rows}\n"
        )
    report_path.write_text(
        "# Strategy Authoring Bundle Report\n\n"
        "paper_only: true\n\n"
        f"- bundle_id: {payload['bundle_id']}\n"
        f"- member_count: {payload['aggregate_metrics']['member_count']}\n"
        f"- weighted_total_return: {payload['aggregate_metrics']['weighted_total_return']:.6f}\n"
        f"- best_member: {(payload.get('best_member') or {}).get('strategy_id')}\n\n"
        "| Strategy | Effective Weight | Trades | Total Return | Backtest Passed |\n"
        "|---|---:|---:|---:|---:|\n"
        f"{rows}\n"
        f"{group_section}",
        encoding="utf-8",
    )
    return {"bundle_result": result_path, "bundle_report": report_path}
