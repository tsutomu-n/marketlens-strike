from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.edge_candidates.risk_taker_sprint_isolation import (
    PromotionDebtCode,
    build_and_write_risk_taker_sprint_isolation,
    build_risk_taker_sprint_isolation,
)
from sis.strategy_idea_candidates.ledger import search_ledger_rows_from_candidate_set
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact

from strategy_idea_candidates.fixtures import HASH_C, valid_candidate_set_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _write_artifacts(tmp_path: Path) -> dict[str, Path]:
    candidate_set_payload = valid_candidate_set_payload()
    candidate_set_path = tmp_path / "sprint_candidate_set.json"
    write_json_artifact(candidate_set_path, candidate_set_payload)
    candidate_set = StrategyIdeaCandidateSet.model_validate(candidate_set_payload)

    ledger_path = tmp_path / "sprint_search_ledger.jsonl"
    ledger_rows = search_ledger_rows_from_candidate_set(
        candidate_set=candidate_set,
        source_kind="risk_taker_sprint_fixture",
    )
    write_text_artifact(
        ledger_path,
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in ledger_rows)
        + "\n",
    )

    protocol_path = tmp_path / "risk_taker_protocol.json"
    write_json_artifact(protocol_path, _protocol_payload())

    multiplicity_path = tmp_path / "sprint_multiplicity_account.json"
    write_json_artifact(multiplicity_path, _multiplicity_payload())
    return {
        "protocol": protocol_path,
        "candidate_set": candidate_set_path,
        "ledger": ledger_path,
        "multiplicity": multiplicity_path,
    }


def _protocol_payload(*, mode: str = "risk_taker_sprint", benchmark: str = "NO_TRADE") -> dict:
    return {
        "schema_version": "candidate_protocol_manifest.v1",
        "protocol_id": "risk-sprint-001",
        "mode": mode,
        "mode_isolation": mode == "risk_taker_sprint",
        "created_at": "2026-07-01T06:50:00Z",
        "target_market": "equity_index",
        "target_venue_family": "local_research",
        "families": [
            {
                "family_id": "trend_momentum",
                "hypothesis": "Sprint search may discover candidates for later default retest.",
                "generator_type": "light_ga",
            }
        ],
        "parameter_spaces": {"trend_momentum": {"lookback": [10, 20], "threshold_z": [1.0]}},
        "objective": {"primary": "ranking_or_no_trade_filter", "benchmark": benchmark},
        "exclusion_rules": ["no live order", "no direct actual cash from sprint"],
        "sealed_holdout_definition": {
            "window_id": "sprint-holdout-2026-q3",
            "start": "2026-07-01T00:00:00Z",
            "end": "2026-09-30T23:59:59Z",
            "peek_policy": "sprint-only; not reusable for default promotion",
        },
        "family_event_count_policy": {
            "trend_momentum": {
                "min_event_count_default": 30,
                "insufficient_data_state": "RESEARCH_ONLY",
            }
        },
        "source_requirements": [
            {"source_id": "ndx_ohlcv_daily", "schema_version": "market_ohlcv.v1", "required": True}
        ],
        "venue_execution_constraints": {"max_leverage": 1},
        "llm_policy": {"role": "adversarial_finding_only", "approval_allowed": False},
        "permits_actual_cash": False,
        "permits_live_order": False,
    }


def _multiplicity_payload(*, mode: str = "risk_taker_sprint") -> dict:
    return {
        "schema_version": "trial_multiplicity_account.v1",
        "account_id": "risk-sprint-001-trial-multiplicity",
        "mode": mode,
        "candidate_count_total": 2,
        "candidate_count_shortlisted": 1,
        "family_count": 1,
        "family_trial_count": {"trend_momentum": 2},
        "parameter_grid_hashes": {"trend_momentum": HASH_C},
        "effective_trial_count": 2,
        "correlation_cluster_count": 1,
        "validation_peek_count": 0,
        "rerank_count": 0,
        "sealed_test_used_for_selection": False,
        "success_only_reporting": False,
        "raw_p_value_count": 1,
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


def test_risk_taker_sprint_isolation_records_promotion_debt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)

    result = build_and_write_risk_taker_sprint_isolation(
        protocol_path=paths["protocol"],
        candidate_set_path=paths["candidate_set"],
        search_ledger_path=paths["ledger"],
        multiplicity_account_path=paths["multiplicity"],
        out_dir=tmp_path / "isolation",
    )

    isolation = result.isolation
    debt_codes = {debt.debt_code for debt in isolation.promotion_debt}

    assert isolation.schema_version == "profit_core_risk_taker_sprint_isolation.v1"
    assert isolation.mode == "risk_taker_sprint"
    assert isolation.output_label == "SPECULATIVE_SPRINT"
    assert isolation.default_aggregate_inclusion_allowed is False
    assert isolation.default_aggregate_candidate_count == 0
    assert isolation.actual_cash_direct_promotion_allowed is False
    assert isolation.tiny_live_direct_promotion_allowed is False
    assert isolation.separate_ledger is True
    assert isolation.separate_holdout is True
    assert isolation.separate_multiplicity_account is True
    assert PromotionDebtCode.RE_REGISTER_UNDER_VERIFICATION_THROUGHPUT in debt_codes
    assert PromotionDebtCode.DO_NOT_REUSE_SPRINT_HOLDOUT in debt_codes
    assert isolation.generator_constraints["light_ga"] == "ranking_or_no_trade_filter_only"
    assert isolation.boundary["default_aggregate_mixed"] is False
    assert isolation.boundary["permits_actual_cash"] is False
    assert result.isolation_path.exists()


def test_risk_taker_sprint_isolation_schema_validates_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    result = build_and_write_risk_taker_sprint_isolation(
        protocol_path=paths["protocol"],
        candidate_set_path=paths["candidate_set"],
        search_ledger_path=paths["ledger"],
        multiplicity_account_path=paths["multiplicity"],
        out_dir=tmp_path / "isolation",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_risk_taker_sprint_isolation.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.isolation.model_dump(mode="json"))


def test_risk_taker_sprint_isolation_rejects_default_protocol(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    write_json_artifact(paths["protocol"], _protocol_payload(mode="verification_throughput"))

    with pytest.raises(ValueError, match="risk_taker_sprint protocol"):
        build_risk_taker_sprint_isolation(
            protocol_path=paths["protocol"],
            candidate_set_path=paths["candidate_set"],
            search_ledger_path=paths["ledger"],
            multiplicity_account_path=paths["multiplicity"],
        )


def test_risk_taker_sprint_isolation_rejects_multiplicity_mode_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    write_json_artifact(
        paths["multiplicity"], _multiplicity_payload(mode="verification_throughput")
    )

    with pytest.raises(ValueError, match="multiplicity account must be risk_taker_sprint"):
        build_risk_taker_sprint_isolation(
            protocol_path=paths["protocol"],
            candidate_set_path=paths["candidate_set"],
            search_ledger_path=paths["ledger"],
            multiplicity_account_path=paths["multiplicity"],
        )


def test_risk_taker_sprint_isolation_rejects_ledger_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    write_text_artifact(
        paths["ledger"],
        json.dumps(
            {
                "trial_id": "trial-001",
                "candidate_id": "idea-cand-001",
                "source_kind": "risk_taker_sprint_fixture",
            },
            sort_keys=True,
        )
        + "\n",
    )

    with pytest.raises(ValueError, match="search ledger candidate ids"):
        build_risk_taker_sprint_isolation(
            protocol_path=paths["protocol"],
            candidate_set_path=paths["candidate_set"],
            search_ledger_path=paths["ledger"],
            multiplicity_account_path=paths["multiplicity"],
        )


def test_risk_taker_sprint_isolation_requires_no_trade_benchmark_for_light_ga(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    write_json_artifact(paths["protocol"], _protocol_payload(benchmark="SPY"))

    with pytest.raises(ValueError, match="NO_TRADE"):
        build_risk_taker_sprint_isolation(
            protocol_path=paths["protocol"],
            candidate_set_path=paths["candidate_set"],
            search_ledger_path=paths["ledger"],
            multiplicity_account_path=paths["multiplicity"],
        )


def test_risk_taker_sprint_isolation_cli_writes_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_artifacts(tmp_path)
    out_dir = tmp_path / "isolation_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-risk-taker-sprint-isolation-record",
            "--protocol",
            str(paths["protocol"]),
            "--candidate-set",
            str(paths["candidate_set"]),
            "--search-ledger",
            str(paths["ledger"]),
            "--multiplicity-account",
            str(paths["multiplicity"]),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "mode=risk_taker_sprint" in result.stdout
    assert "output_label=SPECULATIVE_SPRINT" in result.stdout
    assert "default_aggregate_inclusion_allowed=false" in result.stdout
    assert "actual_cash_direct_promotion_allowed=false" in result.stdout
    assert "promotion_debt_count=6" in result.stdout
    assert (out_dir / "profit_core_risk_taker_sprint_isolation.json").exists()
