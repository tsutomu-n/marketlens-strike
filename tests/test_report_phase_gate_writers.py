from pathlib import Path
from typing import Any

from sis.commands import report_phase_gate_writers as writers
from sis.commands import report_writers


def test_phase_gate_review_writer_uses_standard_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_phase_gate_review(*args: object, **kwargs: object) -> str:
        captured["args"] = args
        captured.update(kwargs)
        return "phase gate text"

    monkeypatch.setattr(writers, "build_phase_gate_review", fake_build_phase_gate_review)

    out, summary, text = writers._write_phase_gate_review(tmp_path)

    assert out == tmp_path / "reports/phase_gate_review.md"
    assert summary == tmp_path / "ops/phase_gate_review_summary.json"
    assert text == "phase gate text"
    assert captured["args"] == (tmp_path,)
    assert captured["schema_root"] == Path(writers.__file__).resolve().parents[3] / "schemas"
    assert captured["execution_snapshot_summary_path"] == (
        tmp_path / "ops/execution_snapshot_summary.json"
    )
    assert captured["execution_venue_comparison_summary_path"] == (
        tmp_path / "ops/execution_venue_comparison_summary.json"
    )
    assert captured["execution_drift_overview_summary_path"] == (
        tmp_path / "ops/execution_drift_overview_summary.json"
    )
    assert captured["remediation_planner_summary_path"] == (
        tmp_path / "ops/remediation_planner_summary.json"
    )
    assert captured["remediation_evaluator_summary_path"] == (
        tmp_path / "ops/remediation_evaluator_summary.json"
    )
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary


def test_phase_gate_review_writer_is_reexported_from_report_writers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_phase_gate_review(*args: object, **kwargs: object) -> str:
        captured["args"] = args
        captured.update(kwargs)
        return "reexport text"

    monkeypatch.setattr(writers, "build_phase_gate_review", fake_build_phase_gate_review)

    out, summary, text = report_writers._write_phase_gate_review(tmp_path)

    assert report_writers._write_phase_gate_review is writers._write_phase_gate_review
    assert out == tmp_path / "reports/phase_gate_review.md"
    assert summary == tmp_path / "ops/phase_gate_review_summary.json"
    assert text == "reexport text"
    assert captured["args"] == (tmp_path,)
    assert captured["schema_root"] == Path(writers.__file__).resolve().parents[3] / "schemas"
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary
