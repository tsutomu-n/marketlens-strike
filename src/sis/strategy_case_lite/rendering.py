from __future__ import annotations

from sis.strategy_case_lite.models import StrategyCaseLite


def render_strategy_case_lite_markdown(case: StrategyCaseLite) -> str:
    lines = [
        f"# Strategy Case Lite: {case.strategy_id}",
        "",
        f"- case_id: `{case.case_id}`",
        f"- latest_status: `{case.summary.latest_status or 'none'}`",
        f"- artifact_count: `{case.summary.artifact_count}`",
        f"- timeline_count: `{case.summary.timeline_count}`",
        f"- paper_execution_allowed: `{str(case.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(case.live_allowed).lower()}`",
        "",
        "## Timeline",
        "",
        "| artifact_type | event_time | status | action | path |",
        "|---|---|---|---|---|",
    ]
    for entry in case.timeline:
        lines.append(
            f"| `{entry.artifact_type.value}` | `{entry.event_time or ''}` | `{entry.status or ''}` | `{entry.action or ''}` | `{entry.path}` |"
        )

    lines.extend(["", "## Open Actions", ""])
    if case.summary.open_actions:
        lines.extend(f"- {action}" for action in case.summary.open_actions)
    else:
        lines.append("- none")

    lines.extend(["", "## Blocked Reasons", ""])
    if case.summary.blocked_reasons:
        lines.extend(f"- {reason}" for reason in case.summary.blocked_reasons)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Latest Source Hashes",
            "",
            "| artifact_type | sha256 |",
            "|---|---|",
        ]
    )
    for artifact_type, sha256 in sorted(case.summary.latest_source_hashes.items()):
        lines.append(f"| `{artifact_type}` | `{sha256}` |")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is a read-only case timeline.",
            "- It does not run paper orders, permit live execution, use wallet, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)
