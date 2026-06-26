from __future__ import annotations

from typing import Any

from sis.reports import phase_gate_review_markdown_values

_as_mapping = phase_gate_review_markdown_values.as_mapping
_as_str_list = phase_gate_review_markdown_values.as_str_list


def remediation_section_lines(
    *,
    remediation_order: list[dict[str, Any]],
    remediation_success_criteria: dict[str, list[str]],
    remediation_preflight_commands: dict[str, list[str]],
    remediation_postcheck_commands: dict[str, list[str]],
    remediation_preflight_expected_outputs: dict[str, list[str]],
    remediation_execute_expected_outputs: dict[str, list[str]],
    remediation_postcheck_pass_signals: dict[str, list[str]],
    remediation_signal_snapshots_before: dict[str, object],
    remediation_signal_snapshots_target: dict[str, object],
    remediation_signal_snapshot_diffs: dict[str, object],
    remediation_recommendations: dict[str, object],
) -> list[str]:
    lines: list[str] = ["", "## Remediation Order", ""]
    if remediation_order:
        for item in remediation_order:
            lines.append(f"- priority_{item['priority']}: {item['reason']}")
            lines.extend(f"  - `{command}`" for command in _as_str_list(item.get("commands")))
    else:
        lines.append("- remediation_order: none")
    lines.extend(["", "## Remediation Success Criteria", ""])
    if remediation_success_criteria:
        for reason, criteria in remediation_success_criteria.items():
            lines.append(f"- {reason}:")
            lines.extend(f"  - {criterion}" for criterion in criteria)
    else:
        lines.append("- remediation_success_criteria: none")
    lines.extend(["", "## Remediation Command Flow", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight:")
            for command in remediation_preflight_commands.get(reason, []):
                lines.append(f"    - `{command}`")
            lines.append("  - execute:")
            for command in _as_str_list(item.get("commands")):
                lines.append(f"    - `{command}`")
            lines.append("  - post_check:")
            for command in remediation_postcheck_commands.get(reason, []):
                lines.append(f"    - `{command}`")
    else:
        lines.append("- remediation_command_flow: none")
    lines.extend(["", "## Remediation Verification Signals", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - preflight_expected_output:")
            for value in remediation_preflight_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - execute_expected_output:")
            for value in remediation_execute_expected_outputs.get(reason, []):
                lines.append(f"    - {value}")
            lines.append("  - postcheck_pass_signal:")
            for value in remediation_postcheck_pass_signals.get(reason, []):
                lines.append(f"    - {value}")
    else:
        lines.append("- remediation_verification_signals: none")
    lines.extend(["", "## Remediation Signal Snapshots", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            lines.append("  - before:")
            for key, value in _as_mapping(remediation_signal_snapshots_before.get(reason)).items():
                lines.append(f"    - {key}: {value}")
            lines.append("  - target:")
            for key, value in _as_mapping(remediation_signal_snapshots_target.get(reason)).items():
                lines.append(f"    - {key}: {value}")
    else:
        lines.append("- remediation_signal_snapshots: none")
    lines.extend(["", "## Remediation Signal Diffs", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            lines.append(f"- {reason}:")
            for key, diff in _as_mapping(remediation_signal_snapshot_diffs.get(reason)).items():
                diff_payload = _as_mapping(diff)
                lines.append(
                    "  - {key}: previous={previous} current={current} target={target} trend={trend} target_matched={target_matched}".format(
                        key=key,
                        previous=diff_payload.get("previous"),
                        current=diff_payload.get("current"),
                        target=diff_payload.get("target"),
                        trend=diff_payload.get("trend"),
                        target_matched=diff_payload.get("target_matched"),
                    )
                )
    else:
        lines.append("- remediation_signal_diffs: none")
    lines.extend(["", "## Remediation Recommendations", ""])
    if remediation_order:
        for item in remediation_order:
            reason = str(item["reason"])
            recommendation = _as_mapping(remediation_recommendations.get(reason))
            lines.append(f"- {reason}:")
            lines.append(f"  - status: {recommendation.get('status')}")
            lines.append(f"  - why: {recommendation.get('why')}")
            for command in _as_str_list(recommendation.get("commands")):
                lines.append(f"  - next: `{command}`")
    else:
        lines.append("- remediation_recommendations: none")
    return lines
