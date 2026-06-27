from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.crypto_perp.source_availability import build_source_availability
from .test_event_card import _event


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_source_availability_marks_missing_sources_without_zero_fill() -> None:
    event = _event()

    artifact = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        row_counts={"trades": 0},
    )

    assert artifact.can_compute_trade_sign_imbalance is False
    assert artifact.can_compute_ofi is False
    assert artifact.can_compute_depth is False
    assert artifact.can_compute_actual_cash is False
    assert "TRADES_ROW_COUNT_ZERO" in artifact.known_gaps
    assert "BOOKS_SOURCE_MISSING" in artifact.known_gaps
    assert "ACTUAL_CASH_SOURCE_MISSING" in artifact.known_gaps


def test_source_availability_schema_accepts_artifact() -> None:
    artifact = build_source_availability(
        event=_event(),
        created_at="2026-06-27T10:00:00Z",
        available_sources={"books": True, "trades": True, "cash_ledger": True},
        row_counts={"books": 12, "trades": 20, "cash_ledger": 1},
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_source_availability.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(artifact.model_dump(mode="json"))
    assert artifact.can_compute_depth is True
    assert artifact.can_compute_trade_sign_imbalance is True
    assert artifact.can_compute_actual_cash is True
