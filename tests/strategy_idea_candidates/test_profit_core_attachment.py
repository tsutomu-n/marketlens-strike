from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.strategy_idea_candidates.ledger import search_ledger_rows_from_candidate_set
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_inputs.io import write_json_artifact
from support.cli import normalized_stdout

from .fixtures import copy_payload, valid_candidate_set_payload


runner = CliRunner()


def _write_candidate_set_and_ledger(tmp_path: Path) -> tuple[Path, Path, StrategyIdeaCandidateSet]:
    candidate_set = StrategyIdeaCandidateSet.model_validate(valid_candidate_set_payload())
    candidate_set_path = tmp_path / "strategy_idea_candidate_set.json"
    ledger_path = tmp_path / "search_ledger.jsonl"
    write_json_artifact(candidate_set_path, candidate_set.model_dump(mode="json"))
    ledger_rows = search_ledger_rows_from_candidate_set(candidate_set=candidate_set)
    ledger_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger_rows),
        encoding="utf-8",
    )
    return candidate_set_path, ledger_path, candidate_set


def test_profit_core_multiplicity_account_from_candidate_set_and_ledger(
    tmp_path: Path,
) -> None:
    from sis.strategy_idea_candidates.profit_core import (
        build_trial_multiplicity_account_from_candidate_set,
    )

    candidate_set_path, ledger_path, candidate_set = _write_candidate_set_and_ledger(tmp_path)

    account = build_trial_multiplicity_account_from_candidate_set(
        candidate_set=candidate_set,
        ledger_path=ledger_path,
    )

    assert account.schema_version == "trial_multiplicity_account.v1"
    assert account.account_id == "ndx-candidate-set-001-trial-multiplicity"
    assert account.candidate_count_total == 2
    assert account.family_trial_count == {"trend_momentum": 2}
    assert account.raw_p_value_count == 0
    assert account.fdr_status == "NOT_ESTIMABLE"
    assert "RAW_P_VALUE_MISSING_FOR_BH_FDR" in account.not_estimable_reasons
    assert account.success_only_reporting is False
    assert account.sealed_test_used_for_selection is False
    assert candidate_set_path.exists()


def test_profit_core_multiplicity_account_rejects_ledger_mismatch(tmp_path: Path) -> None:
    from sis.strategy_idea_candidates.profit_core import (
        build_trial_multiplicity_account_from_candidate_set,
    )

    _candidate_set_path, ledger_path, candidate_set = _write_candidate_set_and_ledger(tmp_path)
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    rows.pop()
    ledger_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ledger candidate ids must match candidate set"):
        build_trial_multiplicity_account_from_candidate_set(
            candidate_set=candidate_set,
            ledger_path=ledger_path,
        )


def test_profit_core_multiplicity_account_cli_writes_sidecar(tmp_path: Path) -> None:
    candidate_set_path, ledger_path, _candidate_set = _write_candidate_set_and_ledger(tmp_path)
    out_dir = tmp_path / "profit_core"

    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-multiplicity-account-build",
            "--candidate-set",
            str(candidate_set_path),
            "--ledger",
            str(ledger_path),
            "--out",
            str(out_dir),
        ],
    )

    stdout = normalized_stdout(result)
    assert result.exit_code == 0, result.stdout
    assert "status=pass" in stdout
    account_path = out_dir / "trial_multiplicity_account.json"
    payload = json.loads(account_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "trial_multiplicity_account.v1"
    assert payload["fdr_status"] == "NOT_ESTIMABLE"


def test_profit_core_multiplicity_account_counts_raw_p_values(tmp_path: Path) -> None:
    from sis.strategy_idea_candidates.profit_core import (
        build_trial_multiplicity_account_from_candidate_set,
    )

    payload = copy_payload(valid_candidate_set_payload())
    payload["candidate_inventory"][0]["raw_validation_metrics"]["raw_p_value"] = 0.04
    payload["candidate_inventory"][1]["raw_validation_metrics"]["raw_p_value"] = 0.50
    candidate_set = StrategyIdeaCandidateSet.model_validate(payload)
    ledger_path = tmp_path / "search_ledger.jsonl"
    ledger_rows = search_ledger_rows_from_candidate_set(candidate_set=candidate_set)
    ledger_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger_rows),
        encoding="utf-8",
    )

    account = build_trial_multiplicity_account_from_candidate_set(
        candidate_set=candidate_set,
        ledger_path=ledger_path,
    )

    assert account.raw_p_value_count == 2
    assert account.fdr_status == "AVAILABLE"
