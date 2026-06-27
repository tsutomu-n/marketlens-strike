from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.crypto_perp.edge_scorer import build_edge_score
from sis.crypto_perp.features import build_feature_pack
from sis.crypto_perp.source_availability import build_source_availability
from .test_event_card import _event


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_edge_scorer_selects_no_trade_when_cost_inputs_are_missing() -> None:
    event = _event()
    availability = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        available_sources={"books": False, "trades": False},
    )
    feature_pack = build_feature_pack(
        event=event,
        source_availability=availability,
        created_at="2026-06-27T10:01:00Z",
    )

    edge = build_edge_score(
        feature_pack=feature_pack,
        source_availability=availability,
        created_at="2026-06-27T10:02:00Z",
    )

    assert edge.selected_action in {"NO_TRADE", "UNKNOWN"}
    assert edge.why_no_trade
    assert "EDGE_SCORE_UNKNOWN_COST_ADJUSTED_INPUTS_MISSING" in edge.known_gaps


def test_edge_scorer_schema_accepts_artifact() -> None:
    event = _event()
    availability = build_source_availability(
        event=event,
        created_at="2026-06-27T10:00:00Z",
        available_sources={"books": True, "trades": True},
        row_counts={"books": 10, "trades": 10},
    )
    feature_pack = build_feature_pack(
        event=event,
        source_availability=availability,
        created_at="2026-06-27T10:01:00Z",
    )
    edge = build_edge_score(
        feature_pack=feature_pack,
        source_availability=availability,
        created_at="2026-06-27T10:02:00Z",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_edge_score.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(edge.model_dump(mode="json"))
    assert {row.action for row in edge.action_scores} >= {
        "REVERSAL_SHORT",
        "CONTINUATION_LONG",
        "NO_TRADE",
    }
