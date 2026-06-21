from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st
import pytest

from sis.crypto_perp.decisions import build_decision
from sis.crypto_perp.models import CryptoPerpAction


BASE_TIME = datetime(2026, 6, 21, 5, 0, tzinfo=timezone.utc)


@given(st.integers(min_value=0, max_value=86_400))
def test_decision_time_can_equal_or_follow_information_cutoff(offset_seconds: int) -> None:
    cutoff = BASE_TIME
    decision_at = cutoff + timedelta(seconds=offset_seconds)

    decision = build_decision(
        event_id="event-1",
        action=CryptoPerpAction.NO_TRADE,
        actor_type="system",
        actor_id="property-test",
        decision_at=decision_at,
        information_cutoff_at=cutoff,
        size_cap_usd=Decimal("0"),
        reason_codes=[],
        notes="",
        review_seconds=0,
        source_event_path="data/events/event-1.json",
        source_event_sha256="d" * 64,
    )

    assert decision.decision_at >= decision.information_cutoff_at


@given(st.integers(min_value=1, max_value=86_400))
def test_decision_time_rejects_pre_cutoff_timestamp(offset_seconds: int) -> None:
    cutoff = BASE_TIME
    decision_at = cutoff - timedelta(seconds=offset_seconds)

    with pytest.raises(ValueError, match="decision_at must be after or equal"):
        build_decision(
            event_id="event-1",
            action=CryptoPerpAction.NO_TRADE,
            actor_type="system",
            actor_id="property-test",
            decision_at=decision_at,
            information_cutoff_at=cutoff,
            size_cap_usd=Decimal("0"),
            reason_codes=[],
            notes="",
            review_seconds=0,
            source_event_path="data/events/event-1.json",
            source_event_sha256="d" * 64,
        )
