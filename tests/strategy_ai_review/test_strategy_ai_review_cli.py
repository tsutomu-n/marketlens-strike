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
    assert "--model-reason" in stdout
    assert "[medium|xhigh]" in stdout
    assert "AI recommendation" in stdout


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
            "--model-reasoning-effort",
            "medium",
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
    assert "model_reasoning_effort=medium" in note_result.stdout
    assert "auto_applied=false" in note_result.stdout
    assert "permission_allowed=false" in note_result.stdout


def test_strategy_ai_review_findings_structure_cli_success(tmp_path: Path, monkeypatch) -> None:
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
            "codex-cli",
            "--model",
            "gpt-5.5",
            "--prompt-hash",
            PROMPT_HASH,
            "--finding",
            "Inspect the referenced strategy_case_lite.v1 source artifact.",
            "--limitation",
            "No raw market data inspected.",
            "--recommendation",
            "HUMAN_REVIEW_REQUIRED",
        ],
    )
    assert note_result.exit_code == 0

    structured_input = tmp_path / "structured_findings_input.json"
    structured_input.write_text(
        """[
  {
    "finding_type": "SOURCE_ARTIFACT_REVIEW",
    "severity": "MEDIUM",
    "review_impact": "HUMAN_REVIEW_REQUIRED",
    "statement": "Inspect the referenced strategy_case_lite.v1 source artifact.",
    "evidence_refs": [
      {"ref_type": "note_finding", "index": 0},
      {"ref_type": "packet_context_entry", "index": 0, "entry_key": "open_actions"}
    ],
    "recommended_next_action": "INSPECT_SOURCE_ARTIFACT",
    "limitations": ["No raw market data inspected."]
  }
]""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "strategy-ai-review-findings-structure",
            "--note",
            str(
                tmp_path / "data/strategy_ai_reviews/ndx-breakout-001/strategy_ai_review_note.json"
            ),
            "--structured-finding-json",
            str(structured_input),
        ],
    )

    assert result.exit_code == 0
    assert "finding_set_status=RECORDED" in result.stdout
    assert "finding_count=1" in result.stdout
