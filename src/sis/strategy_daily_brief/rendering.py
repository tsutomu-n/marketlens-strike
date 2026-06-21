from __future__ import annotations

from sis.strategy_daily_brief.models import StrategyDailyBrief


def render_strategy_daily_brief_markdown(brief: StrategyDailyBrief) -> str:
    summary = brief.summary
    lines = [
        "# Strategy Daily Brief",
        "",
        f"- data_dir: `{brief.data_dir}`",
        f"- scanned_json_count: `{summary.scanned_json_count}`",
        f"- total_item_count: `{summary.total_item_count}`",
        f"- broken_artifact_count: `{summary.broken_artifact_count}`",
        f"- pending_human_review_count: `{summary.pending_human_review_count}`",
        f"- crypto_perp_gate_follow_up_count: `{summary.crypto_perp_gate_follow_up_count}`",
        f"- crypto_perp_truth_cycle_follow_up_count: `{summary.crypto_perp_truth_cycle_follow_up_count}`",
        f"- normal_paper_gap_count: `{summary.normal_paper_gap_count}`",
        f"- drift_review_needed_count: `{summary.drift_review_needed_count}`",
        f"- learning_request_pending_count: `{summary.learning_request_pending_count}`",
        f"- boundary_violation_count: `{summary.boundary_violation_count}`",
        f"- paper_execution_allowed: `{str(brief.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(brief.live_allowed).lower()}`",
        "",
        "## Items",
        "",
        "| category | severity | strategy_id | status | action | reason | path |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in brief.items:
        lines.append(
            f"| `{item.category.value}` | `{item.severity.value}` | `{item.strategy_id or ''}` | `{item.status or ''}` | `{item.action or ''}` | `{item.reason}` | `{item.path}` |"
        )
    if not brief.items:
        lines.append("| none | info |  |  |  | no actionable items |  |")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is a read-only daily index.",
            "- It does not run paper orders, permit live execution, use wallet, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)
