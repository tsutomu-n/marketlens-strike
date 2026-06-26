from pathlib import Path
from typing import Any

from sis.commands import report_state_writers as writers
from sis.commands import report_writers


def test_audit_dashboard_writer_uses_standard_paths(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_build_audit_dashboard(**kwargs: object) -> str:
        captured.update(kwargs)
        return "audit dashboard text"

    monkeypatch.setattr(writers, "build_audit_dashboard", fake_build_audit_dashboard)

    out, summary, text = writers._write_audit_dashboard(tmp_path)

    assert out == tmp_path / "reports/audit_dashboard.md"
    assert summary == tmp_path / "ops/audit_dashboard_summary.json"
    assert text == "audit dashboard text"
    assert captured["bundle_manifest_path"] == tmp_path / "ops/operations_bundle_manifest.json"
    assert captured["audit_pack_path"] == tmp_path / "ops/operations_audit_pack.json"
    assert captured["audit_bundle_history_summary_path"] == (
        tmp_path / "ops/audit_bundle_history_summary.json"
    )
    assert captured["phase_gate_summary_path"] == tmp_path / "ops/phase_gate_review_summary.json"
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary


def test_current_state_index_writer_uses_latest_live_evidence_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}
    summaries_root = tmp_path / "logs/live_evidence/summaries"
    summaries_root.mkdir(parents=True)
    (summaries_root / "live_evidence_summary_20260522_2308.json").touch()
    latest_name = "live_evidence_summary_20260523_0100.json"
    (summaries_root / latest_name).touch()
    monkeypatch.chdir(tmp_path)

    def fake_build_current_state_index(**kwargs: object) -> str:
        captured.update(kwargs)
        return "current state text"

    monkeypatch.setattr(
        writers,
        "build_current_state_index",
        fake_build_current_state_index,
    )

    out, summary, text = writers._write_current_state_index(tmp_path / "data")

    assert out == tmp_path / "data/reports/current_state_index.md"
    assert summary == tmp_path / "data/ops/current_state_index.json"
    assert text == "current state text"
    assert captured["operations_dashboard_summary_path"] == (
        tmp_path / "data/ops/operations_dashboard_summary.json"
    )
    assert captured["backtest_metrics_summary_path"] == (
        tmp_path / "data/research/backtest_metrics_summary.json"
    )
    assert (
        captured["live_evidence_summary_path"] == Path("logs/live_evidence/summaries") / latest_name
    )
    assert captured["research_quality_report_path"] == (
        tmp_path / "data/research/research_quality_report.md"
    )


def test_readiness_snapshot_writer_is_reexported_from_report_writers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_readiness_snapshot(**kwargs: object) -> str:
        captured.update(kwargs)
        return "readiness text"

    monkeypatch.setattr(
        writers,
        "build_readiness_snapshot",
        fake_build_readiness_snapshot,
    )

    out, summary, text = report_writers._write_readiness_snapshot(tmp_path)

    assert report_writers._write_readiness_snapshot is writers._write_readiness_snapshot
    assert out == tmp_path / "reports/readiness_snapshot.md"
    assert summary == tmp_path / "ops/readiness_snapshot.json"
    assert text == "readiness text"
    assert captured["current_state_index_path"] == tmp_path / "ops/current_state_index.json"
    assert captured["phase_gate_summary_path"] == tmp_path / "ops/phase_gate_review_summary.json"
    assert captured["operations_dashboard_summary_path"] == (
        tmp_path / "ops/operations_dashboard_summary.json"
    )
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary
