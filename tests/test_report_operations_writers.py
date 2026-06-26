from pathlib import Path
from typing import Any

from sis.commands import report_operations_writers as writers
from sis.commands import report_writers


def test_ops_review_writer_uses_standard_paths(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_build_ops_review_report(**kwargs: object) -> str:
        captured.update(kwargs)
        return "ops review text"

    monkeypatch.setattr(writers, "build_ops_review_report", fake_build_ops_review_report)

    out, summary, text = writers._write_ops_review(tmp_path)

    assert out == tmp_path / "reports/ops_review_report.md"
    assert summary == tmp_path / "ops/ops_review_summary.json"
    assert text == "ops review text"
    assert captured["operation_chain_path"] == tmp_path / "ops/operation_manifests.jsonl"
    assert captured["operations_bundle_manifest_path"] == (
        tmp_path / "ops/operations_bundle_manifest.json"
    )
    assert captured["phase_gate_summary_path"] == tmp_path / "ops/phase_gate_review_summary.json"
    assert captured["readiness_summary_path"] == tmp_path / "ops/readiness_snapshot.json"
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary


def test_operations_dashboard_writer_uses_standard_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_operations_dashboard(**kwargs: object) -> str:
        captured.update(kwargs)
        return "dashboard text"

    monkeypatch.setattr(
        writers,
        "build_operations_dashboard",
        fake_build_operations_dashboard,
    )

    out, summary, text = writers._write_operations_dashboard(tmp_path)

    assert out == tmp_path / "reports/operations_dashboard.md"
    assert summary == tmp_path / "ops/operations_dashboard_summary.json"
    assert text == "dashboard text"
    assert captured["operations_timeline_summary_path"] == (
        tmp_path / "ops/operations_timeline_summary.json"
    )
    assert captured["ops_review_summary_path"] == tmp_path / "ops/ops_review_summary.json"
    assert captured["execution_drift_overview_summary_path"] == (
        tmp_path / "ops/execution_drift_overview_summary.json"
    )
    assert captured["operations_bundle_manifest_path"] == (
        tmp_path / "ops/operations_bundle_manifest.json"
    )
    assert captured["phase_gate_summary_path"] == tmp_path / "ops/phase_gate_review_summary.json"
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary


def test_paper_operations_runbook_writer_uses_standard_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_paper_operations_runbook(**kwargs: object) -> str:
        captured.update(kwargs)
        return "runbook text"

    monkeypatch.setattr(
        writers,
        "build_paper_operations_runbook",
        fake_build_paper_operations_runbook,
    )

    out, summary, text = writers._write_paper_operations_runbook(tmp_path)

    assert out == tmp_path / "reports/paper_operations_runbook.md"
    assert summary == tmp_path / "ops/paper_operations_runbook_summary.json"
    assert text == "runbook text"
    assert captured["scheduled_run_path"] == tmp_path / "ops/scheduled_run.json"
    assert captured["ops_dashboard_summary_path"] == (
        tmp_path / "ops/operations_dashboard_summary.json"
    )
    assert captured["remediation_evaluator_summary_path"] == (
        tmp_path / "ops/remediation_evaluator_summary.json"
    )
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary


def test_operation_chain_writers_use_expected_filenames(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_write_operation_chain_report(**kwargs: object) -> tuple[Path, Path, str]:
        calls.append(dict(kwargs))
        return tmp_path / "reports/fake.md", tmp_path / "ops/fake.json", "fake text"

    monkeypatch.setattr(
        writers,
        "write_operation_chain_report",
        fake_write_operation_chain_report,
    )

    assert writers._write_paper_cycle_history(tmp_path)[2] == "fake text"
    assert writers._write_operations_timeline(tmp_path)[2] == "fake text"

    assert calls[0]["settings_data_dir"] == tmp_path
    assert calls[0]["report_filename"] == "paper_cycle_history_report.md"
    assert calls[0]["summary_filename"] == "paper_cycle_history_summary.json"
    assert calls[0]["build_report"] is writers.build_paper_cycle_history_report
    assert calls[1]["settings_data_dir"] == tmp_path
    assert calls[1]["report_filename"] == "operations_timeline_report.md"
    assert calls[1]["summary_filename"] == "operations_timeline_summary.json"
    assert calls[1]["build_report"] is writers.build_operations_timeline_report


def test_operations_audit_pack_writer_is_reexported_from_report_writers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_operations_audit_pack(**kwargs: object) -> str:
        captured.update(kwargs)
        return "audit pack text"

    monkeypatch.setattr(
        writers,
        "build_operations_audit_pack",
        fake_build_operations_audit_pack,
    )

    out, manifest, text = report_writers._write_operations_audit_pack(tmp_path)

    assert report_writers._write_operations_audit_pack is writers._write_operations_audit_pack
    assert out == tmp_path / "reports/operations_audit_pack.md"
    assert manifest == tmp_path / "ops/operations_audit_pack.json"
    assert text == "audit pack text"
    assert captured["bundle_manifest_path"] == tmp_path / "ops/operations_bundle_manifest.json"
    assert captured["timeline_summary_path"] == tmp_path / "ops/operations_timeline_summary.json"
    assert captured["cycle_history_summary_path"] == (
        tmp_path / "ops/paper_cycle_history_summary.json"
    )
    assert captured["phase_gate_summary_path"] == tmp_path / "ops/phase_gate_review_summary.json"
    assert captured["out_path"] == out
    assert captured["manifest_path"] == manifest
