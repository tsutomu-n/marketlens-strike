from __future__ import annotations

from sis.reports.remediation_planner_markdown import render_remediation_planner_markdown


def _summary() -> dict[str, object]:
    return {
        "planner_status": "stalled",
        "planned_step_count": 2,
        "next_best_command": "uv run sis validate-artifacts --strict",
        "phase_gate_summary_path": "data/ops/phase_gate_review_summary.json",
        "runbook_summary_path": "data/ops/paper_operations_runbook_summary.json",
        "remediation_evaluator_summary_path": "data/ops/remediation_evaluator_summary.json",
        "remediation_command_results_summary_path": (
            "data/ops/remediation_command_results_summary.json"
        ),
        "operation_chain_path": "data/ops/operation_manifests.jsonl",
        "recommended_command_chain": [
            "uv run sis validate-artifacts --strict",
            "uv run sis refresh-operations-artifacts",
        ],
        "planner_rerun_diff": {
            "trend": "improved",
            "previous_summary_status": "regressed",
            "previous_manifest_status": "regressed",
            "current_status": "stalled",
            "previous_next_best_command": "uv run sis refresh-operations-artifacts",
            "current_next_best_command": "uv run sis validate-artifacts --strict",
            "previous_planned_step_count": 3,
            "current_planned_step_count": 2,
            "previous_manifest_run_id": "20260524_010203",
            "command_chain_diff": {
                "trend": "changed",
                "added": ["uv run sis validate-artifacts --strict"],
                "removed": [],
                "unchanged": ["uv run sis refresh-operations-artifacts"],
            },
        },
        "planner_entry_diffs": {
            "paper_operations_runbook:strict_validation_failed": {
                "trend": "improved",
                "previous_status": "regressed",
                "current_status": "stalled",
                "previous_commands": ["uv run sis validate-artifacts --strict"],
                "current_commands": ["uv run sis validate-artifacts --strict"],
                "active": True,
            }
        },
        "entries": [
            {
                "source": "paper_operations_runbook",
                "priority": 2,
                "effective_priority": 0,
                "reason": "strict_validation_failed",
                "status": "stalled",
                "why": "signals did not move toward target",
                "commands": ["uv run sis validate-artifacts --strict"],
                "observed_sources": ["stdout_stderr"],
                "source_confidence": "high",
                "source_policy": "direct_observation_priority",
                "feedback_priority_reason": "evaluation_failed",
                "supporting_action_keys": [
                    "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1"
                ],
            }
        ],
        "quick_navigation": {
            "remediation_planner_report": "data/reports/remediation_planner.md",
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
        },
        "related_reports": {
            "remediation_execution_plan_report": ("data/reports/remediation_execution_plan.md"),
            "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        },
    }


def test_render_remediation_planner_markdown_includes_core_sections() -> None:
    text = render_remediation_planner_markdown(_summary())

    assert text.startswith("# Remediation Planner Dry Run\n")
    assert "## Quick Navigation" in text
    assert "- remediation_planner_report: data/reports/remediation_planner.md" in text
    assert "## Related Reports" in text
    assert "- remediation_execution_plan_report: data/reports/remediation_execution_plan.md" in text
    assert "## Planner Summary" in text
    assert "- planner_status: stalled" in text
    assert "- next_best_command: uv run sis validate-artifacts --strict" in text
    assert "## Recommended Command Chain" in text
    assert "- `uv run sis validate-artifacts --strict`" in text
    assert "## Planner Rerun Diff" in text
    assert "- trend: improved" in text
    assert "## Recommended Command Chain Diff" in text
    assert "- added: ['uv run sis validate-artifacts --strict']" in text
    assert "## Planner Entry Diffs" in text
    assert "- paper_operations_runbook:strict_validation_failed: improved" in text
    assert "  - previous_status: regressed" in text
    assert "  - current_status: stalled" in text
    assert "## Planned Steps" in text
    assert "- priority_2_paper_operations_runbook: strict_validation_failed" in text
    assert "  - observed_sources: ['stdout_stderr']" in text
    assert "  - source_confidence: high" in text
    assert "  - feedback_priority_reason: evaluation_failed" in text
    assert "  - next: `uv run sis validate-artifacts --strict`" in text


def test_render_remediation_planner_markdown_handles_empty_states() -> None:
    summary = _summary()
    summary["recommended_command_chain"] = []
    summary["planner_entry_diffs"] = {}
    summary["entries"] = []
    summary["quick_navigation"] = {}
    summary["related_reports"] = {}

    text = render_remediation_planner_markdown(summary)

    assert "## Quick Navigation" not in text
    assert "## Related Reports" not in text
    assert "- recommended_command_chain: none" in text
    assert "- planner_entry_diffs: none" in text
    assert "- planned_steps: none" in text
