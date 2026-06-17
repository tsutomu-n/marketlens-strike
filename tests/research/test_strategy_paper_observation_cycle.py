from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from research.test_ndx_layer25_strategy_lab_export import _validate_json_artifact
from research.test_ndx_layer26_paper_observation_gate import _layer25_export, _write_xyz_quote
from support.cli import invoke_cli


def test_strategy_paper_observation_cycle_creates_fresh_session_and_reviews(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir, artifact_dir, reports_dir = _prepare_promoted_paper_candidate(tmp_path, monkeypatch)
    _write_backtest_acceptance(
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    )
    stale_preview = data_dir / "bot/paper_intent_preview.json"
    stale_preview.parent.mkdir(parents=True, exist_ok=True)
    stale_preview.write_text(
        json.dumps(
            [
                {
                    "schema_version": "paper_intent_preview.v1",
                    "intent_id": "stale-intent",
                    "generated_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                }
            ]
        ),
        encoding="utf-8",
    )

    result = invoke_cli(
        [
            "strategy-paper-observation-cycle",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-id",
            "session-001",
            "--smoke",
        ]
    )

    assert result.exit_code == 0, result.stdout
    session_dir = data_dir / "paper/observations/session-001"
    manifest_path = session_dir / "paper_observation_session_manifest.json"
    ledger_path = session_dir / "paper_observation_ledger.jsonl"
    session_review_path = session_dir / "paper_observation_review_decision.json"
    canonical_review_path = artifact_dir / "paper_observation_review_decision.json"
    lifecycle_path = data_dir / "research/strategy_lifecycle/strategy_lifecycle_review.json"
    assert manifest_path.exists()
    assert ledger_path.exists()
    assert session_review_path.exists()
    assert canonical_review_path.exists()
    assert lifecycle_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_json_artifact(
        schema_path=Path("schemas/paper_observation_session_manifest.v1.schema.json"),
        artifact_path=manifest_path,
    )
    assert manifest["smoke"] is True
    assert manifest["thresholds"]["min_fills_for_pass"] == 1
    assert manifest["thresholds"]["min_trading_days_for_pass"] == 1
    assert manifest["observation_ledger_path"] == ledger_path.as_posix()
    assert (
        manifest["source_intent_preview_path"]
        == (session_dir / "source_artifacts/paper_intent_preview.json").as_posix()
    )
    assert manifest["source_intent_preview_original_path"] == stale_preview.as_posix()
    assert (
        manifest["source_paper_candidate_pack_path"]
        == (data_dir / "research/paper_candidate_pack.json").as_posix()
    )
    assert manifest["source_paper_candidate_pack_sha256"].startswith("sha256:")
    assert (
        manifest["source_promotion_decision_path"]
        == (data_dir / "research/promotion_decision.json").as_posix()
    )
    assert manifest["source_promotion_decision_sha256"].startswith("sha256:")
    assert manifest["permits_live_order"] is False
    assert manifest["wallet_used"] is False
    assert "stale-intent" not in stale_preview.read_text(encoding="utf-8")
    ledger_row = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert ledger_row["status"] == "paper_filled"
    assert ledger_row["venue_write_used"] is False
    review = json.loads(canonical_review_path.read_text(encoding="utf-8"))
    assert review["decision"] == "PASS_PAPER_OBSERVATION_REVIEW"
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    assert lifecycle["decision"] == "CONTINUE_EXECUTION_READINESS"
    assert lifecycle["permits_live_order"] is False


def test_strategy_paper_observation_cycle_requires_passed_backtest(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir, artifact_dir, reports_dir = _prepare_promoted_paper_candidate(tmp_path, monkeypatch)
    _write_backtest_acceptance(
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json",
        decision="FAIL_BACKTEST_ACCEPTANCE",
    )

    result = invoke_cli(
        [
            "strategy-paper-observation-cycle",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-id",
            "session-001",
            "--smoke",
        ]
    )

    assert result.exit_code == 2
    assert "strategy backtest acceptance is not passed" in result.stdout
    assert not (data_dir / "paper/observations/session-001").exists()


def test_strategy_paper_observation_cycle_rejects_existing_session_id(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir, artifact_dir, reports_dir = _prepare_promoted_paper_candidate(tmp_path, monkeypatch)
    _write_backtest_acceptance(
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    )
    command = [
        "strategy-paper-observation-cycle",
        "--data-dir",
        str(data_dir),
        "--artifact-dir",
        str(artifact_dir),
        "--reports-dir",
        str(reports_dir),
        "--session-id",
        "session-001",
        "--smoke",
    ]

    first = invoke_cli(command)
    assert first.exit_code == 0, first.stdout
    ledger_path = data_dir / "paper/observations/session-001/paper_observation_ledger.jsonl"
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == 1
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_before = preview_path.read_text(encoding="utf-8")

    second = invoke_cli(command)

    assert second.exit_code == 2
    assert "paper observation session already exists" in second.stdout
    assert "use a unique --session-id" in second.stdout
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == 1
    assert preview_path.read_text(encoding="utf-8") == preview_before


def test_strategy_paper_observation_append_extends_existing_session_and_reviews(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir, artifact_dir, reports_dir = _prepare_promoted_paper_candidate(tmp_path, monkeypatch)
    _write_backtest_acceptance(
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    )
    cycle = invoke_cli(
        [
            "strategy-paper-observation-cycle",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-id",
            "session-append",
            "--min-fills-for-pass",
            "2",
            "--min-trading-days-for-pass",
            "1",
        ]
    )
    assert cycle.exit_code == 0, cycle.stdout
    assert "paper_review_decision=NEEDS_MORE_PAPER_OBSERVATION" in cycle.stdout
    session_dir = data_dir / "paper/observations/session-append"
    manifest_path = session_dir / "paper_observation_session_manifest.json"
    ledger_path = session_dir / "paper_observation_ledger.jsonl"
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_before = preview_path.read_text(encoding="utf-8")
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == 1

    append = invoke_cli(
        [
            "strategy-paper-observation-append",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-manifest",
            str(manifest_path),
        ]
    )

    assert append.exit_code == 0, append.stdout
    assert "appended_ledger_entries=1" in append.stdout
    assert "ledger_entry_count=2" in append.stdout
    assert "paper_review_decision=PASS_PAPER_OBSERVATION_REVIEW" in append.stdout
    assert "observation_state=normal_observation_passed_not_live_ready" in append.stdout
    assert len(ledger_path.read_text(encoding="utf-8").splitlines()) == 2
    assert preview_path.read_text(encoding="utf-8") == preview_before
    review = json.loads((session_dir / "paper_observation_review_decision.json").read_text())
    assert review["decision"] == "PASS_PAPER_OBSERVATION_REVIEW"
    assert review["metrics"]["fills_count"] == 2
    summary = json.loads((session_dir / "paper_observation_append_summary.json").read_text())
    assert summary["appended_ledger_entries"] == 1
    assert summary["ledger_entry_count"] == 2
    status = json.loads(
        (data_dir / "research/strategy_lifecycle/paper_observation_status.json").read_text()
    )
    assert status["normal_thresholds_met"] is True


def test_strategy_paper_observation_append_rejects_source_hash_mismatch_before_write(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir, artifact_dir, reports_dir = _prepare_promoted_paper_candidate(tmp_path, monkeypatch)
    _write_backtest_acceptance(
        data_dir / "research/strategy_lifecycle/backtest_acceptance_decision.json"
    )
    cycle = invoke_cli(
        [
            "strategy-paper-observation-cycle",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-id",
            "session-hash-mismatch",
            "--smoke",
        ]
    )
    assert cycle.exit_code == 0, cycle.stdout
    session_dir = data_dir / "paper/observations/session-hash-mismatch"
    manifest_path = session_dir / "paper_observation_session_manifest.json"
    ledger_path = session_dir / "paper_observation_ledger.jsonl"
    before_lines = ledger_path.read_text(encoding="utf-8").splitlines()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    Path(manifest["source_intent_preview_path"]).write_text("[]\n", encoding="utf-8")

    append = invoke_cli(
        [
            "strategy-paper-observation-append",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--session-manifest",
            str(manifest_path),
        ]
    )

    assert append.exit_code == 2
    assert "intent preview hash mismatch" in append.stdout
    assert ledger_path.read_text(encoding="utf-8").splitlines() == before_lines


def _prepare_promoted_paper_candidate(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
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
    return data_dir, artifact_dir, reports_dir


def _write_backtest_acceptance(path: Path, *, decision: str = "PASS_BACKTEST_ACCEPTANCE") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_backtest_acceptance_decision.v1",
                "decision": decision,
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "venue_write_used": False,
                "exchange_write_used": False,
            }
        ),
        encoding="utf-8",
    )
