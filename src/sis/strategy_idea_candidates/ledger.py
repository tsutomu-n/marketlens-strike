from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_inputs.io import write_text_artifact


@dataclass(frozen=True)
class StrategyIdeaCandidateLedgerWriteResult:
    ledger_path: Path
    row_count: int


class StrategyIdeaCandidateLedgerError(ValueError):
    pass


class StrategyIdeaCandidateLedgerOutputExistsError(StrategyIdeaCandidateLedgerError):
    pass


def parameter_set_hash(parameter_set: dict[str, Any]) -> str:
    payload = json.dumps(parameter_set, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def search_ledger_rows_from_candidate_set(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    source_kind: str = "deterministic_generator",
    prompt_hash_by_candidate_id: dict[str, str | None] | None = None,
) -> list[dict[str, Any]]:
    prompt_hash_by_candidate_id = prompt_hash_by_candidate_id or {}
    rows: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidate_set.candidate_inventory, start=1):
        prompt_hash = prompt_hash_by_candidate_id.get(candidate.idea_candidate_id)
        metric_refs = [
            key
            for key, value in sorted(candidate.raw_validation_metrics.items())
            if value not in (None, "", [])
        ]
        rows.append(
            {
                "trial_id": candidate.trial_count_refs[0]
                if candidate.trial_count_refs
                else f"trial-{index:03d}",
                "candidate_id": candidate.idea_candidate_id,
                "candidate_status": candidate.candidate_status,
                "source_kind": source_kind,
                "family": candidate.family,
                "parameter_set_hash": parameter_set_hash(candidate.parameter_set),
                "prompt_hash": prompt_hash,
                "decision": candidate.decision.value,
                "rejection_reason": candidate.rejection_reason,
                "raw_metric_refs": metric_refs,
                "selection_adjusted_metrics_status": (
                    candidate.selection_adjusted_metrics_status.value
                ),
                "uses_sealed_test_for_selection": (
                    candidate.leakage_checks.get("uses_sealed_test_for_selection") is True
                ),
            }
        )
    return rows


def write_strategy_idea_candidate_search_ledger(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    out_dir: Path,
    source_kind: str = "deterministic_generator",
    prompt_hash_by_candidate_id: dict[str, str | None] | None = None,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateLedgerWriteResult:
    ledger_path = out_dir / "search_ledger.jsonl"
    if ledger_path.exists() and not replace_existing:
        raise StrategyIdeaCandidateLedgerOutputExistsError(f"output already exists: {ledger_path}")
    rows = search_ledger_rows_from_candidate_set(
        candidate_set=candidate_set,
        source_kind=source_kind,
        prompt_hash_by_candidate_id=prompt_hash_by_candidate_id,
    )
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if rows:
        text += "\n"
    write_text_artifact(ledger_path, text)
    return StrategyIdeaCandidateLedgerWriteResult(ledger_path=ledger_path, row_count=len(rows))
