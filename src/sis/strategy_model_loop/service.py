from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import sha256_file
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_model_loop.models import (
    ModelOutputRoute,
    OptimizerTrialStatus,
    StrategyModelRun,
    StrategyModelTrainingData,
    StrategyOptimizerTrial,
    StrategyOptimizerTrialLedger,
    StrategyOptimizerTrialLedgerSummary,
)
from sis.strategy_model_loop.rendering import (
    render_optimizer_trial_ledger_markdown,
    render_strategy_model_run_markdown,
)
from sis.strategy_review.provenance import repo_relative_path
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class StrategyModelLoopResult:
    model_run: StrategyModelRun
    trial_ledger: StrategyOptimizerTrialLedger
    model_run_path: Path
    model_run_report_path: Path
    trial_ledger_path: Path
    trial_ledger_report_path: Path


class StrategyModelLoopError(ValueError):
    pass


class StrategyModelLoopOutputExistsError(StrategyModelLoopError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _hash_payload(payload: object) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(data).hexdigest()


def parse_json_object(value: str, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise StrategyModelLoopError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise StrategyModelLoopError(f"{label} must be a JSON object")
    return payload


def _trial_from_payload(payload: dict[str, Any]) -> StrategyOptimizerTrial:
    return StrategyOptimizerTrial.model_validate(payload)


def _ledger_summary(trials: list[StrategyOptimizerTrial]) -> StrategyOptimizerTrialLedgerSummary:
    counts = Counter(trial.status for trial in trials)
    return StrategyOptimizerTrialLedgerSummary(
        trial_count=len(trials),
        complete_count=counts[OptimizerTrialStatus.COMPLETE],
        failed_count=counts[OptimizerTrialStatus.FAILED],
        pruned_count=counts[OptimizerTrialStatus.PRUNED],
        running_count=counts[OptimizerTrialStatus.RUNNING],
    )


def build_strategy_model_run(
    *,
    strategy_id: str,
    training_data_path: Path,
    label_definition: str,
    split: str,
    search_space: dict[str, Any],
    trials: list[dict[str, Any]],
    out_dir: Path,
    model_run_id: str = "strategy-model-run",
    ledger_id: str = "strategy-optimizer-trial-ledger",
    seed: int | None = None,
    best_trial_id: str | None = None,
    holdout_result: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    output_route: ModelOutputRoute = ModelOutputRoute.REVISION_REQUEST_ONLY,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyModelLoopResult:
    if not training_data_path.exists():
        raise FileNotFoundError(f"training data missing: {training_data_path}")
    if not trials:
        raise StrategyModelLoopError("at least one trial is required")
    parsed_trials = [_trial_from_payload(payload) for payload in trials]
    trial_ids = {trial.trial_id for trial in parsed_trials}
    if best_trial_id is not None and best_trial_id not in trial_ids:
        raise StrategyModelLoopError("best_trial_id must reference a recorded trial")

    selected_holdout = holdout_result or {}
    now = created_at or _utc_now()
    ledger = StrategyOptimizerTrialLedger(
        ledger_id=ledger_id,
        strategy_id=strategy_id,
        created_at=now,
        producer=StageProducer(command="strategy-model-run-record"),
        search_space=search_space,
        trials=parsed_trials,
        best_trial_id=best_trial_id,
        holdout_result=selected_holdout,
        summary=_ledger_summary(parsed_trials),
    )

    ledger_path = out_dir / "strategy_optimizer_trial_ledger.json"
    ledger_report_path = out_dir / "strategy_optimizer_trial_ledger.md"
    model_run_path = out_dir / "strategy_model_run.json"
    model_run_report_path = out_dir / "strategy_model_run.md"
    if not replace_existing and (
        ledger_path.exists()
        or ledger_report_path.exists()
        or model_run_path.exists()
        or model_run_report_path.exists()
    ):
        raise StrategyModelLoopOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )

    write_json_artifact(ledger_path, ledger.model_dump(mode="json", exclude_none=True))
    model_run = StrategyModelRun(
        model_run_id=model_run_id,
        strategy_id=strategy_id,
        created_at=now,
        producer=StageProducer(command="strategy-model-run-record"),
        training_data=StrategyModelTrainingData(
            path=repo_relative_path(training_data_path),
            sha256=sha256_file(training_data_path),
        ),
        label_definition=label_definition,
        split=split,
        seed=seed,
        search_space_hash=_hash_payload(search_space),
        optimizer_trial_ledger_path=repo_relative_path(ledger_path),
        optimizer_trial_ledger_sha256=sha256_file(ledger_path),
        best_trial_id=best_trial_id,
        holdout_result=selected_holdout,
        limitations=limitations or [],
        output_route=output_route,
    )
    write_json_artifact(model_run_path, model_run.model_dump(mode="json", exclude_none=True))
    write_text_artifact(ledger_report_path, render_optimizer_trial_ledger_markdown(ledger))
    write_text_artifact(model_run_report_path, render_strategy_model_run_markdown(model_run))
    return StrategyModelLoopResult(
        model_run=model_run,
        trial_ledger=ledger,
        model_run_path=model_run_path,
        model_run_report_path=model_run_report_path,
        trial_ledger_path=ledger_path,
        trial_ledger_report_path=ledger_report_path,
    )
