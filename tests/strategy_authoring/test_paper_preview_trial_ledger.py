from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_trial import (
    _paper_preview_trial_record,
)
from sis.research.strategy_lab.authoring.compiler.paper_preview_trial_ledger import (
    _append_paper_preview_trial_record_once,
)
from sis.research.strategy_lab.trial_ledger import TrialLedger

from .helpers import _write_spec, load_authoring_spec


def _record(tmp_path, *, trial_id: str = "trial-run-1"):
    spec_path = tmp_path / "spec.yaml"
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    return _paper_preview_trial_record(
        spec=spec,
        summary={"backtest_passed": True, "total_return": 0.12},
        parameter_hash="param-hash",
        trial_id=trial_id,
        trial_group_id=f"group-{trial_id}",
        signal_count=1,
        selected_signal_ids=["sig-1"],
        selected=True,
    )


def test_append_paper_preview_trial_record_once_creates_expected_ledger_path(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    record = _record(tmp_path)

    ledger_path = _append_paper_preview_trial_record_once(
        data_dir=data_dir,
        record=record,
    )

    assert ledger_path == data_dir / "research/trial_ledger.jsonl"
    assert TrialLedger(ledger_path).read_all() == [record]


def test_append_paper_preview_trial_record_once_skips_existing_trial_id(tmp_path) -> None:
    data_dir = tmp_path / "data"
    record = _record(tmp_path)

    ledger_path = _append_paper_preview_trial_record_once(
        data_dir=data_dir,
        record=record,
    )
    duplicate_path = _append_paper_preview_trial_record_once(
        data_dir=data_dir,
        record=record,
    )

    assert duplicate_path == ledger_path
    assert [item.trial_id for item in TrialLedger(ledger_path).read_all()] == [record.trial_id]
