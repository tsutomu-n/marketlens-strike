from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

from jsonschema import Draft202012Validator

from sis.crypto_perp.replay import (
    DEFAULT_REPLAY_LATENCY_SECONDS_GRID,
    DEFAULT_REPLAY_NOTIONAL_USD_GRID,
    DepthLevel,
    ReplayOrderRequest,
    build_replay_grid_requests,
    replay_order,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_replay_is_direction_neutral_and_uses_correct_book_side() -> None:
    asks = [DepthLevel(price=Decimal("100"), size=Decimal("0.10"))]
    bids = [DepthLevel(price=Decimal("99"), size=Decimal("0.10"))]

    long_entry = replay_order(
        ReplayOrderRequest(
            event_id="event-1",
            side="buy",
            requested_qty=Decimal("0.05"),
            latency_seconds=5,
        ),
        bids=bids,
        asks=asks,
        replayed_at="2026-06-21T07:00:00Z",
    )
    short_entry = replay_order(
        ReplayOrderRequest(
            event_id="event-1",
            side="sell",
            requested_qty=Decimal("0.05"),
            latency_seconds=5,
        ),
        bids=bids,
        asks=asks,
        replayed_at="2026-06-21T07:00:00Z",
    )

    assert long_entry.fill_status == "FILLED"
    assert long_entry.entry_book_side == "ask"
    assert long_entry.entry_vwap == Decimal("100")
    assert short_entry.fill_status == "FILLED"
    assert short_entry.entry_book_side == "bid"
    assert short_entry.entry_vwap == Decimal("99")


def test_replay_never_extrapolates_depth_when_unfillable() -> None:
    result = replay_order(
        ReplayOrderRequest(
            event_id="event-1",
            side="buy",
            requested_qty=Decimal("0.50"),
            latency_seconds=15,
        ),
        bids=[DepthLevel(price=Decimal("99"), size=Decimal("0.10"))],
        asks=[DepthLevel(price=Decimal("100"), size=Decimal("0.10"))],
        replayed_at="2026-06-21T07:00:00Z",
    )

    assert result.fill_status == "UNFILLABLE"
    assert result.filled_qty == Decimal("0.10")
    assert result.unfilled_qty == Decimal("0.40")
    assert "DEPTH_EXHAUSTED" in result.known_gaps


def test_replay_grid_uses_default_notional_and_latency_grid() -> None:
    requests = build_replay_grid_requests(
        event_id="event-1",
        side="buy",
        reference_price=Decimal("100"),
    )

    assert len(requests) == len(DEFAULT_REPLAY_NOTIONAL_USD_GRID) * len(
        DEFAULT_REPLAY_LATENCY_SECONDS_GRID
    )
    assert requests[0].requested_notional_usd == Decimal("5")
    assert requests[0].requested_qty == Decimal("0.05")
    assert requests[0].latency_seconds == 5
    assert requests[-1].requested_notional_usd == Decimal("250")
    assert requests[-1].requested_qty == Decimal("2.5")
    assert requests[-1].latency_seconds == 60


def test_replay_dump_matches_schema() -> None:
    result = replay_order(
        ReplayOrderRequest(
            event_id="event-1",
            side="buy",
            requested_qty=Decimal("0.05"),
            latency_seconds=5,
        ),
        bids=[DepthLevel(price=Decimal("99"), size=Decimal("0.10"))],
        asks=[DepthLevel(price=Decimal("100"), size=Decimal("0.10"))],
        replayed_at="2026-06-21T07:00:00Z",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_execution_replay.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.model_dump(mode="json"))
