from __future__ import annotations

from pathlib import Path

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.generator import (
    CandidateFamilyId,
    StrategyIdeaCandidateGeneratorConfig,
    StrategyIdeaCandidateProfile,
    build_deterministic_candidate_set_from_input_evidence,
)
from sis.strategy_idea_candidates.policies import validate_perp_shortlist_constraints
from sis.strategy_inputs.io import write_json_artifact
from sis.strategy_inputs.models import StrategyInputContract, StrategyInputContractValidation

from .fixtures import valid_input_contract_payload, valid_input_validation_payload


def _input_evidence(
    tmp_path: Path,
) -> tuple[StrategyInputContract, StrategyInputContractValidation, Path]:
    source = tmp_path / "data/research/crypto_perp/source/BTCUSDT_15m.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("ts,mark,index,spread_bps\n2026-06-17T21:00:00Z,100,99,2\n", encoding="utf-8")
    source_hash = sha256_file(source)

    contract_payload = valid_input_contract_payload(sha256=source_hash)
    contract_payload["contract_id"] = "btc-perp-inputs-001"
    contract_payload["strategy_scope"]["strategy_family"] = "crypto_perp_hypothesis"
    contract_payload["strategy_scope"]["instruments"] = ["BTCUSDT"]
    contract_payload["strategy_scope"]["timeframe"] = "15m"
    contract_payload["sources"][0]["source_id"] = "btc_usdt_perp_features"

    validation_payload = valid_input_validation_payload()
    validation_payload["contract_id"] = "btc-perp-inputs-001"
    validation_payload["source_results"][0]["source_id"] = "btc_usdt_perp_features"
    validation_payload["source_results"][0]["actual_sha256"] = source_hash
    validation_payload["source_results"][0]["declared_sha256"] = source_hash
    validation_path = (
        tmp_path / "data/strategy_inputs/btc_perp/strategy_input_contract_validation.json"
    )
    write_json_artifact(validation_path, validation_payload)

    return (
        StrategyInputContract.model_validate(contract_payload),
        StrategyInputContractValidation.model_validate(validation_payload),
        validation_path,
    )


def _config() -> StrategyIdeaCandidateGeneratorConfig:
    return StrategyIdeaCandidateGeneratorConfig(
        candidate_set_id="btc-perp-risk-taker-001",
        profile=StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER,
        family_ids=[CandidateFamilyId.PERP_MOMENTUM_CONTINUATION],
        candidate_cap=2,
        shortlist_count=1,
        parameter_grids={
            "perp_momentum_continuation": [
                {
                    "side_bias": "long",
                    "lookback": 12,
                    "breakout_z": 1.2,
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
                    "kill_conditions": ["spread_bps_gt_15"],
                },
                {
                    "side_bias": "short",
                    "lookback": 24,
                    "breakout_z": 1.3,
                    "venue": "bitget",
                    "product_type": "USDT-FUTURES",
                    "margin_mode": "isolated",
                    "margin_coin": "USDT",
                    "leverage": 2,
                    "funding_assumption": "funding paid or received during hold is modeled",
                    "fee_model_ref": "bitget_usdt_futures_taker_fee_estimate",
                    "slippage_model_ref": "bps_stress_model",
                    "liquidation_buffer_bps": 3000,
                    "max_position_notional_usd": 100,
                    "max_daily_loss_usd": 25,
                    "kill_conditions": ["spread_bps_gt_15"],
                },
            ]
        },
        label_window={
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-12-31T00:00:00Z",
        },
        feature_observation_window={
            "start": "2024-01-01T00:00:00Z",
            "end": "2025-12-30T00:00:00Z",
        },
        train_window={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T00:00:00Z",
        },
        validation_window={
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-12-31T00:00:00Z",
        },
        sealed_test_window={
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-06-18T00:00:00Z",
        },
        generated_at="2026-06-18T12:49:00Z",
    )


def test_perp_profile_shortlists_only_candidates_with_cost_and_liquidation_fields(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation, validation_path = _input_evidence(tmp_path)

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=_config(),
    )

    candidate = candidate_set.candidate_inventory[0]
    assert candidate.decision.value == "SHORTLISTED"
    assert candidate.parameter_set["product_type"] == "USDT-FUTURES"
    assert candidate.raw_validation_metrics["metric_basis"] == "raw_only_not_profit_proof"
    result = validate_perp_shortlist_constraints(candidate_set)
    assert result.passed is True


def test_perp_profile_rejects_missing_funding_or_liquidation_fields_before_shortlist(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation, validation_path = _input_evidence(tmp_path)
    config = _config()
    broken_grid = dict(config.parameter_grids or {})
    broken_parameter = dict(broken_grid["perp_momentum_continuation"][0])
    broken_parameter.pop("funding_assumption")
    broken_parameter.pop("liquidation_buffer_bps")
    broken_grid["perp_momentum_continuation"] = [broken_parameter]
    config = config.model_copy(update={"parameter_grids": broken_grid})

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    )

    candidate = candidate_set.candidate_inventory[0]
    assert candidate.decision.value == "REJECTED"
    assert candidate.shortlist_reason is None
    assert "perp shortlist constraints failed" in (candidate.rejection_reason or "")
    assert "missing funding_assumption, liquidation_buffer_bps" in (
        candidate.rejection_reason or ""
    )
    result = validate_perp_shortlist_constraints(candidate_set)
    assert result.passed is True


def test_perp_profile_rejects_non_directional_side_bias_before_shortlist(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation, validation_path = _input_evidence(tmp_path)
    config = _config()
    grid = dict(config.parameter_grids or {})
    both_parameter = dict(grid["perp_momentum_continuation"][0])
    both_parameter["side_bias"] = "both"
    short_parameter = dict(grid["perp_momentum_continuation"][1])
    short_parameter["side_bias"] = "short"
    grid["perp_momentum_continuation"] = [both_parameter, short_parameter]
    config = config.model_copy(update={"parameter_grids": grid})

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    )

    rejected = candidate_set.candidate_inventory[0]
    shortlisted = candidate_set.candidate_inventory[1]
    assert rejected.decision.value == "REJECTED"
    assert rejected.shortlist_reason is None
    assert "side_bias must be long or short" in (rejected.rejection_reason or "")
    assert shortlisted.decision.value == "SHORTLISTED"
    assert shortlisted.parameter_set["side_bias"] == "short"


def test_perp_profile_rejects_liquidation_source_families_before_shortlist(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    contract, validation, validation_path = _input_evidence(tmp_path)
    config = _config()
    common = dict((config.parameter_grids or {})["perp_momentum_continuation"][0])
    reversal_short = dict(common)
    reversal_short.update(
        {
            "side_bias": "short",
            "liquidation_move_bps": 250,
            "reversal_wait_bars": 3,
        }
    )
    funding_long = dict(common)
    funding_long.update(
        {
            "side_bias": "long",
            "funding_rate_threshold_bps": -2,
            "holding_bars": 8,
        }
    )
    open_interest_both = dict(common)
    open_interest_both.update(
        {
            "side_bias": "both",
            "oi_change_threshold_pct": 3,
            "liquidation_pressure_bps": 100,
        }
    )
    config = config.model_copy(
        update={
            "family_ids": [
                CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE,
                CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER,
                CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE,
            ],
            "candidate_cap": 3,
            "shortlist_count": 1,
            "parameter_grids": {
                "perp_reversal_after_liquidation_move": [reversal_short],
                "perp_funding_rate_carry_filter": [funding_long],
                "perp_open_interest_liquidation_pressure": [open_interest_both],
            },
        }
    )

    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    )

    reversal = candidate_set.candidate_inventory[0]
    funding = candidate_set.candidate_inventory[1]
    open_interest = candidate_set.candidate_inventory[2]
    assert reversal.decision.value == "REJECTED"
    assert reversal.shortlist_reason is None
    assert "requires liquidation_notional source" in (reversal.rejection_reason or "")
    assert funding.decision.value == "SHORTLISTED"
    assert funding.family == CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER.value
    assert open_interest.decision.value == "REJECTED"
    assert "requires open_interest and liquidation_notional sources" in (
        open_interest.rejection_reason or ""
    )
    assert "side_bias must be long or short" in (open_interest.rejection_reason or "")
