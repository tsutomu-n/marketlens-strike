from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from support.cli import invoke_cli


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _backtest(path: Path, decision: str = "PASS_BACKTEST_ACCEPTANCE", **extra: object) -> Path:
    payload = {
        "schema_version": "strategy_backtest_acceptance_decision.v1",
        "decision": decision,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    payload.update(extra)
    return _write_json(path, payload)


def _paper(path: Path, decision: str = "PASS_PAPER_OBSERVATION_REVIEW", **extra: object) -> Path:
    payload = {
        "schema_version": "ndx_paper_observation_review_decision.v1",
        "decision": decision,
        "block_reasons": [],
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    payload.update(extra)
    return _write_json(path, payload)


def _phase(path: Path, decision: str = "READ_ONLY_GO", **extra: object) -> Path:
    payload = {
        "decision": decision,
        "execution_drift_classification_counts": {
            "P2_BLOCKER": 0,
            "LIVE_READINESS_BLOCKER": 0,
        },
    }
    payload.update(extra)
    return _write_json(path, payload)


def _run(tmp_path: Path, *, backtest: Path | None, paper: Path | None, phase: Path | None):
    args = [
        "strategy-lifecycle-review",
        "--data-dir",
        str(tmp_path / "data"),
        "--out",
        str(tmp_path / "out"),
        "--reports-dir",
        str(tmp_path / "reports"),
    ]
    if backtest is not None:
        args += ["--backtest-decision-path", str(backtest)]
    if paper is not None:
        args += ["--paper-review-path", str(paper)]
    if phase is not None:
        args += ["--phase-gate-path", str(phase)]
    result = invoke_cli(args)
    payload = json.loads((tmp_path / "out/strategy_lifecycle_review.json").read_text())
    return result, payload


def test_strategy_lifecycle_review_continues_research_without_backtest(tmp_path) -> None:
    result, payload = _run(tmp_path, backtest=None, paper=None, phase=None)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "CONTINUE_RESEARCH"
    assert payload["permits_live_order"] is False


def test_strategy_lifecycle_review_rejects_failed_backtest(tmp_path) -> None:
    backtest = _backtest(tmp_path / "backtest.json", "FAIL_BACKTEST_ACCEPTANCE")

    result, payload = _run(tmp_path, backtest=backtest, paper=None, phase=None)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "REJECT_OR_REVISE"


def test_strategy_lifecycle_review_accepts_backtest_before_paper_review(tmp_path) -> None:
    backtest = _backtest(tmp_path / "backtest.json")

    result, payload = _run(tmp_path, backtest=backtest, paper=None, phase=None)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "BACKTEST_ACCEPTED"


def test_strategy_lifecycle_review_continues_paper_observation(tmp_path) -> None:
    backtest = _backtest(tmp_path / "backtest.json")
    paper = _paper(tmp_path / "paper.json", "NEEDS_MORE_PAPER_OBSERVATION")

    result, payload = _run(tmp_path, backtest=backtest, paper=paper, phase=None)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "CONTINUE_PAPER_OBSERVATION"


def test_strategy_lifecycle_review_continues_execution_readiness_for_live_blockers(
    tmp_path,
) -> None:
    backtest = _backtest(tmp_path / "backtest.json")
    paper = _paper(tmp_path / "paper.json")
    phase = _phase(
        tmp_path / "phase.json",
        execution_drift_classification_counts={
            "P2_BLOCKER": 0,
            "LIVE_READINESS_BLOCKER": 2,
        },
    )

    result, payload = _run(tmp_path, backtest=backtest, paper=paper, phase=phase)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "CONTINUE_EXECUTION_READINESS"


def test_strategy_lifecycle_review_can_reach_live_canary_plan_gate_only(tmp_path) -> None:
    backtest = _backtest(tmp_path / "backtest.json")
    paper = _paper(tmp_path / "paper.json")
    phase = _phase(tmp_path / "phase.json")

    result, payload = _run(tmp_path, backtest=backtest, paper=paper, phase=phase)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "ELIGIBLE_FOR_LIVE_CANARY_PLAN"
    assert payload["permits_live_order"] is False
    assert payload["live_conversion_allowed"] is False
    assert payload["wallet_used"] is False
    assert payload["venue_write_used"] is False
    assert payload["exchange_write_used"] is False
    assert (
        "does not permit live orders"
        in (tmp_path / "reports/strategy_lifecycle_review.md").read_text()
    )
    Draft202012Validator(
        json.loads(Path("schemas/strategy_lifecycle_review.v1.schema.json").read_text())
    ).validate(payload)


def test_strategy_lifecycle_review_blocks_any_boundary_flag(tmp_path) -> None:
    backtest = _backtest(tmp_path / "backtest.json", permits_live_order=True)

    result, payload = _run(tmp_path, backtest=backtest, paper=None, phase=None)

    assert result.exit_code == 0, result.stdout
    assert payload["decision"] == "BLOCKED_BOUNDARY_VIOLATION"
    assert payload["boundary_flags"]["permits_live_order"] is True


def test_strategy_lifecycle_review_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(Path("schemas/strategy_lifecycle_review.v1.schema.json").read_text())
    )
