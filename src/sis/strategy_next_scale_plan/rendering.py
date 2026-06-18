from __future__ import annotations

from sis.strategy_next_scale_plan.models import StrategyNextScalePlan


def render_next_scale_plan_markdown(plan: StrategyNextScalePlan) -> str:
    lines = [
        "# Strategy Next Scale Plan",
        "",
        "## Summary",
        "",
        f"- plan_id: `{plan.plan_id}`",
        f"- strategy_id: `{plan.strategy_id}`",
        f"- plan_status: `{plan.plan_status.value}`",
        f"- scale_decision_status: `{plan.scale_decision_status or ''}`",
        f"- scale_recommended_action: `{plan.scale_recommended_action or ''}`",
        f"- next_scale_execution_allowed: `{str(plan.next_scale_execution_allowed).lower()}`",
        f"- live_allowed: `{str(plan.live_allowed).lower()}`",
        "",
        "## Risk Limits",
        "",
        f"- next_max_order_notional_usd: `{plan.risk_limits.next_max_order_notional_usd}`",
        f"- next_max_position_notional_usd: `{plan.risk_limits.next_max_position_notional_usd}`",
        f"- next_max_daily_loss_usd: `{plan.risk_limits.next_max_daily_loss_usd}`",
        f"- next_max_total_loss_usd: `{plan.risk_limits.next_max_total_loss_usd}`",
        f"- next_max_open_positions: `{plan.risk_limits.next_max_open_positions}`",
        f"- allowed_symbols: `{', '.join(plan.risk_limits.allowed_symbols)}`",
        f"- session_window: `{plan.risk_limits.session_window}`",
        "",
        "## Monitoring",
        "",
        f"- owner: `{plan.monitoring_plan.owner}`",
        f"- cadence: `{plan.monitoring_plan.cadence}`",
        f"- schedule_cancel_procedure: `{plan.monitoring_plan.schedule_cancel_procedure}`",
        f"- kill_switch_procedure: `{plan.monitoring_plan.kill_switch_procedure}`",
        "",
        "## Guard Policy",
        "",
        f"- max_scale_multiplier: `{plan.guard_policy.max_scale_multiplier}`",
        f"- require_previous_micro_live_plan: `{str(plan.guard_policy.require_previous_micro_live_plan).lower()}`",
        f"- require_scale_decision_ready: `{str(plan.guard_policy.require_scale_decision_ready).lower()}`",
        "",
        "## Conditions",
        "",
    ]
    for condition in [
        *plan.failed_conditions,
        *plan.warning_conditions,
        *plan.passed_conditions,
    ]:
        state = "PASS" if condition.passed else condition.severity.upper()
        lines.append(
            f"- {state}: `{condition.condition_id}` "
            f"(observed=`{condition.observed}`, required=`{condition.required}`)"
        )
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "| artifact | path | sha256 | schema_version |",
            "|---|---|---|---|",
        ]
    )
    for artifact in plan.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is a planning artifact only.",
            "- It is not next-scale execution permission.",
            "- It does not permit live orders, wallet, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)
