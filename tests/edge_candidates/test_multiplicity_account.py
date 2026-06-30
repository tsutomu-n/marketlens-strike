from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from sis.edge_candidates.multiplicity import TrialMultiplicityAccount


REPO_ROOT = Path(__file__).resolve().parents[2]
SHA256_A = "sha256:" + "a" * 64


def valid_account_payload() -> dict:
    return {
        "schema_version": "trial_multiplicity_account.v1",
        "account_id": "btc-perp-trials-001",
        "mode": "verification_throughput",
        "candidate_count_total": 10,
        "candidate_count_shortlisted": 2,
        "family_count": 1,
        "family_trial_count": {"intraday_breakout": 10},
        "parameter_grid_hashes": {"intraday_breakout": SHA256_A},
        "effective_trial_count": 4,
        "correlation_cluster_count": 3,
        "validation_peek_count": 0,
        "rerank_count": 0,
        "sealed_test_used_for_selection": False,
        "success_only_reporting": False,
        "raw_p_value_count": 2,
        "fdr_status": "AVAILABLE",
        "pbo_status": "NOT_ESTIMABLE",
        "dsr_status": "NOT_ESTIMABLE",
        "white_reality_check_status": "NOT_ESTIMABLE",
        "not_estimable_reasons": [
            "PBO_NOT_ESTIMABLE_FOLD_OUTCOMES_MISSING",
            "DSR_NOT_ESTIMABLE_RETURN_DISTRIBUTION_MISSING",
            "WHITE_REALITY_CHECK_NOT_ESTIMABLE_BOOTSTRAP_SERIES_MISSING",
        ],
    }


def test_multiplicity_account_accepts_not_estimable_statistical_inputs() -> None:
    account = TrialMultiplicityAccount.model_validate(valid_account_payload())

    assert account.success_only_reporting is False
    assert account.sealed_test_used_for_selection is False
    assert account.fdr_status == "AVAILABLE"
    assert account.pbo_status == "NOT_ESTIMABLE"
    assert account.dsr_status == "NOT_ESTIMABLE"
    assert account.white_reality_check_status == "NOT_ESTIMABLE"


def test_multiplicity_account_rejects_success_only_reporting() -> None:
    payload = valid_account_payload()
    payload["success_only_reporting"] = True

    with pytest.raises(ValidationError, match="success_only_reporting"):
        TrialMultiplicityAccount.model_validate(payload)


def test_multiplicity_account_rejects_sealed_test_selection() -> None:
    payload = valid_account_payload()
    payload["sealed_test_used_for_selection"] = True

    with pytest.raises(ValidationError, match="sealed_test_used_for_selection"):
        TrialMultiplicityAccount.model_validate(payload)


def test_multiplicity_account_requires_raw_p_values_for_fdr_available() -> None:
    payload = valid_account_payload()
    payload["raw_p_value_count"] = 0

    with pytest.raises(ValidationError, match="raw_p_value_count"):
        TrialMultiplicityAccount.model_validate(payload)

    payload["fdr_status"] = "NOT_ESTIMABLE"
    payload["not_estimable_reasons"].append("RAW_P_VALUE_MISSING_FOR_BH_FDR")
    account = TrialMultiplicityAccount.model_validate(payload)
    assert account.fdr_status == "NOT_ESTIMABLE"


def test_multiplicity_account_requires_not_estimable_reasons() -> None:
    payload = valid_account_payload()
    payload["not_estimable_reasons"] = []

    with pytest.raises(ValidationError, match="not_estimable_reasons"):
        TrialMultiplicityAccount.model_validate(payload)


def test_multiplicity_account_allows_unavailable_effective_counts_with_reasons() -> None:
    payload = valid_account_payload()
    payload["effective_trial_count"] = None
    payload["correlation_cluster_count"] = None
    payload["not_estimable_reasons"].extend(
        [
            "EFFECTIVE_TRIAL_COUNT_NOT_ESTIMABLE",
            "CORRELATION_CLUSTER_COUNT_NOT_ESTIMABLE",
        ]
    )

    account = TrialMultiplicityAccount.model_validate(payload)

    assert account.effective_trial_count is None
    assert account.correlation_cluster_count is None


def test_multiplicity_account_schema_validates_payload() -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas/trial_multiplicity_account.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(valid_account_payload())
