from __future__ import annotations

from sis.strategy_case_index.models import StrategyCaseIndex


def render_strategy_case_index_markdown(index: StrategyCaseIndex) -> str:
    lines = [
        f"# Strategy Case Index: {index.index_id}",
        "",
        f"- case_count: `{index.case_count}`",
        f"- strategy_count: `{index.strategy_count}`",
        f"- paper_execution_allowed: `{str(index.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(index.live_allowed).lower()}`",
        f"- db_persistence_allowed: `{str(index.index_boundary.db_persistence_allowed).lower()}`",
        "",
        "## Strategies",
        "",
        "| strategy_id | case_count | latest_case_id | latest_status | open_actions |",
        "|---|---:|---|---|---|",
    ]
    for strategy in index.strategies:
        actions = ", ".join(strategy.open_actions)
        lines.append(
            f"| `{strategy.strategy_id}` | {strategy.case_count} | "
            f"`{strategy.latest_case_id}` | `{strategy.latest_status or ''}` | {actions} |"
        )

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| case_id | strategy_id | updated_at | latest_status | path | sha256 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for case in index.cases:
        lines.append(
            f"| `{case.case_id}` | `{case.strategy_id}` | "
            f"`{case.updated_at.isoformat()}` | `{case.latest_status or ''}` | "
            f"`{case.case_path}` | `{case.case_sha256}` |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact is a read-only index over Strategy Case Lite artifacts.",
            "- It is not a DB registry, merge policy, paper permission, or live permission.",
            "",
        ]
    )
    return "\n".join(lines)
