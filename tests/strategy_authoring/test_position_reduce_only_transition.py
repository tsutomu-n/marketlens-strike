from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.position_reduce_only_transition import (
    _apply_reduce_only_entry_transition,
)
from sis.research.strategy_lab.authoring.io import template_yaml

from .helpers import _write_data, load_authoring_spec


def _spec(tmp_path):
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-reduce-only-transition.yaml"
    _write_data(data_dir)
    spec_path.write_text(template_yaml(), encoding="utf-8")
    return load_authoring_spec(spec_path)


def _row(side: str, **updates):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = {
        "side": side,
        "ts_signal": start,
        "execution_symbol": "XYZ100",
        "signal_id": f"sig-{side}",
        "reason_codes": ["entry"],
        "block_reasons": [],
        "confidence": 0.8,
        "position_weight": 0.4,
        "notional_usd": 4000.0,
        "reduce_fraction": 0.5,
    }
    row.update(updates)
    return row


def test_reduce_only_entry_transition_reduces_opposing_open_side(tmp_path) -> None:
    spec = _spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [
        (start + timedelta(hours=1), "long", 0.25),
        (start + timedelta(hours=2), "short", 0.6),
    ]

    selected, updated_active = _apply_reduce_only_entry_transition(
        row=_row("long"),
        spec=spec,
        active=active,
        side="long",
    )

    assert selected["side"] == "reduce"
    assert selected["signal_id"] != "sig-long"
    assert selected["position_weight"] == 0.0
    assert selected["notional_usd"] is None
    assert selected["reason_codes"] == ["entry", "reduce_only"]
    assert selected["block_reasons"] == []
    assert updated_active == [
        (start + timedelta(hours=1), "long", 0.25),
        (start + timedelta(hours=2), "short", 0.3),
    ]


def test_reduce_only_entry_transition_blocks_without_opposing_open_side(tmp_path) -> None:
    spec = _spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [(start + timedelta(hours=1), "long", 0.25)]

    selected, updated_active = _apply_reduce_only_entry_transition(
        row=_row("long"),
        spec=spec,
        active=active,
        side="long",
    )

    assert selected["side"] == "none"
    assert selected["block_reasons"] == ["position_reduce_only_without_opposing_open"]
    assert selected["position_weight"] == 0.0
    assert updated_active == active
