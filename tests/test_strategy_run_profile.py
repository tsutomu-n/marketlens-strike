from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.strategy_lab.run_profile import StrategyRunProfile


def test_strategy_lab_run_profile_blocks_live_surfaces() -> None:
    profile = StrategyRunProfile(strategy_lab=True)

    assert profile.exchange_write_allowed is False
    assert profile.wallet_required is False
    assert profile.live_order_submission_allowed is False
    assert profile.forbidden_claims == [
        "profitability_claim",
        "paper_ready_claim",
        "tiny_live_ready_claim",
        "live_ready_claim",
    ]


def test_strategy_lab_run_profile_rejects_exchange_write() -> None:
    with pytest.raises(ValidationError, match="exchange_write_allowed"):
        StrategyRunProfile(strategy_lab=True, exchange_write_allowed=True)
