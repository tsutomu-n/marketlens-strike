from __future__ import annotations

import pytest

from sis.edge_candidate_factory.models import SmartCandidateCard
from sis.edge_candidate_factory.smart_priors import (
    DEFAULT_SMART_PRIOR_CAUSE_IDS,
    DEFAULT_SMART_PRIOR_FAMILY_IDS,
    build_default_candidate_card,
    default_smart_prior_families,
    smart_prior_family_by_id,
)


EXPECTED_CAUSE_IDS = (
    "FORCED_FLOW",
    "INVENTORY_RISK_TRANSFER",
    "SLOW_INFORMATION",
    "CONSTRAINED_ARBITRAGE",
    "CROWDED_POSITIONING",
    "BEHAVIORAL_ATTENTION",
    "ADVERSE_SELECTION",
    "EXECUTION_FRICTION",
    "DATA_OBSERVABILITY",
)

EXPECTED_FAMILY_IDS = (
    "funding_pressure_reversion",
    "mark_index_basis_reversion",
    "liquidation_exhaustion_reversal",
    "liquidation_cascade_continuation",
    "oi_impulse_continuation",
    "volume_shock_reversal",
    "volatility_compression_breakout",
    "spread_widening_no_trade",
    "funding_window_avoidance",
    "cross_market_basis_dislocation",
)


def test_default_cause_prior_taxonomy_matches_plan() -> None:
    assert DEFAULT_SMART_PRIOR_CAUSE_IDS == EXPECTED_CAUSE_IDS


def test_default_family_ids_match_plan_order() -> None:
    assert DEFAULT_SMART_PRIOR_FAMILY_IDS == EXPECTED_FAMILY_IDS


def test_default_families_are_complete_and_unique() -> None:
    families = default_smart_prior_families()

    assert tuple(family.family_id for family in families) == EXPECTED_FAMILY_IDS
    assert len({family.family_id for family in families}) == len(families)
    for family in families:
        assert family.cause_priors
        assert family.required_sources
        assert family.default_kill_conditions
        assert family.allowed_observables
        assert family.expected_information_gain_template.strip()
        assert set(family.cause_priors).issubset(set(EXPECTED_CAUSE_IDS))


def test_family_lookup_rejects_unknown_family() -> None:
    with pytest.raises(KeyError, match="Unknown smart prior family"):
        smart_prior_family_by_id("unknown_family")


def test_build_default_candidate_card_returns_contract_model() -> None:
    card = build_default_candidate_card(
        "liquidation_exhaustion_reversal",
        candidate_id="edge-cand-liq-001",
        venue_id="bitget",
        product_type="USDT-FUTURES",
        symbol="BTCUSDT",
    )

    assert isinstance(card, SmartCandidateCard)
    assert card.candidate_status == "UNVERIFIED_CANDIDATE"
    assert card.proof_status == "not_alpha_or_profit_proof"
    assert card.family == "liquidation_exhaustion_reversal"
    assert card.execution_precheck.venue_id == "bitget"
    assert card.execution_precheck.product_type == "USDT-FUTURES"
    assert card.execution_precheck.symbol == "BTCUSDT"
    assert card.boundary.permits_live_order is False
    assert card.boundary.exchange_write_used is False


def test_every_family_can_build_a_default_candidate_card() -> None:
    for family_id in DEFAULT_SMART_PRIOR_FAMILY_IDS:
        card = build_default_candidate_card(
            family_id,
            candidate_id=f"edge-cand-{family_id}",
            venue_id="bitget",
            product_type="USDT-FUTURES",
            symbol="BTCUSDT",
        )
        assert card.family == family_id
        assert card.cause_priors
        assert card.required_sources
        assert card.kill_conditions


def test_volatility_compression_breakout_is_regime_state_not_structural_cause() -> None:
    family = smart_prior_family_by_id("volatility_compression_breakout")
    card = build_default_candidate_card(
        family.family_id,
        candidate_id="edge-cand-vol-compression",
        venue_id="bitget",
        product_type="USDT-FUTURES",
        symbol="BTCUSDT",
    )

    assert family.structural_cause_role == "regime_state"
    assert "volatility_compression" in family.allowed_observables
    assert "volatility_compression" in [observable.value for observable in card.observables]
    assert "VOLATILITY_COMPRESSION" not in family.cause_priors


def test_spread_widening_family_is_no_trade_filter() -> None:
    family = smart_prior_family_by_id("spread_widening_no_trade")
    card = build_default_candidate_card(
        family.family_id,
        candidate_id="edge-cand-spread-filter",
        venue_id="bitget",
        product_type="USDT-FUTURES",
        symbol="BTCUSDT",
    )

    assert family.family_role == "filter_no_trade"
    assert family.default_action_set == ("no_trade",)
    assert card.action_set == ["no_trade"]
    assert card.entry_logic == "avoid entries when spread and depth conditions are unfavorable"
