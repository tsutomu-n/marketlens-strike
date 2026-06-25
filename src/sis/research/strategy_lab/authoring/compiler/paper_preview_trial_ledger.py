from __future__ import annotations

from pathlib import Path

from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord


def _append_paper_preview_trial_record_once(*, data_dir: Path, record: TrialRecord) -> Path:
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)
    return ledger_path
