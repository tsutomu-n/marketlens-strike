from pathlib import Path

from sis.live_evidence_runner import (
    CollectionGateResult,
    LiveEvidenceManifest,
    RunOutcome,
    default_manifest_path,
    default_manifest_summary_path,
    evaluate_collection_volume,
    load_manifest,
    terminal_outcome,
    write_manifest,
    write_reports_for_manifest,
    write_manifest_summary,
)


def test_evaluate_collection_volume_pass() -> None:
    result = evaluate_collection_volume(
        metadata_rows_delta=96,
        pricing_rows_delta=500,
        min_metadata_rows=96,
    )

    assert result == CollectionGateResult.PASS


def test_evaluate_collection_volume_retryable_low_volume() -> None:
    result = evaluate_collection_volume(
        metadata_rows_delta=40,
        pricing_rows_delta=500,
        min_metadata_rows=96,
    )

    assert result == CollectionGateResult.RETRYABLE_LOW_VOLUME


def test_evaluate_collection_volume_hard_fail_when_pricing_missing() -> None:
    result = evaluate_collection_volume(
        metadata_rows_delta=96,
        pricing_rows_delta=0,
        min_metadata_rows=96,
    )

    assert result == CollectionGateResult.HARD_FAIL


def test_manifest_round_trip(tmp_path) -> None:
    path = tmp_path / "manifests/live_evidence_20260522_2308.json"
    manifest = LiveEvidenceManifest(
        run_id="20260522_2308",
        status=RunOutcome.COMPLETED_WITH_RETRIES,
        duration_minutes=120,
        metadata_interval_seconds=120,
        row_counts={"raw_quotes": 192},
        decision="GO",
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase2_entry_reason": "Need live window",
            "strict_validation_passed": False,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
        },
        readiness_summary={"next_phase_candidate": "Stay Phase 1", "execution_ready": False},
        execution_gap_history_summary={
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "execution_gap_history_report_path": "data/reports/execution_gap_history.md",
        },
        execution_state_comparison_summary={
            "entry_count": 4,
            "latest_status_match": False,
            "mismatching_count": 1,
            "execution_state_comparison_report_path": "data/reports/execution_state_comparison_history.md",
        },
        execution_snapshot_drift_summary={
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 2,
            "execution_snapshot_drift_report_path": "data/reports/execution_snapshot_drift_history.md",
        },
        execution_drift_overview_summary={
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 2,
        },
    )

    write_manifest(path, manifest)
    loaded = load_manifest(path)

    assert loaded.run_id == "20260522_2308"
    assert loaded.status == RunOutcome.COMPLETED_WITH_RETRIES
    assert loaded.row_counts["raw_quotes"] == 192
    assert loaded.phase_gate_summary["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert loaded.phase_gate_summary["phase2_entry_reason"] == "Need live window"
    assert loaded.phase_gate_summary["phase_gate_reason"] == "Need live window"
    assert loaded.phase_gate_summary["phase_gate_strict_validation_passed"] is False
    assert loaded.phase_gate_decision == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert loaded.phase2_entry_allowed is False
    assert loaded.phase_gate_reason == "Need live window"
    assert loaded.phase_gate_strict_validation_passed is False
    assert loaded.phase_gate_strict_validation_issue_count == 2
    assert loaded.phase_gate_checked_files == 7
    assert loaded.strict_validation_passed is False
    assert loaded.readiness_next_phase_candidate == "Stay Phase 1"
    assert loaded.readiness_execution_ready is False
    assert loaded.readiness_summary["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert loaded.readiness_summary["readiness_execution_ready"] is False
    assert loaded.execution_gap_history_summary["execution_gap_history_entry_count"] == 4
    assert loaded.execution_gap_history_summary["execution_gap_history_latest_status"] == "ok"
    assert (
        loaded.execution_gap_history_summary["execution_gap_history_latest_diagnostics_status"]
        == "degraded"
    )
    assert (
        loaded.execution_gap_history_summary["report_path"]
        == "data/reports/execution_gap_history.md"
    )
    assert loaded.execution_state_comparison_summary["execution_state_comparison_entry_count"] == 4
    assert (
        loaded.execution_state_comparison_summary["execution_state_comparison_latest_status_match"]
        is False
    )
    assert (
        loaded.execution_state_comparison_summary["execution_state_comparison_mismatching_count"]
        == 1
    )
    assert (
        loaded.execution_state_comparison_summary["report_path"]
        == "data/reports/execution_state_comparison_history.md"
    )
    assert loaded.execution_snapshot_drift_summary["execution_snapshot_drift_entry_count"] == 3
    assert (
        loaded.execution_snapshot_drift_summary["execution_snapshot_drift_latest_status_match"]
        is True
    )
    assert (
        loaded.execution_snapshot_drift_summary["execution_snapshot_drift_mismatching_snapshot_count"]
        == 2
    )
    assert (
        loaded.execution_snapshot_drift_summary["report_path"]
        == "data/reports/execution_snapshot_drift_history.md"
    )
    assert loaded.execution_drift_overview_status == "degraded"
    assert loaded.execution_drift_overview_diagnostics_alignment_match is False
    assert loaded.execution_drift_overview_summary["execution_drift_overview_status"] == "degraded"
    assert (
        loaded.execution_drift_overview_summary["execution_drift_overview_diagnostics_alignment_match"]
        is False
    )
    assert loaded.execution_drift_overview_state_comparison_mismatching_count == 1
    assert loaded.execution_drift_overview_snapshot_drift_mismatching_snapshot_count == 2


def test_terminal_outcome_recognizes_manifest_statuses() -> None:
    assert terminal_outcome("completed")
    assert terminal_outcome("completed_with_retries")
    assert terminal_outcome("partial_failed")
    assert terminal_outcome("failed_preflight")
    assert terminal_outcome("failed_collection")
    assert not terminal_outcome("running")


def test_default_manifest_path_uses_run_id() -> None:
    assert default_manifest_path("20260522_2308") == Path(
        "logs/live_evidence/manifests/live_evidence_20260522_2308.json"
    )


def test_write_manifest_summary_uses_run_id_and_phase_gate(tmp_path) -> None:
    manifest_path = tmp_path / "manifests/live_evidence_20260522_2308.json"
    data_dir = tmp_path / "data"
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"execution_gap_history_entry_count":4,"execution_gap_history_latest_status":"ok","execution_gap_history_latest_diagnostics_status":"degraded","execution_gap_history_report_path":"data/reports/execution_gap_history.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"execution_state_comparison_entry_count":4,"execution_state_comparison_latest_status_match":false,"execution_state_comparison_mismatching_count":1,"execution_state_comparison_report_path":"data/reports/execution_state_comparison_history.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"execution_snapshot_drift_entry_count":3,"execution_snapshot_drift_latest_status_match":true,"execution_snapshot_drift_mismatching_snapshot_count":1,"execution_snapshot_drift_report_path":"data/reports/execution_snapshot_drift_history.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    write_manifest(
        manifest_path,
        LiveEvidenceManifest(
            run_id="20260522_2308",
            status=RunOutcome.COMPLETED,
            duration_minutes=120,
            metadata_interval_seconds=60,
            data_dir=str(data_dir),
            decision="GO",
            phase_gate_summary={"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW", "phase2_entry_allowed": False},
        ),
    )

    summary_path = write_manifest_summary(manifest_path)

    assert summary_path == tmp_path / "summaries/live_evidence_summary_20260522_2308.json"
    assert '"phase_gate_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in summary_path.read_text(encoding="utf-8")
    assert '"phase2_entry_allowed": false' in summary_path.read_text(encoding="utf-8")
    assert '"phase2_entry_reason": null' in summary_path.read_text(encoding="utf-8")
    assert '"readiness_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in summary_path.read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in summary_path.read_text(encoding="utf-8")
    assert '"execution_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_comparison_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_diagnostics_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_gap_history_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_state_comparison_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_snapshot_drift_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_drift_overview_summary"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_gap_history_report_path": "data/reports/execution_gap_history.md"' in summary_path.read_text(
        encoding="utf-8"
    )
    assert (
        '"execution_state_comparison_report_path": "data/reports/execution_state_comparison_history.md"'
        in summary_path.read_text(encoding="utf-8")
    )
    assert (
        '"execution_snapshot_drift_report_path": "data/reports/execution_snapshot_drift_history.md"'
        in summary_path.read_text(encoding="utf-8")
    )
    assert '"execution_drift_overview_status": "degraded"' in summary_path.read_text(encoding="utf-8")
    assert '"execution_drift_overview_diagnostics_alignment_match": false' in summary_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_drift_overview_state_comparison_mismatching_count": 1' in summary_path.read_text(
        encoding="utf-8"
    )
    assert (
        '"execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1'
        in summary_path.read_text(encoding="utf-8")
    )
    assert default_manifest_summary_path("20260522_2308") == Path(
        "logs/live_evidence/summaries/live_evidence_summary_20260522_2308.json"
    )


def test_write_reports_for_manifest_persists_readiness_flat_keys(tmp_path) -> None:
    manifest_path = tmp_path / "manifests/live_evidence_20260522_2308.json"
    data_dir = tmp_path / "data"
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"Need live window","strict_validation_passed":false,"strict_validation_issue_count":2,"checked_files":7}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    log_path = tmp_path / "logs/live_evidence/run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("log line\n", encoding="utf-8")
    write_manifest(
        manifest_path,
        LiveEvidenceManifest(
            run_id="20260522_2308",
            status=RunOutcome.COMPLETED,
            duration_minutes=120,
            metadata_interval_seconds=60,
            data_dir=str(data_dir),
            log_path=str(log_path),
            manifest_path=str(manifest_path),
        ),
    )

    write_reports_for_manifest(manifest_path=manifest_path, settle_seconds=0)

    loaded = load_manifest(manifest_path)
    assert loaded.phase_gate_decision == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert loaded.phase2_entry_allowed is False
    assert loaded.phase_gate_summary["phase2_entry_reason"] == "Need live window"
    assert loaded.phase_gate_summary["phase_gate_strict_validation_passed"] is False
    assert loaded.phase_gate_reason == "Need live window"
    assert loaded.phase_gate_strict_validation_passed is False
    assert loaded.phase_gate_strict_validation_issue_count == 2
    assert loaded.phase_gate_checked_files == 7
    assert loaded.strict_validation_passed is False
    assert loaded.readiness_next_phase_candidate == "Stay Phase 1"
    assert loaded.readiness_execution_ready is False
    assert loaded.execution_drift_overview_status == "degraded"
