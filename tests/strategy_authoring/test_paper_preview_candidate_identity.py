from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_candidate_identity import (
    _base_status,
    _candidate_id,
)


def test_paper_preview_candidate_id_uses_signal_id_or_no_signal_placeholder() -> None:
    assert (
        _candidate_id(trial_id="trial-1", row={"signal_id": "sig-1"}) == "candidate-trial-1-sig-1"
    )
    assert _candidate_id(trial_id="trial-1", row={}) == "candidate-trial-1-no-signal"


def test_paper_preview_base_status_uses_selected_flag_and_empty_row() -> None:
    assert _base_status(selected=True, row={"signal_id": "sig-1"}) == "candidate"
    assert _base_status(selected=False, row={"signal_id": "sig-1"}) == "hold"
    assert _base_status(selected=False, row={}) == "no_signal"
