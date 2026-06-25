from __future__ import annotations

from pathlib import Path


def test_runner_delegates_metrics_post_enrichment_details() -> None:
    runner_text = Path("src/sis/backtest/engine/runner.py").read_text(encoding="utf-8")
    completion_text = Path("src/sis/backtest/engine/run_completion.py").read_text(encoding="utf-8")
    outputs_text = Path("src/sis/backtest/engine/run_outputs.py").read_text(encoding="utf-8")

    assert "complete_backtest_run" in runner_text
    assert "build_run_outputs" not in runner_text
    assert "build_run_outputs" in completion_text
    assert "enrich_run_metrics" in outputs_text
    assert 'metrics["open_position_at_end"]' not in runner_text
    assert 'metrics["end_position_policy"]' not in runner_text
    assert 'metrics["funding_events_ref"]' not in runner_text
    assert 'metrics["funding_event_count"]' not in runner_text
