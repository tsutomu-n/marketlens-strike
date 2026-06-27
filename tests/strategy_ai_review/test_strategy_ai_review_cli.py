from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from support.cli import normalized_stdout

from .test_strategy_ai_review import PROMPT_HASH, _safe_source


runner = CliRunner()


def test_strategy_ai_review_packet_build_help() -> None:
    result = runner.invoke(app, ["strategy-ai-review-packet-build", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--source" in stdout
    assert "--review-question" in stdout


def test_strategy_ai_review_note_record_help() -> None:
    result = runner.invoke(app, ["strategy-ai-review-note-record", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--prompt-hash" in stdout
    assert "--recommendation" in stdout


def test_strategy_ai_review_packet_and_note_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    packet_result = runner.invoke(
        app,
        [
            "strategy-ai-review-packet-build",
            "--source",
            str(_safe_source(tmp_path)),
            "--out",
            str(tmp_path / "data/strategy_ai_reviews/ndx-breakout-001"),
        ],
    )

    assert packet_result.exit_code == 0
    assert "packet_status=READY_FOR_AI_REVIEW" in packet_result.stdout
    assert "context_section_count=1" in packet_result.stdout

    note_result = runner.invoke(
        app,
        [
            "strategy-ai-review-note-record",
            "--packet",
            str(
                tmp_path
                / "data/strategy_ai_reviews/ndx-breakout-001/strategy_ai_review_packet.json"
            ),
            "--provider",
            "openai",
            "--model",
            "gpt-reviewer",
            "--prompt-hash",
            PROMPT_HASH,
            "--finding",
            "Review return drift.",
            "--limitation",
            "No raw market data inspected.",
            "--recommendation",
            "REVISE",
        ],
    )

    assert note_result.exit_code == 0
    assert "auto_applied=false" in note_result.stdout
    assert "permission_allowed=false" in note_result.stdout
