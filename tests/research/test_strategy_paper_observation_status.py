from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from support.cli import invoke_cli


def test_strategy_paper_observation_status_splits_normal_and_smoke_sessions(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    reports_dir = tmp_path / "reports"
    out_dir = data_dir / "research/strategy_lifecycle"
    normal_manifest = _session_manifest(
        data_dir=data_dir,
        session_id="normal-001",
        created_at="2026-06-12T21:07:00+00:00",
        smoke=False,
        min_fills=20,
        min_days=10,
    )
    normal_review = _session_review(
        manifest_path=normal_manifest,
        decision="NEEDS_MORE_PAPER_OBSERVATION",
        fills=1,
        trading_days=1,
        reason_codes=["INSUFFICIENT_PAPER_FILLS", "INSUFFICIENT_TRADING_DAYS"],
    )
    smoke_manifest = _session_manifest(
        data_dir=data_dir,
        session_id="smoke-001",
        created_at="2026-06-12T21:10:00+00:00",
        smoke=True,
        min_fills=1,
        min_days=1,
    )
    _session_review(
        manifest_path=smoke_manifest,
        decision="PASS_PAPER_OBSERVATION_REVIEW",
        fills=1,
        trading_days=1,
    )
    canonical_review = data_dir / "research/ndx/paper_observation_review_decision.json"
    _copy_json(normal_review, canonical_review)
    _lifecycle_review(
        path=out_dir / "strategy_lifecycle_review.json",
        paper_review_path=canonical_review,
        decision="CONTINUE_PAPER_OBSERVATION",
        reasons=["PAPER_OBSERVATION_INSUFFICIENT"],
    )

    result = invoke_cli(
        [
            "strategy-paper-observation-status",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    assert "observation_state=needs_more_normal_paper_observation" in result.stdout
    status_path = out_dir / "paper_observation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    _validate_status_schema(payload)
    assert payload["observation_state"] == "needs_more_normal_paper_observation"
    assert payload["next_action"] == "continue_normal_paper_observation"
    assert payload["canonical_review_decision"] == "NEEDS_MORE_PAPER_OBSERVATION"
    assert payload["canonical_review_session_id"] == "normal-001"
    assert payload["canonical_review_session_smoke"] is False
    assert payload["canonical_matches_latest_normal"] is True
    assert payload["lifecycle_decision"] == "CONTINUE_PAPER_OBSERVATION"
    assert payload["lifecycle_decision_reasons"] == ["PAPER_OBSERVATION_INSUFFICIENT"]
    assert payload["normal_session_count"] == 1
    assert payload["smoke_session_count"] == 1
    assert payload["latest_normal_session_id"] == "normal-001"
    assert payload["latest_normal_decision"] == "NEEDS_MORE_PAPER_OBSERVATION"
    assert payload["latest_smoke_session_id"] == "smoke-001"
    assert payload["latest_smoke_decision"] == "PASS_PAPER_OBSERVATION_REVIEW"
    assert payload["normal_thresholds_met"] is False
    gaps = payload["latest_normal_requirement_gaps"]
    assert gaps["session_id"] == "normal-001"
    assert gaps["available"] is True
    assert gaps["fills"] == {
        "observed": 1,
        "required": 20,
        "remaining": 19,
        "met": False,
    }
    assert gaps["trading_days"] == {
        "observed": 1,
        "required": 10,
        "remaining": 9,
        "met": False,
    }
    assert gaps["timestamp_quality"] == {
        "observed": "complete",
        "required": "complete",
        "met": True,
    }
    assert payload["smoke_pass_present"] is True
    assert payload["smoke_pass_counts_as_normal_pass"] is False
    assert payload["permits_live_order"] is False
    assert payload["live_conversion_allowed"] is False
    assert payload["credentials_used"] is False
    assert payload["external_api_used"] is False
    assert payload["wallet_used"] is False
    assert payload["venue_write_used"] is False
    assert payload["exchange_write_used"] is False
    assert payload["incomplete_artifacts"] == []
    assert payload["stale_artifacts"] == []
    assert [session["session_id"] for session in payload["sessions"]] == [
        "normal-001",
        "smoke-001",
    ]
    report = (reports_dir / "paper_observation_status.md").read_text(encoding="utf-8")
    assert "latest_normal_fills: 1/20 (remaining=19)" in report
    assert "latest_normal_trading_days: 1/10 (remaining=9)" in report
    assert "smoke_pass_counts_as_normal_pass: false" in report
    assert "live readiness" in report


def test_strategy_paper_observation_status_marks_smoke_only_as_not_normal_pass(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    reports_dir = tmp_path / "reports"
    out_dir = data_dir / "research/strategy_lifecycle"
    smoke_manifest = _session_manifest(
        data_dir=data_dir,
        session_id="smoke-only",
        created_at="2026-06-12T21:10:00+00:00",
        smoke=True,
        min_fills=1,
        min_days=1,
    )
    smoke_review = _session_review(
        manifest_path=smoke_manifest,
        decision="PASS_PAPER_OBSERVATION_REVIEW",
        fills=1,
        trading_days=1,
    )
    canonical_review = data_dir / "research/ndx/paper_observation_review_decision.json"
    _copy_json(smoke_review, canonical_review)
    _lifecycle_review(
        path=out_dir / "strategy_lifecycle_review.json",
        paper_review_path=canonical_review,
        decision="CONTINUE_EXECUTION_READINESS",
        reasons=["PHASE_GATE_MISSING"],
    )

    result = invoke_cli(
        [
            "strategy-paper-observation-status",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out_dir / "paper_observation_status.json").read_text(encoding="utf-8"))
    assert payload["observation_state"] == "smoke_only_not_normal_pass"
    assert payload["next_action"] == "continue_normal_paper_observation"
    assert payload["normal_thresholds_met"] is False
    assert payload["latest_normal_requirement_gaps"]["available"] is False
    assert payload["smoke_pass_present"] is True
    assert payload["smoke_pass_counts_as_normal_pass"] is False
    assert payload["canonical_review_session_smoke"] is True
    assert payload["canonical_matches_latest_normal"] is False


def test_strategy_paper_observation_status_writes_incomplete_artifact_status(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    out_dir = data_dir / "research/strategy_lifecycle"

    result = invoke_cli(
        [
            "strategy-paper-observation-status",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(tmp_path / "reports"),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out_dir / "paper_observation_status.json").read_text(encoding="utf-8"))
    assert payload["observation_state"] == "incomplete_artifacts"
    assert payload["next_action"] == "no_action_until_artifacts_exist"
    assert payload["normal_session_count"] == 0
    assert payload["smoke_session_count"] == 0
    missing_names = {artifact["name"] for artifact in payload["incomplete_artifacts"]}
    assert {"canonical_paper_review", "lifecycle_review"}.issubset(missing_names)


def test_strategy_paper_observation_status_detects_stale_canonical_manifest_hash(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    out_dir = data_dir / "research/strategy_lifecycle"
    normal_manifest = _session_manifest(
        data_dir=data_dir,
        session_id="normal-001",
        created_at="2026-06-12T21:07:00+00:00",
        smoke=False,
        min_fills=20,
        min_days=10,
    )
    review = _session_review(
        manifest_path=normal_manifest,
        decision="NEEDS_MORE_PAPER_OBSERVATION",
        fills=1,
        trading_days=1,
        reason_codes=["INSUFFICIENT_PAPER_FILLS"],
    )
    canonical_review = data_dir / "research/ndx/paper_observation_review_decision.json"
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["source_paper_observation_session_manifest_hash"] = "sha256:" + "0" * 64
    _write_json(canonical_review, payload)
    _lifecycle_review(
        path=out_dir / "strategy_lifecycle_review.json",
        paper_review_path=canonical_review,
        decision="CONTINUE_PAPER_OBSERVATION",
        reasons=["PAPER_OBSERVATION_INSUFFICIENT"],
    )

    result = invoke_cli(
        [
            "strategy-paper-observation-status",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(tmp_path / "reports"),
        ]
    )

    assert result.exit_code == 0, result.stdout
    status = json.loads((out_dir / "paper_observation_status.json").read_text(encoding="utf-8"))
    assert status["observation_state"] == "stale_or_mismatched_artifacts"
    assert status["next_action"] == "manual_review_required"
    assert status["stale_artifacts"][0]["name"] == "canonical_session_manifest"


def test_strategy_paper_observation_status_detects_session_boundary_violation(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    out_dir = data_dir / "research/strategy_lifecycle"
    normal_manifest = _session_manifest(
        data_dir=data_dir,
        session_id="normal-001",
        created_at="2026-06-12T21:07:00+00:00",
        smoke=False,
        min_fills=20,
        min_days=10,
    )
    normal_review = _session_review(
        manifest_path=normal_manifest,
        decision="NEEDS_MORE_PAPER_OBSERVATION",
        fills=1,
        trading_days=1,
        reason_codes=["INSUFFICIENT_PAPER_FILLS"],
    )
    smoke_manifest = _session_manifest(
        data_dir=data_dir,
        session_id="smoke-001",
        created_at="2026-06-12T21:10:00+00:00",
        smoke=True,
        min_fills=1,
        min_days=1,
    )
    smoke_review = _session_review(
        manifest_path=smoke_manifest,
        decision="PASS_PAPER_OBSERVATION_REVIEW",
        fills=1,
        trading_days=1,
    )
    smoke_payload = json.loads(smoke_review.read_text(encoding="utf-8"))
    smoke_payload["venue_write_used"] = True
    _write_json(smoke_review, smoke_payload)
    canonical_review = data_dir / "research/ndx/paper_observation_review_decision.json"
    _copy_json(normal_review, canonical_review)
    _lifecycle_review(
        path=out_dir / "strategy_lifecycle_review.json",
        paper_review_path=canonical_review,
        decision="CONTINUE_PAPER_OBSERVATION",
        reasons=["PAPER_OBSERVATION_INSUFFICIENT"],
    )

    result = invoke_cli(
        [
            "strategy-paper-observation-status",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(tmp_path / "reports"),
        ]
    )

    assert result.exit_code == 0, result.stdout
    status = json.loads((out_dir / "paper_observation_status.json").read_text(encoding="utf-8"))
    assert status["observation_state"] == "source_boundary_violation"
    assert "session_review:smoke-001.venue_write_used" in status["source_boundary_violations"]


def test_strategy_paper_observation_status_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(
            Path("schemas/strategy_paper_observation_status.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    )


def _validate_status_schema(payload: dict) -> None:
    Draft202012Validator(
        json.loads(
            Path("schemas/strategy_paper_observation_status.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    ).validate(payload)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _copy_json(source: Path, target: Path) -> Path:
    return _write_json(target, json.loads(source.read_text(encoding="utf-8")))


def _sha256(path: Path) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _session_manifest(
    *,
    data_dir: Path,
    session_id: str,
    created_at: str,
    smoke: bool,
    min_fills: int,
    min_days: int,
) -> Path:
    session_dir = data_dir / f"paper/observations/{session_id}"
    payload = {
        "schema_version": "paper_observation_session_manifest.v1",
        "session_id": session_id,
        "created_at": created_at,
        "data_dir": data_dir.as_posix(),
        "session_dir": session_dir.as_posix(),
        "observation_ledger_path": (session_dir / "paper_observation_ledger.jsonl").as_posix(),
        "paper_orders_path": (data_dir / "paper/orders.parquet").as_posix(),
        "paper_fills_path": (data_dir / "paper/fills.parquet").as_posix(),
        "paper_positions_path": (data_dir / "paper/positions.parquet").as_posix(),
        "source_backtest_acceptance_path": (data_dir / "backtest.json").as_posix(),
        "source_backtest_acceptance_sha256": "sha256:" + "1" * 64,
        "source_operator_promotion_path": (data_dir / "operator.json").as_posix(),
        "source_operator_promotion_sha256": "sha256:" + "2" * 64,
        "source_intent_preview_path": (data_dir / "intent.json").as_posix(),
        "source_intent_preview_sha256": "sha256:" + "3" * 64,
        "thresholds": {
            "max_blocked_rate": 0.5,
            "max_consecutive_blocked": 3,
            "max_open_position_age_hours": 0.0,
            "min_fills_for_pass": min_fills,
            "min_trading_days_for_pass": min_days,
        },
        "smoke": smoke,
        "external_api_used": False,
        "credentials_used": False,
        "permits_live_order": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    return _write_json(session_dir / "paper_observation_session_manifest.json", payload)


def _session_review(
    *,
    manifest_path: Path,
    decision: str,
    fills: int,
    trading_days: int,
    reason_codes: list[str] | None = None,
) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "ndx_paper_observation_review_decision.v1",
        "review_id": "sha256:" + manifest["session_id"].encode().hex().ljust(64, "0")[:64],
        "created_at": manifest["created_at"],
        "decision": decision,
        "source_paper_observation_session_manifest_path": manifest_path.as_posix(),
        "source_paper_observation_session_manifest_hash": _sha256(manifest_path),
        "paper_observation_ledger_path": manifest["observation_ledger_path"],
        "paper_observation_ledger_hash": "sha256:" + "4" * 64,
        "observation_thresholds": manifest["thresholds"],
        "metrics": {
            "ledger_entry_count": fills,
            "fills_count": fills,
            "blocked_count": 0,
            "blocked_rate": 0.0,
            "max_consecutive_blocked": 0,
            "trading_day_count": trading_days,
            "trading_days": ["2026-06-12"][:trading_days],
            "missing_timestamp_count": 0,
            "timestamp_quality": "complete",
            "status_counts": {"paper_filled": fills},
            "block_reason_counts": {},
            "live_boundary_violations": 0,
            "unknown_statuses": [],
        },
        "reason_codes": reason_codes or [],
        "block_reasons": [],
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "external_api_used": False,
        "credentials_used": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    return _write_json(manifest_path.parent / "paper_observation_review_decision.json", payload)


def _lifecycle_review(
    *,
    path: Path,
    paper_review_path: Path,
    decision: str,
    reasons: list[str],
) -> Path:
    payload = {
        "schema_version": "strategy_lifecycle_review.v1",
        "review_id": "sha256:" + "5" * 64,
        "created_at": "2026-06-12T21:15:00+00:00",
        "decision": decision,
        "decision_reasons": reasons,
        "next_actions": ["Continue paper observation until thresholds are met."],
        "source_paper_review_path": paper_review_path.as_posix(),
        "source_paper_review_hash": _sha256(paper_review_path),
        "input_status": {
            "backtest_acceptance_present": True,
            "paper_review_present": True,
            "phase_gate_present": False,
        },
        "blocker_counts": {"P2_BLOCKER": 0, "LIVE_READINESS_BLOCKER": 0},
        "boundary_flags": {},
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }
    return _write_json(path, payload)
