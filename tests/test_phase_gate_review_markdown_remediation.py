from __future__ import annotations

from sis.reports.phase_gate_review_markdown_remediation import remediation_section_lines


def test_remediation_section_lines_render_populated_sections() -> None:
    lines = remediation_section_lines(
        remediation_order=[
            {
                "priority": 3,
                "reason": "execution_drift_unresolved",
                "commands": ["uv run sis phase-gate-review"],
            }
        ],
        remediation_success_criteria={
            "execution_drift_unresolved": ["execution_drift_overview_status == ok"],
        },
        remediation_preflight_commands={
            "execution_drift_unresolved": ["uv run sis monitoring-status"],
        },
        remediation_postcheck_commands={
            "execution_drift_unresolved": ["uv run sis phase-gate-review"],
        },
        remediation_preflight_expected_outputs={
            "execution_drift_unresolved": ["monitoring output shows mismatch counts"],
        },
        remediation_execute_expected_outputs={
            "execution_drift_unresolved": ["execution_drift_overview_status == ok"],
        },
        remediation_postcheck_pass_signals={
            "execution_drift_unresolved": ["phase2_entry_allowed"],
        },
        remediation_signal_snapshots_before={
            "execution_drift_unresolved": {"execution_drift_overview_status": "degraded"},
        },
        remediation_signal_snapshots_target={
            "execution_drift_unresolved": {"execution_drift_overview_status": "ok"},
        },
        remediation_signal_snapshot_diffs={
            "execution_drift_unresolved": {
                "execution_drift_overview_status": {
                    "previous": "degraded",
                    "current": "degraded",
                    "target": "ok",
                    "trend": "unchanged",
                    "target_matched": False,
                }
            },
        },
        remediation_recommendations={
            "execution_drift_unresolved": {
                "status": "retry",
                "why": "target not met",
                "commands": ["uv run sis phase-gate-review"],
            }
        },
    )

    assert lines[:8] == [
        "",
        "## Remediation Order",
        "",
        "- priority_3: execution_drift_unresolved",
        "  - `uv run sis phase-gate-review`",
        "",
        "## Remediation Success Criteria",
        "",
    ]
    assert "- execution_drift_unresolved:" in lines
    assert "  - preflight:" in lines
    assert "    - `uv run sis monitoring-status`" in lines
    assert "  - post_check:" in lines
    assert "    - phase2_entry_allowed" in lines
    assert "## Remediation Signal Diffs" in lines
    assert (
        "  - execution_drift_overview_status: previous=degraded current=degraded target=ok trend=unchanged target_matched=False"
        in lines
    )
    assert "  - status: retry" in lines
    assert "  - next: `uv run sis phase-gate-review`" in lines


def test_remediation_section_lines_render_empty_fallbacks() -> None:
    lines = remediation_section_lines(
        remediation_order=[],
        remediation_success_criteria={},
        remediation_preflight_commands={},
        remediation_postcheck_commands={},
        remediation_preflight_expected_outputs={},
        remediation_execute_expected_outputs={},
        remediation_postcheck_pass_signals={},
        remediation_signal_snapshots_before={},
        remediation_signal_snapshots_target={},
        remediation_signal_snapshot_diffs={},
        remediation_recommendations={},
    )

    assert "- remediation_order: none" in lines
    assert "- remediation_success_criteria: none" in lines
    assert "- remediation_command_flow: none" in lines
    assert "- remediation_verification_signals: none" in lines
    assert "- remediation_signal_snapshots: none" in lines
    assert "- remediation_signal_diffs: none" in lines
    assert "- remediation_recommendations: none" in lines
