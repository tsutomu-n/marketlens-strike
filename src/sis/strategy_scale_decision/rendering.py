from __future__ import annotations

from sis.strategy_scale_decision.models import StrategyScaleDecision


def render_scale_decision_markdown(decision: StrategyScaleDecision) -> str:
    lines = [
        "# Strategy Scale Decision",
        "",
        "## Summary",
        "",
        f"- decision_id: `{decision.decision_id}`",
        f"- strategy_id: `{decision.strategy_id}`",
        f"- decision_status: `{decision.decision_status.value}`",
        f"- recommended_action: `{decision.recommended_action.value}`",
        f"- next_scale_plan_allowed: `{str(decision.next_scale_plan_allowed).lower()}`",
        f"- scale_up_execution_allowed: `{str(decision.scale_up_execution_allowed).lower()}`",
        f"- live_allowed: `{str(decision.live_allowed).lower()}`",
        "",
        "## Policy",
        "",
        f"- require_actual_fill: `{str(decision.policy.require_actual_fill).lower()}`",
        f"- require_cancel_or_close_observed: `{str(decision.policy.require_cancel_or_close_observed).lower()}`",
        f"- allow_rejection: `{str(decision.policy.allow_rejection).lower()}`",
        f"- allow_blocked_canary: `{str(decision.policy.allow_blocked_canary).lower()}`",
        f"- allow_max_loss_breach: `{str(decision.policy.allow_max_loss_breach).lower()}`",
        "",
        "## Conditions",
        "",
    ]
    for condition in [
        *decision.failed_conditions,
        *decision.warning_conditions,
        *decision.passed_conditions,
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
    for artifact in decision.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is not scale-up execution permission.",
            "- It does not permit live orders, wallet, signing, or exchange write.",
            "- A next scale plan still requires separate human approval and execution controls.",
            "",
        ]
    )
    return "\n".join(lines)
