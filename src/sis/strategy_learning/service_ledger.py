from __future__ import annotations

import json
from pathlib import Path

from sis.strategy_learning.models import StrategyLearningEvent


class LearningLedgerIOError(ValueError):
    pass


def read_learning_ledger(path: Path) -> list[StrategyLearningEvent]:
    if not path.exists():
        return []
    events: list[StrategyLearningEvent] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise LearningLedgerIOError(f"invalid learning ledger JSONL at {path}:{index}") from exc
        events.append(StrategyLearningEvent.model_validate(payload))
    return events


def write_learning_ledger(path: Path, events: list[StrategyLearningEvent]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"
    try:
        tmp_path.write_text(
            "".join(
                json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
                for event in events
            ),
            encoding="utf-8",
        )
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path
