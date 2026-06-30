from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import sha256_file
from sis.edge_candidates.multiplicity import SelectionAdjustmentStatus, TrialMultiplicityAccount
from sis.edge_candidates.protocol import CandidateProtocolManifest, CandidateProtocolMode
from sis.strategy_idea_candidates.models import CandidateDecision, StrategyIdeaCandidateSet
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact


_P_VALUE_KEYS = ("validation_p_value", "p_value", "raw_p_value")


@dataclass(frozen=True)
class TrialMultiplicityAccountWriteResult:
    account: TrialMultiplicityAccount
    account_path: Path
    account_sha256: str
    protocol_manifest_path: Path | None = None
    protocol_manifest_sha256: str | None = None


class ProfitCoreAttachmentError(ValueError):
    pass


class ProfitCoreAttachmentOutputExistsError(ProfitCoreAttachmentError):
    pass


def build_trial_multiplicity_account_from_candidate_set(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    ledger_path: Path,
    protocol_manifest_path: Path | None = None,
) -> TrialMultiplicityAccount:
    ledger_rows = _read_jsonl_objects(ledger_path)
    _validate_ledger_matches_candidate_set(candidate_set=candidate_set, ledger_rows=ledger_rows)
    protocol = _load_protocol(protocol_manifest_path)
    if protocol is not None:
        _validate_protocol_covers_candidate_set(protocol=protocol, candidate_set=candidate_set)

    raw_p_value_count = _raw_p_value_count(candidate_set)
    not_estimable_reasons = [
        "PBO_NOT_ESTIMABLE_FOLD_OUTCOMES_MISSING",
        "DSR_NOT_ESTIMABLE_RETURN_DISTRIBUTION_MISSING",
        "WHITE_REALITY_CHECK_NOT_ESTIMABLE_BOOTSTRAP_SERIES_MISSING",
        "EFFECTIVE_TRIAL_COUNT_NOT_ESTIMABLE",
        "CORRELATION_CLUSTER_COUNT_NOT_ESTIMABLE",
    ]
    fdr_status = SelectionAdjustmentStatus.AVAILABLE
    if raw_p_value_count == 0:
        fdr_status = SelectionAdjustmentStatus.NOT_ESTIMABLE
        not_estimable_reasons.append("RAW_P_VALUE_MISSING_FOR_BH_FDR")

    family_trial_count = _family_trial_count(candidate_set=candidate_set, ledger_rows=ledger_rows)
    parameter_grid_hashes = {
        family_id: _stable_sha256(candidate_set.parameter_grids.get(family_id, []))
        for family_id in sorted(family_trial_count)
    }
    return TrialMultiplicityAccount(
        account_id=f"{candidate_set.candidate_set_id}-trial-multiplicity",
        mode=protocol.mode
        if protocol is not None
        else CandidateProtocolMode.VERIFICATION_THROUGHPUT,
        candidate_count_total=len(ledger_rows),
        candidate_count_shortlisted=candidate_set.search_ledger_summary.candidate_count_shortlisted,
        family_count=len(family_trial_count),
        family_trial_count=dict(sorted(family_trial_count.items())),
        parameter_grid_hashes=parameter_grid_hashes,
        effective_trial_count=None,
        correlation_cluster_count=None,
        validation_peek_count=candidate_set.search_ledger_summary.validation_peek_count,
        rerank_count=candidate_set.search_ledger_summary.rerank_count,
        sealed_test_used_for_selection=False,
        success_only_reporting=False,
        raw_p_value_count=raw_p_value_count,
        fdr_status=fdr_status,
        pbo_status=SelectionAdjustmentStatus.NOT_ESTIMABLE,
        dsr_status=SelectionAdjustmentStatus.NOT_ESTIMABLE,
        white_reality_check_status=SelectionAdjustmentStatus.NOT_ESTIMABLE,
        not_estimable_reasons=not_estimable_reasons,
    )


def write_trial_multiplicity_account_from_candidate_set(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    ledger_path: Path,
    out_dir: Path,
    protocol_manifest_path: Path | None = None,
    replace_existing: bool = False,
) -> TrialMultiplicityAccountWriteResult:
    account_path = out_dir / "trial_multiplicity_account.json"
    if account_path.exists() and not replace_existing:
        raise ProfitCoreAttachmentOutputExistsError(f"output already exists: {account_path}")
    account = build_trial_multiplicity_account_from_candidate_set(
        candidate_set=candidate_set,
        ledger_path=ledger_path,
        protocol_manifest_path=protocol_manifest_path,
    )
    write_json_artifact(account_path, account.model_dump(mode="json"))
    protocol_sha256 = (
        sha256_file(protocol_manifest_path) if protocol_manifest_path is not None else None
    )
    return TrialMultiplicityAccountWriteResult(
        account=account,
        account_path=account_path,
        account_sha256=sha256_file(account_path),
        protocol_manifest_path=protocol_manifest_path,
        protocol_manifest_sha256=protocol_sha256,
    )


def _read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"candidate search ledger missing: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProfitCoreAttachmentError(
                f"invalid search ledger JSON at line {line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ProfitCoreAttachmentError(
                f"search ledger line {line_number} must be a JSON object"
            )
        rows.append(payload)
    return rows


def _validate_ledger_matches_candidate_set(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    ledger_rows: list[dict[str, Any]],
) -> None:
    candidate_by_id = {
        candidate.idea_candidate_id: candidate for candidate in candidate_set.candidate_inventory
    }
    ledger_ids = [str(row.get("candidate_id") or "") for row in ledger_rows]
    if any(not candidate_id for candidate_id in ledger_ids):
        raise ProfitCoreAttachmentError("ledger rows must include candidate_id")
    if len(ledger_ids) != len(set(ledger_ids)):
        raise ProfitCoreAttachmentError("ledger candidate ids must be unique")
    if set(ledger_ids) != set(candidate_by_id):
        raise ProfitCoreAttachmentError("ledger candidate ids must match candidate set")
    summary = candidate_set.search_ledger_summary
    if len(ledger_rows) != summary.candidate_count_total:
        raise ProfitCoreAttachmentError("ledger row count must match candidate_count_total")
    if summary.success_only_reporting is not False:
        raise ProfitCoreAttachmentError("success_only_reporting must be false")
    if summary.sealed_test_used_for_selection is not False:
        raise ProfitCoreAttachmentError("sealed_test_used_for_selection must be false")
    for row in ledger_rows:
        candidate = candidate_by_id[str(row["candidate_id"])]
        if row.get("family") is not None and row["family"] != candidate.family:
            raise ProfitCoreAttachmentError("ledger family must match candidate set")
        if row.get("decision") is not None:
            expected = (
                candidate.decision.value
                if isinstance(candidate.decision, CandidateDecision)
                else str(candidate.decision)
            )
            if row["decision"] != expected:
                raise ProfitCoreAttachmentError("ledger decision must match candidate set")
        if row.get("uses_sealed_test_for_selection") is True:
            raise ProfitCoreAttachmentError("ledger must not use sealed test for selection")


def _load_protocol(protocol_manifest_path: Path | None) -> CandidateProtocolManifest | None:
    if protocol_manifest_path is None:
        return None
    return CandidateProtocolManifest.model_validate(read_mapping_file(protocol_manifest_path))


def _validate_protocol_covers_candidate_set(
    *,
    protocol: CandidateProtocolManifest,
    candidate_set: StrategyIdeaCandidateSet,
) -> None:
    protocol_families = {family.family_id for family in protocol.families}
    candidate_families = {candidate.family for candidate in candidate_set.candidate_inventory}
    missing = sorted(candidate_families - protocol_families)
    if missing:
        raise ProfitCoreAttachmentError(
            "protocol manifest missing candidate families: " + ", ".join(missing)
        )


def _family_trial_count(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    ledger_rows: list[dict[str, Any]],
) -> Counter[str]:
    candidate_by_id = {
        candidate.idea_candidate_id: candidate for candidate in candidate_set.candidate_inventory
    }
    counts: Counter[str] = Counter()
    for row in ledger_rows:
        candidate = candidate_by_id[str(row["candidate_id"])]
        family_id = str(row.get("family") or candidate.family)
        counts[family_id] += 1
    return counts


def _raw_p_value_count(candidate_set: StrategyIdeaCandidateSet) -> int:
    count = 0
    for candidate in candidate_set.candidate_inventory:
        for key in _P_VALUE_KEYS:
            value = candidate.raw_validation_metrics.get(key)
            if isinstance(value, int | float) and not isinstance(value, bool):
                if 0 <= float(value) <= 1:
                    count += 1
                    break
    return count


def _stable_sha256(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
