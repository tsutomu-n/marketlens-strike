from __future__ import annotations

from pathlib import Path

from sis.commands.report_writer_common import write_operation_chain_report


def test_write_operation_chain_report_passes_standard_paths_to_builder(tmp_path) -> None:
    calls: list[dict[str, Path]] = []

    def fake_builder(
        *,
        operation_chain_path: Path,
        out_path: Path,
        summary_path: Path,
    ) -> str:
        calls.append(
            {
                "operation_chain_path": operation_chain_path,
                "out_path": out_path,
                "summary_path": summary_path,
            }
        )
        return "report text"

    out, summary, text = write_operation_chain_report(
        settings_data_dir=tmp_path / "data",
        report_filename="paper_cycle_history_report.md",
        summary_filename="paper_cycle_history_summary.json",
        build_report=fake_builder,
    )

    assert out == tmp_path / "data/reports/paper_cycle_history_report.md"
    assert summary == tmp_path / "data/ops/paper_cycle_history_summary.json"
    assert text == "report text"
    assert calls == [
        {
            "operation_chain_path": tmp_path / "data/ops/operation_manifests.jsonl",
            "out_path": tmp_path / "data/reports/paper_cycle_history_report.md",
            "summary_path": tmp_path / "data/ops/paper_cycle_history_summary.json",
        }
    ]
