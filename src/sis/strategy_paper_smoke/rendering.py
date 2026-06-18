from __future__ import annotations

from sis.strategy_paper_smoke.models import StrategyPaperSmokePlan


def render_paper_smoke_plan_markdown(plan: StrategyPaperSmokePlan) -> str:
    lines = [
        f"# Strategy Paper Smoke Plan: {plan.strategy_id}",
        "",
        f"- plan_status: `{plan.plan_status.value}`",
        f"- paper_execution_allowed: `{str(plan.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(plan.live_allowed).lower()}`",
        "",
        "## Thresholds",
        "",
        f"- min_fills_for_pass: `{plan.thresholds.min_fills_for_pass}`",
        f"- min_trading_days_for_pass: `{plan.thresholds.min_trading_days_for_pass}`",
        f"- max_blocked_rate: `{plan.thresholds.max_blocked_rate}`",
        f"- max_consecutive_blocked: `{plan.thresholds.max_consecutive_blocked}`",
        f"- max_open_position_age_hours: `{plan.thresholds.max_open_position_age_hours}`",
        f"- max_order_notional_usd: `{plan.thresholds.max_order_notional_usd or 'not_set'}`",
        f"- max_position_notional_usd: `{plan.thresholds.max_position_notional_usd or 'not_set'}`",
        f"- max_orders_per_day: `{plan.thresholds.max_orders_per_day if plan.thresholds.max_orders_per_day is not None else 'not_set'}`",
        "",
        "## Source Artifacts",
        "",
        "| artifact | required | exists | path | sha256 | schema_version |",
        "|---|---:|---:|---|---|---|",
    ]
    for artifact in plan.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{str(artifact.required).lower()}` | `{str(artifact.exists).lower()}` | `{artifact.path}` | `{artifact.sha256 or ''}` | `{artifact.schema_version or ''}` |"
        )

    lines.extend(
        [
            "",
            "## Conditions",
            "",
            "| condition | passed | observed | required | severity |",
            "|---|---:|---|---|---|",
        ]
    )
    for condition in [
        *plan.passed_conditions,
        *plan.failed_conditions,
        *plan.warning_conditions,
    ]:
        lines.append(
            f"| `{condition.condition_id}` | `{str(condition.passed).lower()}` | `{condition.observed}` | `{condition.required}` | `{condition.severity}` |"
        )

    lines.extend(
        [
            "",
            "## Execution Preview",
            "",
            "```bash",
            plan.execution_preview.command,
            "```",
            "",
            "## Boundary",
            "",
            "- This artifact is a paper smoke plan only.",
            "- It does not run paper orders by itself.",
            "- It does not permit live execution, wallet use, signing, or exchange write.",
            "- A smoke pass is not a normal paper observation pass.",
            "",
        ]
    )
    return "\n".join(lines)
