from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from sis.strategy_learning.models import (
    LearningEventType,
    LearningRecommendedAction,
    LearningSourceArtifact,
    StrategyLearningEvent,
)
from sis.strategy_learning.service_ledger import (
    LearningLedgerIOError,
    read_learning_ledger,
    write_learning_ledger,
)
from sis.strategy_stage.models import StageProducer


def _event(event_id: str = "learn-001") -> StrategyLearningEvent:
    return StrategyLearningEvent(
        learning_event_id=event_id,
        strategy_id="ndx-breakout-001",
        created_at=datetime(2026, 6, 19, tzinfo=timezone.utc),
        producer=StageProducer(command="strategy-learning-ledger-update"),
        source_stage="paper_smoke",
        source_artifacts=[
            LearningSourceArtifact(
                artifact_key="paper_vs_backtest_drift_review",
                path="data/review.json",
                sha256="sha256:" + "b" * 64,
                schema_version="paper_vs_backtest_drift_review.v1",
            )
        ],
        event_type=LearningEventType.EXECUTION_ASSUMPTION_UPDATE,
        finding="Drift review failed conditions: runtime_no_fill_rate_within_limit",
        impact="Runtime behavior may invalidate execution assumptions used by the backtest.",
        recommended_action=LearningRecommendedAction.REVISE_STRATEGY,
        source_review_status="READY_FOR_HUMAN_DRIFT_REVIEW",
        source_recommended_action="REVISE_STRATEGY",
    )


def test_read_learning_ledger_returns_empty_for_missing_path(tmp_path: Path) -> None:
    assert read_learning_ledger(tmp_path / "missing.jsonl") == []


def test_read_learning_ledger_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "learning_ledger.jsonl"
    payload = _event().model_dump(mode="json")
    path.write_text("\n" + json.dumps(payload) + "\n\n", encoding="utf-8")

    assert read_learning_ledger(path) == [_event()]


def test_read_learning_ledger_reports_invalid_json_line(tmp_path: Path) -> None:
    path = tmp_path / "learning_ledger.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")

    with pytest.raises(LearningLedgerIOError, match="invalid learning ledger JSONL"):
        read_learning_ledger(path)


def test_write_learning_ledger_uses_sorted_keys_newline_and_temp_cleanup(tmp_path: Path) -> None:
    path = tmp_path / "nested/learning_ledger.jsonl"
    event = _event()

    written = write_learning_ledger(path, [event])

    assert written == path
    assert path.exists()
    assert not (path.parent / ".learning_ledger.jsonl.tmp").exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == event.model_dump(mode="json")
    assert lines[0].index('"auto_applied"') < lines[0].index('"boundary"')
