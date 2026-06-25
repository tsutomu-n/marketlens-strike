from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sis.research.strategy_lab.authoring.compiler.position_row_state import (
    _apply_position_row_state,
)
from sis.research.strategy_lab.authoring.io import template_yaml

from .helpers import _write_data, load_authoring_spec


def _spec(tmp_path, *, position_yaml: str = ""):
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-row-state.yaml"
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
    ts_signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = {
        "side": side,
        "ts_signal": ts_signal,
        "execution_symbol": "XYZ100",
        "signal_id": f"sig-{side}",
        "reason_codes": ["entry"],
        "block_reasons": [],
        "confidence": 0.8,
        "position_weight": 0.4,
        "notional_usd": 4000.0,
    }
    row.update(updates)
    return row


def test_position_row_state_marker_close_clears_active_positions(tmp_path) -> None:
    ts_signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [(ts_signal + timedelta(hours=1), "long", 0.6)]

    result = _apply_position_row_state(
        row=_row("close", ts_signal=ts_signal),
        spec=_spec(tmp_path),
        active=active,
        open_weight=0.6,
        ts_signal=ts_signal,
        horizon_minutes=240,
    )

    assert result.selected_row["side"] == "close"
    assert result.active == []


def test_position_row_state_reduce_only_reduces_opposing_open_side(tmp_path) -> None:
    ts_signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [
        (ts_signal + timedelta(hours=1), "long", 0.25),
        (ts_signal + timedelta(hours=2), "short", 0.6),
    ]

    result = _apply_position_row_state(
        row=_row("long", entry_reduce_only=True, reduce_fraction=0.5),
        spec=_spec(tmp_path),
        active=active,
        open_weight=0.85,
        ts_signal=ts_signal,
        horizon_minutes=240,
    )

    assert result.selected_row["side"] == "reduce"
    assert result.selected_row["signal_id"] != "sig-long"
    assert result.selected_row["reason_codes"] == ["entry", "reduce_only"]
    assert result.active == [
        (ts_signal + timedelta(hours=1), "long", 0.25),
        (ts_signal + timedelta(hours=2), "short", 0.3),
    ]


def test_position_row_state_blocks_entry_without_updating_active(tmp_path) -> None:
    ts_signal = datetime(2026, 1, 1, tzinfo=timezone.utc)
    active = [(ts_signal + timedelta(hours=1), "long", 0.4)]

    result = _apply_position_row_state(
        row=_row("long"),
        spec=_spec(tmp_path, position_yaml="\n  position:\n    max_open_signals_per_symbol: 1"),
        active=active,
        open_weight=0.4,
        ts_signal=ts_signal,
        horizon_minutes=240,
    )

    assert result.selected_row["side"] == "none"
    assert result.selected_row["block_reasons"] == ["position_open_signal_limit"]
    assert result.active == active


def test_position_row_state_accepts_entry_and_appends_horizon_state(tmp_path) -> None:
    ts_signal = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = _apply_position_row_state(
        row=_row("short", position_weight=0.3),
        spec=_spec(tmp_path, position_yaml="\n  position:\n    allow_pyramiding: true"),
        active=[],
        open_weight=0.0,
        ts_signal=ts_signal,
        horizon_minutes=90,
    )

    assert result.selected_row["side"] == "short"
    assert result.active == [(ts_signal + timedelta(minutes=90), "short", 0.3)]
