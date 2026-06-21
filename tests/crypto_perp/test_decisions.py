from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator
import pytest

from sis.crypto_perp.decisions import build_decision
from sis.crypto_perp.models import CryptoPerpAction


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_decision_is_immutable_pre_outcome_and_direction_neutral() -> None:
    decisions = [
        build_decision(
            event_id="event-1",
            action=action,
            actor_type="system",
            actor_id="mvp-b",
            decision_at="2026-06-21T05:01:00Z",
            information_cutoff_at="2026-06-21T05:00:00Z",
            size_cap_usd=Decimal("25"),
            reason_codes=["manual_review_required"],
            notes="prospective decision only",
            review_seconds=42,
            source_event_path="data/events/event-1.json",
            source_event_sha256="a" * 64,
        )
        for action in CryptoPerpAction
    ]

    assert {item.action for item in decisions} == set(CryptoPerpAction)
    payload = decisions[0].model_dump(mode="json")
    assert payload["action"] == "REVERSAL_SHORT"
    assert payload["size_cap_usd"] == "25"
    assert payload["information_cutoff_at"] == "2026-06-21T05:00:00Z"
    assert "outcome" not in payload
    assert "pnl" not in payload
    assert "matured" not in payload
    assert "entry_bid_vwap" not in payload
    assert "exit_ask_vwap" not in payload

    with pytest.raises(Exception, match="frozen|read-only"):
        decisions[0].action = CryptoPerpAction.NO_TRADE


def test_decision_rejects_decision_before_information_cutoff() -> None:
    with pytest.raises(ValueError, match="decision_at must be after or equal"):
        build_decision(
            event_id="event-1",
            action=CryptoPerpAction.UNKNOWN,
            actor_type="system",
            actor_id="mvp-b",
            decision_at="2026-06-21T04:59:59Z",
            information_cutoff_at="2026-06-21T05:00:00Z",
            size_cap_usd=Decimal("0"),
            reason_codes=[],
            notes="",
            review_seconds=0,
            source_event_path="data/events/event-1.json",
            source_event_sha256="a" * 64,
        )


def test_decision_dump_matches_schema() -> None:
    decision = build_decision(
        event_id="event-1",
        action=CryptoPerpAction.CONTINUATION_LONG,
        actor_type="human",
        actor_id="operator-1",
        decision_at="2026-06-21T05:01:00Z",
        information_cutoff_at="2026-06-21T05:00:00Z",
        size_cap_usd=Decimal("12.50"),
        reason_codes=["spread_ok", "funding_checked"],
        notes="manual prospective decision",
        review_seconds=180,
        source_event_path="data/events/event-1.json",
        source_event_sha256="b" * 64,
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_decision.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision.model_dump(mode="json"))
