from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.compiler.paper_preview_selected_rows import (
    _paper_preview_selected_rows,
)


def test_paper_preview_selected_rows_keeps_first_sorted_unblocked_long_or_short() -> None:
    frame = pl.DataFrame(
        [
            {
                "ts_signal": "2026-01-01T04:00:00+00:00",
                "signal_id": "sig-late",
                "side": "long",
                "block_reasons": [],
            },
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-neutral",
                "side": "none",
                "block_reasons": [],
            },
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-blocked",
                "side": "short",
                "block_reasons": ["risk_gate"],
            },
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-first",
                "side": "short",
                "block_reasons": [],
            },
        ]
    )

    selected = _paper_preview_selected_rows(frame)

    assert [row["signal_id"] for row in selected] == ["sig-first"]


def test_paper_preview_selected_rows_returns_empty_when_rows_are_not_eligible() -> None:
    frame = pl.DataFrame(
        [
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "signal_id": "sig-neutral",
                "side": "none",
                "block_reasons": [],
            },
            {
                "ts_signal": "2026-01-01T04:00:00+00:00",
                "signal_id": "sig-blocked",
                "side": "long",
                "block_reasons": ["risk_gate"],
            },
        ]
    )

    assert _paper_preview_selected_rows(frame) == []
