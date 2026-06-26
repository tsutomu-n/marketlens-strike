from pathlib import Path
from typing import Any

from sis.commands import report_execution_writers as writers
from sis.commands import report_writers


def test_execution_history_writers_use_expected_filenames(
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

    assert writers._write_execution_gap_history(tmp_path)[2] == "fake text"
    assert writers._write_execution_state_comparison_history(tmp_path)[2] == "fake text"
    assert writers._write_execution_snapshot_drift_history(tmp_path)[2] == "fake text"

    assert calls[0]["settings_data_dir"] == tmp_path
    assert calls[0]["report_filename"] == "execution_gap_history.md"
    assert calls[0]["summary_filename"] == "execution_gap_history_summary.json"
    assert calls[0]["build_report"] is writers.build_execution_gap_history_report
    assert calls[1]["settings_data_dir"] == tmp_path
    assert calls[1]["report_filename"] == "execution_state_comparison_history.md"
    assert calls[1]["summary_filename"] == "execution_state_comparison_history_summary.json"
    assert calls[1]["build_report"] is writers.build_execution_state_comparison_history_report
    assert calls[2]["settings_data_dir"] == tmp_path
    assert calls[2]["report_filename"] == "execution_snapshot_drift_history.md"
    assert calls[2]["summary_filename"] == "execution_snapshot_drift_history_summary.json"
    assert calls[2]["build_report"] is writers.build_execution_snapshot_drift_history_report


def test_execution_drift_overview_writer_uses_standard_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_execution_drift_overview_report(**kwargs: object) -> str:
        captured.update(kwargs)
        return "drift overview text"

    monkeypatch.setattr(
        writers,
        "build_execution_drift_overview_report",
        fake_build_execution_drift_overview_report,
    )

    out, summary, text = writers._write_execution_drift_overview(tmp_path)

    assert out == tmp_path / "reports/execution_drift_overview.md"
    assert summary == tmp_path / "ops/execution_drift_overview_summary.json"
    assert text == "drift overview text"
    assert captured == {
        "execution_gap_history_summary_path": tmp_path / "ops/execution_gap_history_summary.json",
        "execution_state_comparison_history_summary_path": tmp_path
        / "ops/execution_state_comparison_history_summary.json",
        "execution_snapshot_drift_history_summary_path": tmp_path
        / "ops/execution_snapshot_drift_history_summary.json",
        "out_path": out,
        "summary_path": summary,
    }


def test_execution_drift_overview_writer_is_reexported_from_report_writers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_execution_drift_overview_report(**kwargs: object) -> str:
        captured.update(kwargs)
        return "reexport text"

    monkeypatch.setattr(
        writers,
        "build_execution_drift_overview_report",
        fake_build_execution_drift_overview_report,
    )

    out, summary, text = report_writers._write_execution_drift_overview(tmp_path)

    assert report_writers._write_execution_drift_overview is writers._write_execution_drift_overview
    assert out == tmp_path / "reports/execution_drift_overview.md"
    assert summary == tmp_path / "ops/execution_drift_overview_summary.json"
    assert text == "reexport text"
    assert captured["execution_gap_history_summary_path"] == (
        tmp_path / "ops/execution_gap_history_summary.json"
    )
    assert captured["out_path"] == out
    assert captured["summary_path"] == summary
