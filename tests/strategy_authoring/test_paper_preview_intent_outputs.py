from __future__ import annotations

import json

from sis.research.strategy_lab.authoring.compiler.paper_preview_intent_outputs import (
    _write_empty_paper_intent_preview_outputs,
)


def test_write_empty_paper_intent_preview_outputs_writes_json_and_report(tmp_path) -> None:
    paths = _write_empty_paper_intent_preview_outputs(
        data_dir=tmp_path,
        decision="hold",
        scorecard_summary={
            "schema_version": "strategy_authoring_scorecard.v1",
            "failed_thresholds": ["total_return"],
        },
    )

    assert set(paths) == {"paper_intent_preview", "paper_intent_preview_report"}
    preview = json.loads(paths["paper_intent_preview"].read_text(encoding="utf-8"))
    report = paths["paper_intent_preview_report"].read_text(encoding="utf-8")

    assert preview == []
    assert "# Paper Intent Preview" in report
    assert "- source: strategy_authoring" in report
    assert "- decision: hold" in report
    assert "- intents: 0" in report
    assert "- scorecard_schema_version: strategy_authoring_scorecard.v1" in report
    assert "- scorecard_failed_thresholds: ['total_return']" in report
    assert "- paper_only: true" in report
