from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.paper.observation_session import (
    PaperObservationThresholds,
    create_paper_observation_session,
)
from sis.paper.runner import run_paper_from_intents
from support.cli import invoke_cli
from research.test_ndx_layer25_strategy_lab_export import _validate_json_artifact
from research.test_ndx_layer26_paper_observation_gate import (
    _layer25_export,
    _write_xyz_quote,
)


def test_layer28_passes_completed_paper_observation_review(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--min-fills-for-pass",
            "1",
            "--min-trading-days-for-pass",
            "1",
        ]
    )

    assert result.exit_code == 0, result.stdout
    review_path = artifact_dir / "paper_observation_review_decision.json"
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "PASS_PAPER_OBSERVATION_REVIEW"
    assert payload["metrics"]["fills_count"] == 1
    assert payload["metrics"]["trading_day_count"] == 1
    assert payload["metrics"]["timestamp_quality"] == "complete"
    assert payload["metrics"]["blocked_count"] == 0
    assert payload["permits_live_order"] is False
    assert payload["live_conversion_allowed"] is False
    assert payload["wallet_used"] is False
    assert payload["venue_write_used"] is False
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_paper_observation_review_decision.v1.schema.json"),
        artifact_path=review_path,
    )


def test_layer28_needs_more_observation_before_min_fill_threshold(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (artifact_dir / "paper_observation_review_decision.json").read_text(encoding="utf-8")
    )
    assert payload["decision"] == "NEEDS_MORE_PAPER_OBSERVATION"
    assert "INSUFFICIENT_PAPER_FILLS" in payload["reason_codes"]
    assert "INSUFFICIENT_TRADING_DAYS" in payload["reason_codes"]
    assert payload["block_reasons"] == []


def test_layer28_needs_more_observation_before_min_trading_days(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--min-fills-for-pass",
            "1",
            "--min-trading-days-for-pass",
            "2",
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (artifact_dir / "paper_observation_review_decision.json").read_text(encoding="utf-8")
    )
    assert payload["decision"] == "NEEDS_MORE_PAPER_OBSERVATION"
    assert payload["metrics"]["trading_day_count"] == 1
    assert "INSUFFICIENT_TRADING_DAYS" in payload["reason_codes"]


def test_layer28_does_not_pass_timestamp_incomplete_ledger(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)
    ledger_path = data_dir / "paper/paper_observation_ledger.jsonl"
    row = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    for key in ("created_at", "ts_fill", "fill_ts", "ts_order", "order_ts", "quote_ts"):
        row.pop(key, None)
    ledger_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--min-fills-for-pass",
            "1",
            "--min-trading-days-for-pass",
            "1",
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (artifact_dir / "paper_observation_review_decision.json").read_text(encoding="utf-8")
    )
    assert payload["decision"] == "NEEDS_MORE_PAPER_OBSERVATION"
    assert payload["metrics"]["timestamp_quality"] == "missing_or_partial"
    assert "PAPER_OBSERVATION_TIMESTAMPS_INCOMPLETE" in payload["reason_codes"]


def test_layer28_stops_on_paper_boundary_violation(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)
    ledger_path = data_dir / "paper/paper_observation_ledger.jsonl"
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "intent_id": "bad-intent",
                    "status": "paper_filled",
                    "live_order_submitted": True,
                    "wallet_used": False,
                    "exchange_write_used": False,
                }
            )
            + "\n"
        )

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--min-fills-for-pass",
            "1",
            "--min-trading-days-for-pass",
            "1",
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (artifact_dir / "paper_observation_review_decision.json").read_text(encoding="utf-8")
    )
    assert payload["decision"] == "STOP_PAPER_OBSERVATION"
    assert "PAPER_BOUNDARY_VIOLATION" in payload["block_reasons"]
    assert payload["metrics"]["live_boundary_violations"] == 1


def test_layer28_reviews_session_manifest_thresholds(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)
    manifest = _paper_session_manifest(
        data_dir=data_dir,
        artifact_dir=artifact_dir,
        session_id="session-001",
    )
    session_ledger = data_dir / "paper/observations/session-001/paper_observation_ledger.jsonl"
    session_ledger.write_text(
        (data_dir / "paper/paper_observation_ledger.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-manifest",
            str(manifest.manifest_path),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (artifact_dir / "paper_observation_review_decision.json").read_text(encoding="utf-8")
    )
    assert payload["decision"] == "PASS_PAPER_OBSERVATION_REVIEW"
    assert payload["observation_thresholds"]["min_fills_for_pass"] == 1
    assert payload["observation_thresholds"]["min_trading_days_for_pass"] == 1
    assert (
        payload["source_paper_observation_session_manifest_path"]
        == manifest.manifest_path.as_posix()
    )
    assert payload["source_paper_observation_session_manifest_hash"].startswith("sha256:")


def test_layer28_fails_on_session_manifest_ledger_mismatch(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)
    manifest = _paper_session_manifest(
        data_dir=data_dir,
        artifact_dir=artifact_dir,
        session_id="session-001",
    )

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-manifest",
            str(manifest.manifest_path),
            "--ledger-path",
            str(data_dir / "paper/paper_observation_ledger.jsonl"),
        ]
    )

    assert result.exit_code == 2
    assert "session manifest ledger path mismatch" in result.stdout


def test_layer28_fails_on_session_manifest_intent_hash_mismatch(tmp_path, monkeypatch) -> None:
    data_dir, artifact_dir, reports_dir = _run_layer27_paper_observation(tmp_path, monkeypatch)
    manifest = _paper_session_manifest(
        data_dir=data_dir,
        artifact_dir=artifact_dir,
        session_id="session-001",
    )
    session_ledger = data_dir / "paper/observations/session-001/paper_observation_ledger.jsonl"
    session_ledger.write_text(
        (data_dir / "paper/paper_observation_ledger.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (data_dir / "bot/paper_intent_preview.json").write_text("[]\n", encoding="utf-8")

    result = invoke_cli(
        [
            "research-ndx-paper-observation-review",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-manifest",
            str(manifest.manifest_path),
        ]
    )

    assert result.exit_code == 2
    assert "intent preview hash mismatch" in result.stdout


def test_layer28_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(
            Path("schemas/ndx_paper_observation_review_decision.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    )


def _run_layer27_paper_observation(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    data_dir, artifact_dir, reports_dir = _layer25_export(tmp_path)
    quotes_path = _write_xyz_quote(data_dir)
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    assert invoke_cli(["evaluate-strategy-lab"]).exit_code == 0
    assert invoke_cli(["build-paper-candidate-pack"]).exit_code == 0
    gate = invoke_cli(
        [
            "research-ndx-paper-observation-gate",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--quotes-path",
            str(quotes_path),
        ]
    )
    assert gate.exit_code == 0, gate.stdout
    promotion = invoke_cli(
        [
            "research-ndx-operator-promotion",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--decision",
            "promote_to_paper_observation",
            "--reviewer",
            "local_operator",
            "--approval-reason",
            "paper_observation_gate_reviewed",
        ]
    )
    assert promotion.exit_code == 0, promotion.stdout
    assert invoke_cli(["build-paper-candidate-pack"]).exit_code == 0
    assert invoke_cli(["promotion-decision", "--decision", "promote"]).exit_code == 0
    assert invoke_cli(["build-paper-intent-preview"]).exit_code == 0
    summary = run_paper_from_intents(
        data_dir, intents_path=data_dir / "bot/paper_intent_preview.json"
    )
    assert summary.orders_count == 1
    assert summary.fills_count == 1
    assert summary.blocked_count == 0
    return data_dir, artifact_dir, reports_dir


def _paper_session_manifest(data_dir: Path, artifact_dir: Path, session_id: str):
    backtest = data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    backtest.parent.mkdir(parents=True, exist_ok=True)
    backtest.write_text(
        json.dumps(
            {
                "schema_version": "strategy_backtest_acceptance_decision.v1",
                "decision": "PASS_BACKTEST_ACCEPTANCE",
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "venue_write_used": False,
                "exchange_write_used": False,
            }
        ),
        encoding="utf-8",
    )
    return create_paper_observation_session(
        data_dir=data_dir,
        source_backtest_acceptance_path=backtest,
        source_operator_promotion_path=artifact_dir / "operator_promotion_decision.json",
        source_intent_preview_path=data_dir / "bot/paper_intent_preview.json",
        session_id=session_id,
        thresholds=PaperObservationThresholds(
            min_fills_for_pass=1,
            min_trading_days_for_pass=1,
            max_blocked_rate=0.5,
            max_consecutive_blocked=3,
            max_open_position_age_hours=0.0,
        ),
    )
