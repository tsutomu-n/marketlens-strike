from __future__ import annotations

from collections.abc import Iterable

from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord


class EvaluationRunner:
    def __init__(self, *, ledger: TrialLedger) -> None:
        self.ledger = ledger

    def record_trials(self, trials: Iterable[TrialRecord]) -> list[TrialRecord]:
        records = list(trials)
        for record in records:
            self.ledger.append(record)
        return records
