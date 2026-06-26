from pathlib import Path
from typing import Any

from sis.commands import report_remediation_writers as writers
from sis.commands import report_writers


def test_remediation_planner_writer_uses_standard_paths(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_build_remediation_planner(**kwargs: object) -> str:
        captured.update(kwargs)
        return "planner text"

    monkeypatch.setattr(
        writers,
        "build_remediation_planner",
        fake_build_remediation_planner,
    )

    out, summary, text = writers._write_remediation_planner(tmp_path)

    assert out == tmp_path / "reports/remediation_planner.md"
    assert summary == tmp_path / "ops/remediation_planner_summary.json"
    assert text == "planner text"
    assert captured == {
        "phase_gate_summary_path": tmp_path / "ops/phase_gate_review_summary.json",
        "runbook_summary_path": tmp_path / "ops/paper_operations_runbook_summary.json",
        "remediation_evaluator_summary_path": tmp_path / "ops/remediation_evaluator_summary.json",
        "remediation_command_results_summary_path": tmp_path
        / "ops/remediation_command_results_summary.json",
        "operation_chain_path": tmp_path / "ops/operation_manifests.jsonl",
        "out_path": out,
        "summary_path": summary,
    }


def test_remediation_session_checkpoint_writer_forwards_operator_inputs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_remediation_session_checkpoint(**kwargs: object) -> str:
        captured.update(kwargs)
        return "checkpoint text"

    monkeypatch.setattr(
        writers,
        "build_remediation_session_checkpoint",
        fake_build_remediation_session_checkpoint,
    )

    out, summary, text = writers._write_remediation_session_checkpoint(
        tmp_path,
        action_key="priority_1_check",
        result="retry",
        note="still failing",
        evidence_path="data/ops/evidence.log",
        observed_signal="strict validation reports issue count",
        stdout_summary="issues=2",
        stderr_summary="",
        exit_code=1,
    )

    assert out == tmp_path / "reports/remediation_session_checkpoint.md"
    assert summary == tmp_path / "ops/remediation_session_checkpoint_summary.json"
    assert text == "checkpoint text"
    assert captured == {
        "remediation_session_summary_path": tmp_path / "ops/remediation_session_summary.json",
        "checkpoint_summary_path": summary,
        "remediation_command_results_summary_path": tmp_path
        / "ops/remediation_command_results_summary.json",
        "remediation_evaluator_summary_path": tmp_path / "ops/remediation_evaluator_summary.json",
        "out_path": out,
        "summary_path": summary,
        "action_key": "priority_1_check",
        "result": "retry",
        "note": "still failing",
        "evidence_path": "data/ops/evidence.log",
        "observed_signal": "strict validation reports issue count",
        "stdout_summary": "issues=2",
        "stderr_summary": "",
        "exit_code": 1,
    }


def test_remediation_scoreboard_writer_is_reexported_from_report_writers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_remediation_scoreboard(**kwargs: object) -> str:
        captured.update(kwargs)
        return "scoreboard text"

    monkeypatch.setattr(
        writers,
        "build_remediation_scoreboard",
        fake_build_remediation_scoreboard,
    )

    out, summary, text = report_writers._write_remediation_scoreboard(tmp_path)

    assert report_writers._write_remediation_scoreboard is writers._write_remediation_scoreboard
    assert out == tmp_path / "reports/remediation_scoreboard.md"
    assert summary == tmp_path / "ops/remediation_scoreboard_summary.json"
    assert text == "scoreboard text"
    assert captured == {
        "remediation_session_checkpoint_summary_path": tmp_path
        / "ops/remediation_session_checkpoint_summary.json",
        "remediation_command_results_summary_path": tmp_path
        / "ops/remediation_command_results_summary.json",
        "remediation_evaluator_summary_path": tmp_path / "ops/remediation_evaluator_summary.json",
        "out_path": out,
        "summary_path": summary,
    }
