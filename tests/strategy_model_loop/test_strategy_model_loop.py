from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.strategy_model_loop.models import ModelOutputRoute
from sis.strategy_model_loop.service import StrategyModelLoopError, build_strategy_model_run


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / f"schemas/{name}").read_text(encoding="utf-8"))


def _training_data(tmp_path: Path) -> Path:
    path = tmp_path / "data/features/training.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ts,feature,label\n2026-06-18T00:00:00Z,1.0,0.1\n", encoding="utf-8")
    return path


def _trials() -> list[dict]:
    return [
        {
            "trial_id": "trial-001",
            "status": "complete",
            "parameters": {"lookback": 20},
            "objective_value": 0.12,
            "metrics": {"validation_return": 0.12},
        },
        {
            "trial_id": "trial-002",
            "status": "failed",
            "parameters": {"lookback": 80},
            "metrics": {},
            "failure_reason": "insufficient_samples",
        },
    ]


def test_strategy_model_run_records_all_trials_and_boundaries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = build_strategy_model_run(
        strategy_id="ndx-breakout-001",
        training_data_path=_training_data(tmp_path),
        label_definition="next_10_bar_return",
        split="train=2024,validation=2025,holdout=2026",
        search_space={"lookback": [20, 80]},
        trials=_trials(),
        out_dir=tmp_path / "data/strategy_model_loop/ndx-breakout-001",
        seed=42,
        best_trial_id="trial-001",
        holdout_result={"return": 0.03, "drawdown": -0.01},
        limitations=["small holdout window"],
        output_route=ModelOutputRoute.REVISION_REQUEST_ONLY,
    )

    assert result.trial_ledger.summary.trial_count == 2
    assert result.trial_ledger.summary.failed_count == 1
    assert result.trial_ledger.summary.success_only_reporting is False
    assert result.model_run.training_data.sha256.startswith("sha256:")
    assert result.model_run.auto_applied is False
    assert result.model_run.direct_spec_edit_allowed is False
    assert result.model_run.output_route is ModelOutputRoute.REVISION_REQUEST_ONLY

    model_payload = json.loads(result.model_run_path.read_text(encoding="utf-8"))
    ledger_payload = json.loads(result.trial_ledger_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("strategy_model_run.v1.schema.json")).validate(model_payload)
    Draft202012Validator(_schema("strategy_optimizer_trial_ledger.v1.schema.json")).validate(
        ledger_payload
    )
    assert [trial["trial_id"] for trial in ledger_payload["trials"]] == [
        "trial-001",
        "trial-002",
    ]
    report = result.trial_ledger_report_path.read_text(encoding="utf-8")
    assert "insufficient_samples" in report


def test_strategy_model_run_rejects_unknown_best_trial(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(StrategyModelLoopError, match="best_trial_id"):
        build_strategy_model_run(
            strategy_id="ndx-breakout-001",
            training_data_path=_training_data(tmp_path),
            label_definition="next_10_bar_return",
            split="train=2024,validation=2025,holdout=2026",
            search_space={"lookback": [20, 80]},
            trials=_trials(),
            out_dir=tmp_path / "data/strategy_model_loop/ndx-breakout-001",
            best_trial_id="missing-trial",
        )
