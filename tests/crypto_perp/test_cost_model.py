from __future__ import annotations

from pathlib import Path

from sis.crypto_perp.cost_model import (
    CRYPTO_PERP_CONSERVATIVE_COST_MODEL_ID,
    CRYPTO_PERP_CONSERVATIVE_TAKER_FEE_RATE,
    CRYPTO_PERP_PROJECT_COST_MODEL_ID,
    CRYPTO_PERP_PROJECT_FUNDING_RATE,
    CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
    CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
    CRYPTO_PERP_STRESS_SLIPPAGE_MULTIPLIER,
)
from sis.crypto_perp.io import read_mapping_file


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_crypto_perp_bitget_cost_model_config_matches_code_constants() -> None:
    payload = read_mapping_file(
        REPO_ROOT / "configs/cost_models/crypto_perp_bitget_usdt_futures.yaml"
    )

    project = payload["project_assumption"]
    assert project["cost_model_id"] == CRYPTO_PERP_PROJECT_COST_MODEL_ID
    assert project["taker_fee_rate"] == str(CRYPTO_PERP_PROJECT_TAKER_FEE_RATE)
    assert project["funding_rate_assumption"] == str(CRYPTO_PERP_PROJECT_FUNDING_RATE)
    assert project["default_slippage_bps"] == str(CRYPTO_PERP_PROJECT_SLIPPAGE_BPS)
    assert project["stress_slippage_multiplier"] == str(CRYPTO_PERP_STRESS_SLIPPAGE_MULTIPLIER)
    assert set(project["wired_surfaces"]) >= {
        "crypto-perp-backtest-candidate-pack",
        "crypto-perp-tournament-rows-v2",
        "build_crypto_perp_backtest_candidate_pack",
        "build_cost_aware_tournament_rows",
        "build_pre_actual_cash_evidence_pack",
        "write_pre_actual_cash_evidence_pack",
    }

    conservative = payload["stress_or_conservative_assumption"]
    assert conservative["cost_model_id"] == CRYPTO_PERP_CONSERVATIVE_COST_MODEL_ID
    assert conservative["taker_fee_rate"] == str(CRYPTO_PERP_CONSERVATIVE_TAKER_FEE_RATE)
    assert (
        conservative["interpretation"]
        == "explicit_conservative_or_stress_assumption_not_normal_default"
    )
    assert conservative["use_only_when_named"] is True
    assert conservative["actual_cash_used"] is False
    assert conservative["measured_exchange_cost"] is False

    zero_cost = payload["zero_cost_policy"]
    assert zero_cost == {
        "fee_rate_must_be_positive": True,
        "slippage_bps_must_be_positive": True,
        "zero_cost_simulation_allowed": False,
    }
