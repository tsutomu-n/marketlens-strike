from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_review.service import (
    StrategyReviewOutputExistsError,
    build_strategy_review,
)


CREATED_AT = "2026-06-16T09:00:00Z"


def _manifest_schema() -> dict:
    return json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas/strategy_review_manifest.v1.schema.json"
        ).read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_required_artifacts(
    root: Path,
    *,
    wallet_used: bool = False,
    spec_path: str | None = None,
) -> tuple[Path, Path]:
    pack_path = root / "data/research/backtest_pack/strategy_backtest_pack.json"
    validation_path = root / "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    _write_json(
        pack_path,
        {
            "schema_version": "strategy_backtest_pack.v1",
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": wallet_used,
            "exchange_write_used": False,
            **({"spec_path": spec_path} if spec_path is not None else {}),
            "summary": {"suite_run_count": 1, "suite_method_count": 1},
            "external_framework_policy": {
                "policy_id": "native_primary_external_evaluation_only.v1",
                "standard_engine": "strategy_authoring_native",
                "decision": "complete_without_locked_external_dependency",
                "locked_dependency_added": False,
                "external_adapters_required_for_completion": False,
            },
            "artifacts": {},
        },
    )
    _write_json(
        validation_path,
        {
            "schema_version": "strategy_backtest_pack_validation.v1",
            "decision": "PASS",
            "paper_only": True,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "summary": {
                "check_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "locked_dependency_added": False,
            },
        },
    )
    return pack_path, validation_path


def _write_authoring_spec(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: trend_pullback_test_v1
  strategy_family: trend_pullback
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
  run_profile_id: strategy_lab_research_only
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
    any:
      - column: research_return_1d
        op: gt
        value: 0
  hold:
    any:
      - column: vix_level
        op: gte
        value: 30
  exit:
    stop_loss_bps: 150
    take_profit_bps: 300
  sizing:
    position_weight: 1.0
    notional_usd: 1000
backtest:
  split_method: purged_walk_forward
  label_horizon_minutes: 240
  primary_metric: total_return
""",
        encoding="utf-8",
    )


def _write_lifecycle_review(path: Path, *, venue_write_used: bool = False) -> None:
    _write_json(
        path,
        {
            "schema_version": "strategy_lifecycle_review.v1",
            "review_id": "sha256:" + "a" * 64,
            "created_at": CREATED_AT,
            "decision": "CONTINUE_PAPER_OBSERVATION",
            "decision_reasons": ["PAPER_OBSERVATION_INSUFFICIENT"],
            "next_actions": ["Continue paper observation until thresholds are met."],
            "source_backtest_acceptance_path": "",
            "source_backtest_acceptance_hash": "",
            "source_paper_review_path": "",
            "source_paper_review_hash": "",
            "source_phase_gate_path": "",
            "source_phase_gate_hash": "",
            "input_status": {
                "backtest_acceptance_present": True,
                "paper_review_present": True,
                "phase_gate_present": True,
            },
            "blocker_counts": {"P2_BLOCKER": 0, "LIVE_READINESS_BLOCKER": 1},
            "boundary_flags": {},
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "venue_write_used": venue_write_used,
            "exchange_write_used": False,
        },
    )


def test_build_strategy_review_writes_markdown_and_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="ndx-smoke-001",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.review_markdown_path.exists()
    assert result.manifest_path.exists()
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["review_status"] == "READY_FOR_HUMAN_REVIEW"
    assert payload["evaluation_flags"]["pack_validation_status"] == "PASS"
    assert payload["evaluation_flags"]["pack_validation_pass_is_readiness_proof"] is False
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert pack["path"] == "data/research/backtest_pack/strategy_backtest_pack.json"
    assert pack["sha256"].startswith("sha256:")
    assert len(pack["sha256"]) == len("sha256:") + 64
    assert not any(row["artifact_key"] == "authoring_spec" for row in payload["source_artifacts"])


def test_build_strategy_review_missing_required_artifact_is_incomplete(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "data/research/backtest_pack/strategy_backtest_pack.json"
    validation_path = (
        tmp_path / "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    )

    result = build_strategy_review(
        review_id="missing-pack",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        strict=False,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INCOMPLETE_ARTIFACTS"
    assert result.manifest.summary.missing_required_count == 2
    assert result.review_markdown_path.exists()
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_manifest_schema()).validate(payload)
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert "sha256" not in pack


def test_build_strategy_review_detects_boundary_violation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path, wallet_used=True)

    result = build_strategy_review(
        review_id="blocked-wallet",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert result.manifest.summary.boundary_violation_count == 1


def test_build_strategy_review_loads_authoring_yaml_from_pack_spec_path(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    spec_path = tmp_path / "docs/strategy_research_lab/examples/spec.yaml"
    _write_authoring_spec(spec_path)
    pack_path, validation_path = _write_required_artifacts(
        tmp_path,
        spec_path="docs/strategy_research_lab/examples/spec.yaml",
    )

    result = build_strategy_review(
        review_id="with-authoring",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "READY_FOR_HUMAN_REVIEW"
    authoring = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "authoring_spec"
    )
    assert authoring.status.value == "present"
    assert authoring.required is False
    assert authoring.summary["strategy_id"] == "trend_pullback_test_v1"
    assert authoring.summary["entry_rule_count"] == 2
    assert authoring.summary["hold_rule_count"] == 1


def test_build_strategy_review_missing_authoring_yaml_does_not_change_status(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="missing-authoring",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        authoring_spec_path=tmp_path / "missing-spec.yaml",
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "READY_FOR_HUMAN_REVIEW"
    authoring = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "authoring_spec"
    )
    assert authoring.status.value == "missing"


def test_build_strategy_review_invalid_authoring_yaml_is_invalid_input(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    spec_path = tmp_path / "invalid-spec.yaml"
    spec_path.write_text("schema_version: wrong\n", encoding="utf-8")

    result = build_strategy_review(
        review_id="invalid-authoring",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        authoring_spec_path=spec_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INVALID_INPUT"
    authoring = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "authoring_spec"
    )
    assert authoring.status.value == "invalid"


def test_build_strategy_review_loads_lifecycle_review(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    _write_lifecycle_review(lifecycle_path)

    result = build_strategy_review(
        review_id="with-lifecycle",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )

    lifecycle = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "lifecycle_review"
    )
    assert lifecycle.status.value == "present"
    assert lifecycle.summary["decision"] == "CONTINUE_PAPER_OBSERVATION"
    text = result.review_markdown_path.read_text(encoding="utf-8")
    assert "Continue paper observation until thresholds are met." in text


def test_build_strategy_review_invalid_lifecycle_review_is_invalid_input(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    _write_json(lifecycle_path, {"schema_version": "wrong"})

    result = build_strategy_review(
        review_id="invalid-lifecycle",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INVALID_INPUT"
    lifecycle = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "lifecycle_review"
    )
    assert lifecycle.status.value == "invalid"


def test_build_strategy_review_malformed_lifecycle_review_writes_invalid_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    _write_json(
        lifecycle_path,
        {
            "schema_version": "strategy_lifecycle_review.v1",
            "decision": "CONTINUE_PAPER_OBSERVATION",
            "decision_reasons": "not-a-list",
            "next_actions": ["Continue paper observation until thresholds are met."],
            "input_status": {},
            "blocker_counts": {},
        },
    )

    result = build_strategy_review(
        review_id="malformed-lifecycle",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INVALID_INPUT"
    assert result.manifest_path.exists()
    lifecycle = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "lifecycle_review"
    )
    assert lifecycle.status.value == "invalid"
    assert "decision_reasons" in lifecycle.summary["error"]


def test_build_strategy_review_lifecycle_venue_write_boundary_blocks(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    lifecycle_path = tmp_path / "lifecycle.json"
    _write_lifecycle_review(lifecycle_path, venue_write_used=True)

    result = build_strategy_review(
        review_id="blocked-lifecycle",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        lifecycle_review_path=lifecycle_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    lifecycle = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "lifecycle_review"
    )
    assert lifecycle.summary["boundary_violations"] == ["venue_write_used"]


def test_build_strategy_review_invalid_required_json_is_invalid_input(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    pack_path.write_text("{not-json", encoding="utf-8")

    result = build_strategy_review(
        review_id="invalid-pack",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INVALID_INPUT"
    assert result.manifest.summary.invalid_required_count == 1
    pack = next(
        artifact for artifact in result.manifest.source_artifacts if artifact.artifact_key == "pack"
    )
    validation = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "pack_validation"
    )
    assert pack.exists is True
    assert pack.status.value == "invalid"
    assert "error" in pack.summary
    assert validation.status.value == "present"
    assert "error" not in validation.summary
    assert "summary_unavailable_due_to" in validation.summary
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_manifest_schema()).validate(payload)


def test_build_strategy_review_refuses_existing_output_without_replace(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    kwargs = {
        "review_id": "same-id",
        "out_dir": tmp_path / "data/strategy_reviews",
        "pack_path": pack_path,
        "validation_path": validation_path,
        "created_at": CREATED_AT,
    }
    build_strategy_review(**kwargs)

    try:
        build_strategy_review(**kwargs)
    except StrategyReviewOutputExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing output error")
