from __future__ import annotations

from sis.paper.operation_summaries import read_audit_dashboard_summary
from sis.paper.operation_summaries import read_audit_summary
from sis.paper.operation_summaries import read_execution_comparison_summary
from sis.paper.operation_summaries import read_execution_summary
from sis.paper.operation_summaries import read_phase_gate_summary
from sis.paper.operation_summaries import read_readiness_summary


def test_paper_operation_summaries_return_empty_defaults_for_missing_files(tmp_path) -> None:
    data_dir = tmp_path / "data"

    assert read_audit_dashboard_summary(data_dir) == {}
    assert read_audit_summary(data_dir) == {
        "overall_status": None,
        "latest_operation": None,
        "bundle_history_snapshot_count": None,
        "audit_overall_status": None,
        "audit_latest_operation": None,
        "audit_bundle_history_snapshot_count": None,
    }
    assert read_execution_summary(data_dir)["execution_overall_status"] is None
    assert read_readiness_summary(data_dir) == {}
    assert read_phase_gate_summary(data_dir) == {}


def test_read_audit_summary_merges_dashboard_and_bundle_latest_execution(tmp_path) -> None:
    data_dir = tmp_path / "data"
    ops_dir = data_dir / "ops"
    ops_dir.mkdir(parents=True)
    (ops_dir / "audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot",'
        '"timeline_latest_execution_summary":{"execution_overall_status":"ok",'
        '"execution_venue_count":2},'
        '"timeline_latest_execution_comparison_summary":{'
        '"execution_comparison_all_registries_present":"True"}}',
        encoding="utf-8",
    )
    (ops_dir / "audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3,'
        '"bundle_history_latest_execution_summary":{"execution_overall_status":"degraded",'
        '"execution_venue_count":1}}',
        encoding="utf-8",
    )

    summary = read_audit_summary(data_dir)

    assert summary["overall_status"] == "ok"
    assert summary["bundle_history_snapshot_count"] == 3
    assert summary["audit_overall_status"] == "ok"
    assert summary["audit_latest_operation"] == "audit_bundle_snapshot"
    assert summary["audit_bundle_history_snapshot_count"] == 3


def test_read_execution_summary_normalizes_report_path(tmp_path) -> None:
    data_dir = tmp_path / "data"
    ops_dir = data_dir / "ops"
    ops_dir.mkdir(parents=True)
    (ops_dir / "execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )

    summary = read_execution_summary(data_dir)

    assert summary["execution_overall_status"] == "ok"
    assert summary["execution_venue_count"] == 2
    assert summary["report_path"] == str(data_dir / "reports/execution_snapshot.md")
    assert summary["execution_report_path"] == str(data_dir / "reports/execution_snapshot.md")


def test_read_execution_comparison_summary_normalizes_boolean_and_report_path(tmp_path) -> None:
    data_dir = tmp_path / "data"
    ops_dir = data_dir / "ops"
    ops_dir.mkdir(parents=True)
    (ops_dir / "execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":"True"}',
        encoding="utf-8",
    )

    summary = read_execution_comparison_summary(data_dir)

    assert summary["execution_comparison_all_registries_present"] is True
    assert summary["report_path"] == str(data_dir / "reports/execution_venue_comparison.md")


def test_read_phase_gate_and_readiness_summaries_normalize_aliases(tmp_path) -> None:
    data_dir = tmp_path / "data"
    ops_dir = data_dir / "ops"
    ops_dir.mkdir(parents=True)
    (ops_dir / "phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,'
        '"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears",'
        '"strict_validation_passed":true,"strict_validation_issue_count":2,'
        '"checked_files":7}',
        encoding="utf-8",
    )
    (ops_dir / "readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )

    phase_gate = read_phase_gate_summary(data_dir)
    readiness = read_readiness_summary(data_dir)

    assert phase_gate["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert phase_gate["phase2_entry_allowed"] is False
    assert phase_gate["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert phase_gate["phase_gate_checked_files"] == 7
    assert readiness["next_phase_candidate"] == "Stay Phase 1"
    assert readiness["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert readiness["execution_ready"] is False
    assert readiness["readiness_execution_ready"] is False
