from __future__ import annotations

from sis.strategy_micro_live_plan.models import StrategyMicroLivePlan


def render_micro_live_plan_markdown(plan: StrategyMicroLivePlan) -> str:
    lines = [
        "# Strategy Micro Live Plan Gate",
        "",
        "## Summary",
        "",
        f"- plan_id: {plan.plan_id}",
        f"- strategy_id: {plan.strategy_id}",
        f"- plan_status: {plan.plan_status.value}",
        f"- human_approval_present: {plan.human_approval_present}",
        f"- micro_live_execution_allowed: {plan.micro_live_execution_allowed}",
        f"- live_allowed: {plan.live_allowed}",
        "",
        "## Risk Limits",
        "",
        f"- max_order_notional_usd: {plan.risk_limits.max_order_notional_usd}",
        f"- max_position_notional_usd: {plan.risk_limits.max_position_notional_usd}",
        f"- max_daily_loss_usd: {plan.risk_limits.max_daily_loss_usd}",
        f"- max_total_loss_usd: {plan.risk_limits.max_total_loss_usd}",
        f"- max_open_positions: {plan.risk_limits.max_open_positions}",
        f"- allowed_symbols: {', '.join(plan.risk_limits.allowed_symbols)}",
        f"- session_window: {plan.risk_limits.session_window}",
        "",
        "## Monitoring",
        "",
        f"- owner: {plan.monitoring_plan.owner}",
        f"- cadence: {plan.monitoring_plan.cadence}",
        f"- schedule_cancel_procedure: {plan.monitoring_plan.schedule_cancel_procedure}",
        f"- kill_switch_procedure: {plan.monitoring_plan.kill_switch_procedure}",
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
            f"- {state}: {condition.condition_id} "
            f"(observed={condition.observed}; required={condition.required})"
        )

    if plan.micro_live_policy_snapshot is not None:
        snapshot = plan.micro_live_policy_snapshot
        lines.extend(
            [
                "",
                "## Existing Micro Live Policy Snapshot",
                "",
                f"- policy_path: {snapshot.policy_path or ''}",
                f"- enabled: {snapshot.enabled}",
                f"- venue: {snapshot.venue}",
                f"- max_notional_usd: {snapshot.max_notional_usd}",
                f"- max_daily_loss_usd: {snapshot.max_daily_loss_usd}",
                f"- max_open_positions: {snapshot.max_open_positions}",
                f"- allowed_symbols: {', '.join(snapshot.allowed_symbols)}",
            ]
        )

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for artifact in plan.source_artifacts:
        lines.append(
            f"- {artifact.artifact_key}: {artifact.path} "
            f"({artifact.schema_version or 'unknown'}, {artifact.sha256})"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is not live execution permission.",
            "- It does not use wallet, signing, or exchange write.",
        ]
    )
    return "\n".join(lines) + "\n"
