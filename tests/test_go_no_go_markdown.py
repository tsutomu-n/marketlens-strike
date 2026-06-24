from pathlib import Path

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport, VenueDecision
from sis.reports.go_no_go_markdown import (
    _quick_navigation,
    _related_reports,
    write_go_no_go_markdown,
)


def test_quick_navigation_uses_research_sibling_reports_and_summary_paths(tmp_path: Path) -> None:
    out_path = tmp_path / "data/research/go_no_go_report.md"

    navigation = _quick_navigation(
        out_path,
        phase_gate_summary={"phase_gate_review_report_path": "data/reports/phase_gate_review.md"},
        readiness_summary={"readiness_next_phase_candidate": "Stay Phase 1"},
    )

    assert navigation == {
        "go_no_go_report": str(out_path),
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "current_state_index_report": str(tmp_path / "data/reports/current_state_index.md"),
        "readiness_snapshot_report": str(tmp_path / "data/reports/readiness_snapshot.md"),
        "paper_operations_runbook_report": str(
            tmp_path / "data/reports/paper_operations_runbook.md"
        ),
    }


def test_related_reports_include_execution_report_paths(tmp_path: Path) -> None:
    out_path = tmp_path / "data/research/go_no_go_report.md"

    related_reports = _related_reports(
        out_path,
        phase_gate_summary={"phase_gate_review_report_path": "data/reports/phase_gate_review.md"},
        readiness_summary={"readiness_next_phase_candidate": "Stay Phase 1"},
        execution_summary={"report_path": "data/reports/execution_snapshot.md"},
        execution_comparison_summary={"report_path": "data/reports/execution_venue_comparison.md"},
        execution_diagnostics_summary={
            "report_path": "data/reports/execution_venue_diagnostics.md"
        },
        execution_gap_history_summary={"report_path": "data/reports/execution_gap_history.md"},
        execution_state_comparison_summary={
            "report_path": "data/reports/execution_state_comparison_history.md"
        },
        execution_snapshot_drift_summary={
            "report_path": "data/reports/execution_snapshot_drift_history.md"
        },
        execution_drift_overview_summary={
            "report_path": "data/reports/execution_drift_overview.md"
        },
    )

    assert related_reports["go_no_go_report"] == str(out_path)
    assert related_reports["phase_gate_review_report"] == "data/reports/phase_gate_review.md"
    assert related_reports["execution_snapshot_report"] == "data/reports/execution_snapshot.md"
    assert (
        related_reports["execution_venue_comparison_report"]
        == "data/reports/execution_venue_comparison.md"
    )
    assert (
        related_reports["execution_drift_overview_report"]
        == "data/reports/execution_drift_overview.md"
    )


def test_write_go_no_go_markdown_renders_navigation_summaries_and_decisions(
    tmp_path: Path,
) -> None:
    report = GoNoGoReport(
        decision=Decision.CONDITIONAL_GO_DATA_READY,
        summary="Local evidence only.",
        criteria=[
            GoNoGoCriterion(
                criterion="Normalized quote data",
                result="PASS",
                evidence="data/normalized/quotes.parquet",
            )
        ],
        venue_decisions=[
            VenueDecision(
                venue="ostium",
                decision=Decision.CONDITIONAL_GO_DATA_READY,
                main_blocker="Liquidation reference complete",
            )
        ],
        blockers=["Liquidation reference complete"],
        next_actions=["Run `uv run sis phase-gate-review`."],
    )
    out_path = tmp_path / "data/research/go_no_go_report.md"

    write_go_no_go_markdown(
        report,
        out_path,
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        },
        readiness_summary={
            "next_phase_candidate": "Stay Phase 1",
            "execution_ready": False,
            "readiness_next_phase_candidate": "Stay Phase 1",
        },
        execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
            "report_path": "data/reports/execution_snapshot.md",
        },
    )

    text = out_path.read_text(encoding="utf-8")
    assert "## Quick Navigation" in text
    assert f"- go_no_go_report: {out_path}" in text
    assert "## Related Reports" in text
    assert "- execution_snapshot_report: data/reports/execution_snapshot.md" in text
    assert "## Phase Gate Summary" in text
    assert "- decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "## Readiness Summary" in text
    assert "- next_phase_candidate: Stay Phase 1" in text
    assert "## Execution Snapshot" in text
    assert "| Normalized quote data | PASS | data/normalized/quotes.parquet |" in text
    assert "| ostium | CONDITIONAL_GO_DATA_READY | Liquidation reference complete |" in text
    assert "- Run `uv run sis phase-gate-review`." in text
