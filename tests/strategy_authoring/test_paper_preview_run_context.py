from __future__ import annotations

import polars as pl

from sis.research.strategy_lab.authoring.compiler.paper_preview_run_context import (
    _paper_preview_run_context,
)
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest

from .helpers import load_authoring_spec, template_yaml


def _spec(tmp_path):
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(template_yaml(), encoding="utf-8")
    return load_authoring_spec(spec_path)


def test_paper_preview_run_context_uses_parameter_hash_for_empty_frame(tmp_path) -> None:
    spec = _spec(tmp_path)
    summary = {
        "backtest_passed": True,
        "strategy_scorecard": {"schema_version": "strategy_authoring_scorecard.v1"},
    }

    context = _paper_preview_run_context(spec=spec, frame=pl.DataFrame(), summary=summary)

    expected_hash = _stable_digest(spec.model_dump(mode="json"))
    assert context.parameter_hash == expected_hash
    assert context.run_id == expected_hash
    assert context.trial_id == f"trial-{expected_hash}"
    assert context.trial_group_id == f"trial-group-{expected_hash}"
    assert context.selected_rows == []
    assert context.selected_signal_ids == []
    assert context.selected is False
    assert context.scorecard_summary == {"schema_version": "strategy_authoring_scorecard.v1"}


def test_paper_preview_run_context_selects_first_unblocked_signal_only_when_backtest_passed(
    tmp_path,
) -> None:
    spec = _spec(tmp_path)
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

    selected_context = _paper_preview_run_context(
        spec=spec,
        frame=frame,
        summary={"backtest_passed": True, "strategy_scorecard": {}},
    )
    failed_context = _paper_preview_run_context(
        spec=spec,
        frame=frame,
        summary={"backtest_passed": False, "strategy_scorecard": {}},
    )

    assert selected_context.selected_signal_ids == ["sig-first"]
    assert selected_context.selected is True
    assert failed_context.selected_signal_ids == ["sig-first"]
    assert failed_context.selected is False
