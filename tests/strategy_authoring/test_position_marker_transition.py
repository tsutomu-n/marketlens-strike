from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.position_marker_transition import (
    _apply_position_marker_transition,
)
from sis.research.strategy_lab.authoring.io import template_yaml

from .helpers import _write_data, load_authoring_spec


def _spec(tmp_path, *, position_yaml: str = ""):
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-marker-transition.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3" + position_yaml,
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


def _row(side: str, **updates):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = {
        "side": side,
        "ts_signal": start,
        "execution_symbol": "XYZ100",
        "signal_id": f"sig-{side}",
        "reason_codes": [f"{side}_reason"],
        "block_reasons": [],
        "confidence": 0.8,
        "position_weight": 0.0,
        "notional_usd": None,
    }
    row.update(updates)
    return row


def test_position_marker_transition_close_clears_active_positions(tmp_path) -> None:
    spec = _spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [(start + timedelta(hours=1), "long", 1.0)]
    row = _row("close")

    selected, updated_active = _apply_position_marker_transition(
        row=row,
        spec=spec,
        active=active,
        open_weight=1.0,
    )

    assert selected is row
    assert updated_active == []


def test_position_marker_transition_reduce_add_and_rebalance_update_active_weight(
    tmp_path,
) -> None:
    spec = _spec(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [
        (start + timedelta(hours=1), "long", 0.4),
        (start + timedelta(hours=2), "long", 0.6),
    ]

    _selected, reduced = _apply_position_marker_transition(
        row=_row("reduce", reduce_fraction=0.5),
        spec=spec,
        active=active,
        open_weight=1.0,
    )
    assert reduced == [(start + timedelta(hours=2), "long", 0.5)]

    _selected, added = _apply_position_marker_transition(
        row=_row("add", add_fraction=0.25),
        spec=spec,
        active=active,
        open_weight=1.0,
    )
    assert added == [(start + timedelta(hours=2), "long", 1.25)]

    _selected, rebalanced = _apply_position_marker_transition(
        row=_row("rebalance", rebalance_target_fraction=0.3),
        spec=spec,
        active=active,
        open_weight=1.0,
    )
    assert rebalanced == [(start + timedelta(hours=2), "long", 0.3)]


def test_position_marker_transition_blocks_marker_without_open_position(tmp_path) -> None:
    spec = _spec(
        tmp_path,
        position_yaml="\n  position:\n    require_open_position_for_markers: true",
    )

    selected, updated_active = _apply_position_marker_transition(
        row=_row("reduce"),
        spec=spec,
        active=[],
        open_weight=0.0,
    )

    assert selected["side"] == "none"
    assert selected["block_reasons"] == ["position_marker_without_open"]
    assert selected["position_weight"] == 0.0
    assert updated_active == []


def test_position_marker_transition_blocks_add_over_open_weight_limit(tmp_path) -> None:
    spec = _spec(
        tmp_path,
        position_yaml="\n  position:\n    max_open_position_weight_per_symbol: 1.0",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [(start + timedelta(hours=1), "long", 0.8)]

    selected, updated_active = _apply_position_marker_transition(
        row=_row("add", add_fraction=0.3),
        spec=spec,
        active=active,
        open_weight=0.8,
    )

    assert selected["side"] == "none"
    assert selected["block_reasons"] == ["position_open_weight_limit"]
    assert updated_active == active
