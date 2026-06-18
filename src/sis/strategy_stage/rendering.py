from __future__ import annotations

from sis.strategy_stage.models import StrategyStageDecision, StrategyStagePolicyValidation


def render_stage_policy_validation_markdown(validation: StrategyStagePolicyValidation) -> str:
    lines = [
        f"# Strategy Stage Policy Validation: {validation.policy_id}",
        "",
        f"- validation_status: `{validation.validation_status.value}`",
        f"- policy_path: `{validation.policy_path}`",
        f"- policy_hash: `{validation.policy_hash}`",
        f"- stage_count: `{validation.summary.stage_count}`",
        f"- profile_count: `{validation.summary.profile_count}`",
        f"- boundary_violation_count: `{validation.summary.boundary_violation_count}`",
        "",
        "This artifact validates policy shape only. It does not permit paper or live execution.",
        "",
    ]
    return "\n".join(lines)


def render_stage_decision_markdown(decision: StrategyStageDecision) -> str:
    lines = [
        f"# Strategy Stage Decision: {decision.strategy_id}",
        "",
        f"- decision: `{decision.decision.value}`",
        f"- selected_stage: `{decision.selected_stage.value}`",
        f"- selected_profile: `{decision.selected_profile}`",
        f"- policy_id: `{decision.policy_id}`",
        f"- policy_hash: `{decision.policy_hash}`",
        f"- paper_execution_allowed: `{str(decision.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(decision.live_allowed).lower()}`",
        "",
        "## Source Artifacts",
        "",
        "| artifact | path | sha256 | schema_version |",
        "|---|---|---|---|",
    ]
    for artifact in decision.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )

    if decision.paper_evidence_summary is not None:
        summary = decision.paper_evidence_summary
        lines.extend(
            [
                "",
                "## Paper Evidence Summary",
                "",
                f"- paper_status_present: `{str(summary.paper_status_present).lower()}`",
                f"- smoke_pass_present: `{_optional_bool(summary.smoke_pass_present)}`",
                "- smoke_pass_counts_as_normal_pass: "
                f"`{_optional_bool(summary.smoke_pass_counts_as_normal_pass)}`",
                f"- normal_thresholds_met: `{_optional_bool(summary.normal_thresholds_met)}`",
                f"- latest_normal_session_id: `{summary.latest_normal_session_id or ''}`",
            ]
        )
        if summary.normal_fills is not None:
            lines.append(
                "- normal_fills: "
                f"`{summary.normal_fills.observed}/{summary.normal_fills.required}` "
                f"`remaining={summary.normal_fills.remaining}` "
                f"`met={str(summary.normal_fills.met).lower()}`"
            )
        if summary.normal_trading_days is not None:
            lines.append(
                "- normal_trading_days: "
                f"`{summary.normal_trading_days.observed}/{summary.normal_trading_days.required}` "
                f"`remaining={summary.normal_trading_days.remaining}` "
                f"`met={str(summary.normal_trading_days.met).lower()}`"
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
        *decision.passed_conditions,
        *decision.failed_conditions,
        *decision.warning_conditions,
    ]:
        lines.append(
            f"| `{condition.condition_id}` | `{str(condition.passed).lower()}` | `{condition.observed}` | `{condition.required}` | `{condition.severity}` |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is a stage planning decision only.",
            "- It does not submit orders, create paper intents, allow live execution, use wallet, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)


def _optional_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return str(value).lower()
