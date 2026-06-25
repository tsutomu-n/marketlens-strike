from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_trial import (
    _paper_preview_trial_record,
)

from .helpers import _write_data, _write_spec, load_authoring_spec


def test_paper_preview_trial_record_marks_selected_candidate(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)

    record = _paper_preview_trial_record(
        spec=spec,
        summary={"backtest_passed": True, "total_return": 0.12},
        parameter_hash="param-hash",
        trial_id="trial-run-1",
        trial_group_id="trial-group-run-1",
        signal_count=3,
        selected_signal_ids=["sig-1"],
        selected=True,
    )

    assert record.trial_id == "trial-run-1"
    assert record.trial_group_id == "trial-group-run-1"
    assert record.strategy_id == spec.experiment.strategy_id
    assert record.signal_count == 3
    assert record.candidate_count == 3
    assert record.paper_candidate_count == 1
    assert record.blocked_count == 0
    assert record.no_signal_count == 0
    assert record.blocked_reason_counts == {}
    assert record.metrics["selected_signal_ids"] == ["sig-1"]
    assert record.selected_for_next_stage is True
    assert record.rejection_reasons == []
    assert record.profitability_claimed is False
    assert record.paper_ready_claimed is False
    assert record.tiny_live_ready_claimed is False
    assert record.live_ready_claimed is False


def test_paper_preview_trial_record_preserves_failed_candidate_accounting(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)

    record = _paper_preview_trial_record(
        spec=spec,
        summary={"backtest_passed": False, "total_return": -0.01},
        parameter_hash="param-hash",
        trial_id="trial-run-2",
        trial_group_id="trial-group-run-2",
        signal_count=2,
        selected_signal_ids=["sig-2"],
        selected=False,
    )

    assert record.signal_count == 2
    assert record.candidate_count == 2
    assert record.paper_candidate_count == 0
    assert record.blocked_count == 1
    assert record.no_signal_count == 0
    assert record.blocked_reason_counts == {"not_selected": 1}
    assert record.metrics["selected_signal_ids"] == []
    assert record.selected_for_next_stage is False
    assert record.rejection_reasons == ["insufficient_trades_or_no_signal"]


def test_paper_preview_trial_record_preserves_no_signal_accounting(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)

    record = _paper_preview_trial_record(
        spec=spec,
        summary={"backtest_passed": True},
        parameter_hash="param-hash",
        trial_id="trial-run-empty",
        trial_group_id="trial-group-run-empty",
        signal_count=0,
        selected_signal_ids=[],
        selected=False,
    )

    assert record.paper_candidate_count == 0
    assert record.blocked_count == 1
    assert record.no_signal_count == 1
    assert record.metrics["selected_signal_ids"] == []
