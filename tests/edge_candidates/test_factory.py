from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sis.backtest.artifact_io import sha256_file
from sis.cli import app
from sis.edge_candidates.factory import (
    EdgeCandidateFactoryError,
    run_edge_candidate_factory,
)
from sis.strategy_inputs.io import write_json_artifact


runner = CliRunner()


def _perp_params(**overrides) -> dict:
    params = {
        "side_bias": "long",
        "venue": "bitget",
        "product_type": "USDT-FUTURES",
        "margin_mode": "isolated",
        "margin_coin": "USDT",
        "leverage": 3,
        "funding_assumption": "funding paid or received during hold is modeled",
        "fee_model_ref": "bitget_usdt_futures_taker_fee_estimate",
        "slippage_model_ref": "bps_stress_model",
        "liquidation_buffer_bps": 2500,
        "max_position_notional_usd": 100,
        "max_daily_loss_usd": 25,
        "kill_conditions": ["spread_bps_gt_15", "funding_missing", "source_gap"],
        "lookback": 12,
        "breakout_z": 1.0,
    }
    params.update(overrides)
    return params


def _protocol_payload(
    *,
    mode: str = "verification_throughput",
    generator_type: str = "classical_rule",
) -> dict:
    return {
        "schema_version": "candidate_protocol_manifest.v1",
        "protocol_id": "btc-perp-verification-001",
        "mode": mode,
        "mode_isolation": mode == "risk_taker_sprint",
        "created_at": "2026-06-30T11:36:00Z",
        "target_market": "crypto_perp",
        "target_venue_family": "bitget_usdt_futures",
        "families": [
            {
                "family_id": "perp_momentum_continuation",
                "hypothesis": "Perp momentum may continue after a volatility-confirmed move.",
                "generator_type": generator_type,
            }
        ],
        "parameter_spaces": {
            "perp_momentum_continuation": {
                "grid": [
                    _perp_params(),
                    _perp_params(fee_model_ref=""),
                ]
            }
        },
        "objective": {
            "primary": "after_cost_edge_over_no_trade",
            "benchmark": "NO_TRADE",
        },
        "exclusion_rules": ["no arbitrary Python eval", "no live order"],
        "sealed_holdout_definition": {
            "window_id": "holdout-2026-q3",
            "start": "2026-07-01T00:00:00Z",
            "end": "2026-09-30T23:59:59Z",
            "peek_policy": "winner-only once",
        },
        "family_event_count_policy": {
            "perp_momentum_continuation": {
                "min_event_count_default": 100,
                "insufficient_data_state": "INCONCLUSIVE_DATA",
            }
        },
        "source_requirements": [
            {
                "source_id": "btc_usdt_perp_features",
                "schema_version": "crypto_perp_feature_pack.v1",
                "required": True,
            }
        ],
        "venue_execution_constraints": {
            "max_leverage": 3,
            "margin_mode": "isolated",
            "reduce_only_close_required": True,
        },
        "llm_policy": {
            "role": "adversarial_finding_only",
            "approval_allowed": False,
        },
        "permits_actual_cash": False,
        "permits_live_order": False,
    }


def _perp_input_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "data/research/crypto_perp/source/BTCUSDT_15m.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,mark,index,spread_bps\n2026-06-17T21:00:00Z,100,99,2\n", encoding="utf-8")
    source_hash = sha256_file(source)

    contract_payload = _input_contract_payload(source_hash)
    validation_payload = _input_validation_payload(source_hash)

    protocol_path = tmp_path / "data/edge_candidates/protocol.json"
    contract_path = tmp_path / "data/strategy_inputs/btc_perp/strategy_input_contract.json"
    validation_path = (
        tmp_path / "data/strategy_inputs/btc_perp/strategy_input_contract_validation.json"
    )
    write_json_artifact(protocol_path, _protocol_payload())
    write_json_artifact(contract_path, contract_payload)
    write_json_artifact(validation_path, validation_payload)
    return protocol_path, contract_path, validation_path


def _input_contract_payload(source_hash: str) -> dict:
    return {
        "schema_version": "strategy_input_contract.v1",
        "contract_id": "btc-perp-inputs-001",
        "created_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "manual"},
        "strategy_scope": {
            "strategy_family": "crypto_perp_hypothesis",
            "instruments": ["BTCUSDT"],
            "timeframe": "15m",
            "intended_use": "research_backtest_only",
        },
        "sources": [
            {
                "source_id": "btc_usdt_perp_features",
                "source_type": "raw_market_data",
                "path": "data/research/crypto_perp/source/BTCUSDT_15m.csv",
                "required": True,
                "declared_sha256": source_hash,
                "schema_version": "crypto_perp_feature_pack.v1",
                "generated_at": "2026-06-18T00:00:00Z",
                "available_at": "2026-06-18T00:05:00Z",
                "revision_policy": "append_only",
                "survivorship_policy": "not_applicable",
                "execution_reality": {
                    "includes_fills": False,
                    "includes_slippage": False,
                    "includes_latency": False,
                    "assumed_order_type": "paper_only_intent",
                },
            }
        ],
        "known_gaps": ["fixture_source_only"],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def _input_validation_payload(source_hash: str) -> dict:
    return {
        "schema_version": "strategy_input_contract_validation.v1",
        "contract_id": "btc-perp-inputs-001",
        "validated_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "strategy-input-contract-validate"},
        "validation_status": "PASS",
        "strict": False,
        "source_results": [
            {
                "source_id": "btc_usdt_perp_features",
                "status": "present",
                "path": "data/research/crypto_perp/source/BTCUSDT_15m.csv",
                "actual_sha256": source_hash,
                "declared_sha256": source_hash,
                "hash_matches": True,
                "available_at_present": True,
                "generated_before_available": True,
                "max_observed_timestamp": "2026-06-17T21:00:00Z",
            }
        ],
        "summary": {
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "boundary_violation_count": 0,
            "warning_count": 0,
            "column_check_failure_count": 0,
            "timestamp_violation_count": 0,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def test_edge_candidate_factory_writes_protocol_bound_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    protocol_path, contract_path, validation_path = _perp_input_files(tmp_path)

    result = run_edge_candidate_factory(
        protocol_path=protocol_path,
        contract_path=contract_path,
        validation_path=validation_path,
        out_dir=tmp_path / "data/edge_candidates/factory",
        candidate_set_id="btc-perp-p4-factory-test",
        shortlist_count=1,
    )

    candidate_set = json.loads(result.candidate_set_path.read_text(encoding="utf-8"))
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    rejection_rows = [
        json.loads(line)
        for line in result.rejection_ledger_path.read_text(encoding="utf-8").splitlines()
    ]

    assert candidate_set["candidate_set_id"] == "btc-perp-p4-factory-test"
    assert candidate_set["producer"]["command"] == "edge-candidate-factory-run"
    assert set(candidate_set["parameter_grids"]) == {"perp_momentum_continuation"}
    assert len(candidate_set["parameter_grids"]["perp_momentum_continuation"]) == 2
    assert candidate_set["search_ledger_summary"]["candidate_count_total"] == 2
    assert candidate_set["search_ledger_summary"]["candidate_count_shortlisted"] == 1
    assert candidate_set["search_ledger_summary"]["candidate_count_rejected"] == 1

    assert len(rejection_rows) == 1
    assert rejection_rows[0]["family"] == "perp_momentum_continuation"
    assert rejection_rows[0]["rejection_reason"].startswith("missing perp risk modeling fields")
    assert rejection_rows[0]["unexecutable_reasons"]

    assert summary["schema_version"] == "edge_candidate_factory_summary.v1"
    assert summary["protocol_ref"]["protocol_id"] == "btc-perp-verification-001"
    assert summary["candidate_count_total"] == 2
    assert summary["candidate_count_rejected"] == 1
    assert summary["best_only_report"] is False
    assert summary["unexecutable_reason_count"] == 1
    assert summary["unexecutable_rate"] == 0.5
    assert summary["boundary"] == {
        "actual_cash": False,
        "permits_live_order": False,
        "live_order_submitted": False,
        "production_exchange_write_used": False,
    }
    assert result.multiplicity_account_path.exists()


def test_edge_candidate_factory_rejects_risk_taker_sprint(tmp_path: Path) -> None:
    protocol_path, contract_path, validation_path = _perp_input_files(tmp_path)
    write_json_artifact(protocol_path, _protocol_payload(mode="risk_taker_sprint"))

    with pytest.raises(EdgeCandidateFactoryError, match="risk_taker_sprint"):
        run_edge_candidate_factory(
            protocol_path=protocol_path,
            contract_path=contract_path,
            validation_path=validation_path,
            out_dir=tmp_path / "data/edge_candidates/factory",
        )


def test_edge_candidate_factory_rejects_non_p4_generator_type(tmp_path: Path) -> None:
    protocol_path, contract_path, validation_path = _perp_input_files(tmp_path)
    write_json_artifact(protocol_path, _protocol_payload(generator_type="light_ga"))

    with pytest.raises(EdgeCandidateFactoryError, match="unsupported generator_type"):
        run_edge_candidate_factory(
            protocol_path=protocol_path,
            contract_path=contract_path,
            validation_path=validation_path,
            out_dir=tmp_path / "data/edge_candidates/factory",
        )


def test_edge_candidate_factory_cli_writes_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    protocol_path, contract_path, validation_path = _perp_input_files(tmp_path)
    out_dir = tmp_path / "data/edge_candidates/factory"

    result = runner.invoke(
        app,
        [
            "edge-candidate-factory-run",
            "--protocol",
            str(protocol_path),
            "--contract",
            str(contract_path),
            "--validation",
            str(validation_path),
            "--candidate-set-id",
            "btc-perp-p4-factory-cli-test",
            "--shortlist-count",
            "1",
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "candidate_count_total=2" in result.stdout
    assert "unexecutable_reason_count=1" in result.stdout
    assert (out_dir / "strategy_idea_candidate_set.json").exists()
    assert (out_dir / "search_ledger.jsonl").exists()
    assert (out_dir / "rejection_ledger.jsonl").exists()
    assert (out_dir / "trial_multiplicity_account.json").exists()
    assert (out_dir / "edge_candidate_factory_summary.json").exists()
