from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

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
    signing_used: bool = False,
    exchange_write_used: bool = False,
    permits_live_order: bool = False,
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
            "permits_live_order": permits_live_order,
            "live_conversion_allowed": False,
            "wallet_used": wallet_used,
            "signing_used": signing_used,
            "exchange_write_used": exchange_write_used,
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


def _write_input_contract(path: Path, *, exchange_write_used: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "strategy_input_contract.v1",
        "contract_id": "ndx-breakout-inputs-001",
        "created_at": CREATED_AT,
        "producer": {"tool": "sis", "command": "manual"},
        "strategy_scope": {
            "strategy_family": "breakout",
            "instruments": ["NDX"],
            "timeframe": "1d",
            "intended_use": "research_backtest_only",
        },
        "sources": [
            {
                "source_id": "ndx_ohlcv_daily",
                "source_type": "raw_market_data",
                "path": "data/research/ndx/source/ohlcv.csv",
                "required": True,
                "declared_sha256": "sha256:" + "a" * 64,
                "schema_version": "market_ohlcv.v1",
                "generated_at": "2026-06-18T00:00:00Z",
                "available_at": "2026-06-18T00:05:00Z",
                "revision_policy": "append_only",
                "survivorship_policy": "current_constituents_not_allowed",
                "execution_reality": {
                    "includes_fills": False,
                    "includes_slippage": False,
                    "includes_latency": False,
                    "assumed_order_type": "none",
                },
            }
        ],
        "known_gaps": [],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": exchange_write_used,
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_strategy_idea(path: Path, *, wallet_used: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "strategy_idea.v1",
        "idea_id": "ndx-breakout-001",
        "created_at": CREATED_AT,
        "title": "NDX close breakout after volatility compression",
        "hypothesis": "NDX follow-through after low-volatility close breakout.",
        "mechanism": "trend_following",
        "timeframe": "1d",
        "instruments": ["NDX"],
        "required_input_contract_ids": ["ndx-breakout-inputs-001"],
        "baseline": {"name": "cash_or_no_trade", "expected_to_beat": True},
        "invalidation": ["no improvement over cash baseline"],
        "risk": {
            "max_position_notional_usd": 1000,
            "max_daily_loss_usd": 50,
            "kill_conditions": ["no fill in paper smoke"],
        },
        "execution_assumptions": {
            "order_type": "market_on_close_paper_intent",
            "slippage_model": "fixed_bps",
        },
        "authoring_intent": {
            "target": "strategy_authoring_draft",
            "auto_generate_spec": False,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": wallet_used,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


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
    assert payload["producer"] == {
        "command": "strategy-review-build",
        "schema_version": "strategy_review_manifest.v1",
        "tool": "sis",
    }
    assert "safety" not in payload
    assert payload["builder_safety"] == {
        "exchange_write_used": False,
        "live_conversion_allowed": False,
        "permits_live_order": False,
        "signing_used": False,
        "wallet_used": False,
    }
    assert payload["source_safety"]["status"] == "PASS"
    assert payload["source_safety"]["boundary_violation_count"] == 0
    assert payload["source_safety"]["unknown_boundary_count"] == 0
    assert payload["evaluation_flags"]["pack_validation_status"] == "PASS"
    assert payload["evaluation_flags"]["pack_validation_pass_is_readiness_proof"] is False
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert pack["path"] == "data/research/backtest_pack/strategy_backtest_pack.json"
    assert pack["sha256"].startswith("sha256:")
    assert len(pack["sha256"]) == len("sha256:") + 64
    assert pack["bytes"] == pack_path.stat().st_size
    assert pack["detected_schema_version"] == "strategy_backtest_pack.v1"
    assert not any(row["artifact_key"] == "authoring_spec" for row in payload["source_artifacts"])


def test_build_strategy_review_includes_input_contract_and_strategy_idea(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    input_contract_path = tmp_path / "configs/strategy_inputs/ndx-inputs.yaml"
    strategy_idea_path = tmp_path / "configs/strategy_ideas/ndx-idea.yaml"
    _write_input_contract(input_contract_path)
    _write_strategy_idea(strategy_idea_path)

    result = build_strategy_review(
        review_id="with-inputs",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        input_contract_path=input_contract_path,
        strategy_idea_path=strategy_idea_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "READY_FOR_HUMAN_REVIEW"
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_manifest_schema()).validate(payload)
    input_contract = next(
        row for row in payload["source_artifacts"] if row["artifact_key"] == "input_contract"
    )
    strategy_idea = next(
        row for row in payload["source_artifacts"] if row["artifact_key"] == "strategy_idea"
    )
    assert input_contract["status"] == "present"
    assert input_contract["required"] is False
    assert input_contract["summary"]["contract_id"] == "ndx-breakout-inputs-001"
    assert input_contract["summary"]["source_count"] == 1
    assert strategy_idea["status"] == "present"
    assert strategy_idea["required"] is False
    assert strategy_idea["summary"]["idea_id"] == "ndx-breakout-001"
    assert strategy_idea["summary"]["baseline_name"] == "cash_or_no_trade"
    text = result.review_markdown_path.read_text(encoding="utf-8")
    assert "## 6. Input Contract Summary" in text
    assert "## 7. Idea Intake Summary" in text
    assert "contract_id: `ndx-breakout-inputs-001`" in text
    assert "idea_id: `ndx-breakout-001`" in text


def test_build_strategy_review_missing_input_optional_does_not_change_status(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)

    result = build_strategy_review(
        review_id="missing-inputs",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        input_contract_path=tmp_path / "missing-input-contract.yaml",
        strategy_idea_path=tmp_path / "missing-idea.yaml",
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "READY_FOR_HUMAN_REVIEW"
    input_contract = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "input_contract"
    )
    strategy_idea = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "strategy_idea"
    )
    assert input_contract.status.value == "missing"
    assert strategy_idea.status.value == "missing"


def test_build_strategy_review_invalid_input_contract_is_invalid_input(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    input_contract_path = tmp_path / "configs/strategy_inputs/invalid.yaml"
    input_contract_path.parent.mkdir(parents=True)
    input_contract_path.write_text("schema_version: wrong\n", encoding="utf-8")

    result = build_strategy_review(
        review_id="invalid-input-contract",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        input_contract_path=input_contract_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "INVALID_INPUT"
    input_contract = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "input_contract"
    )
    assert input_contract.status.value == "invalid"


def test_build_strategy_review_strategy_idea_boundary_blocks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    strategy_idea_path = tmp_path / "configs/strategy_ideas/blocked.yaml"
    _write_strategy_idea(strategy_idea_path, wallet_used=True)

    result = build_strategy_review(
        review_id="blocked-idea",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        strategy_idea_path=strategy_idea_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert result.manifest.source_safety.observed_flags.wallet_used is True
    strategy_idea = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "strategy_idea"
    )
    assert strategy_idea.status.value == "blocked"
    assert strategy_idea.error == "source boundary violation: boundary.wallet_used"


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
    assert result.manifest.source_safety.status.value == "UNKNOWN"
    assert result.manifest.source_safety.unknown_boundary_count == 2
    assert result.manifest.summary.unknown_boundary_count == 2
    assert result.manifest.summary.missing_required_count == 2
    assert result.review_markdown_path.exists()
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(_manifest_schema()).validate(payload)
    pack = next(row for row in payload["source_artifacts"] if row["artifact_key"] == "pack")
    assert "sha256" not in pack
    assert "bytes" not in pack


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
    assert result.manifest.source_safety.status.value == "BLOCKED"
    assert result.manifest.source_safety.observed_flags.wallet_used is True
    assert result.manifest.summary.boundary_violation_count == 1
    pack = next(
        artifact for artifact in result.manifest.source_artifacts if artifact.artifact_key == "pack"
    )
    assert pack.status.value == "blocked"
    assert pack.error == "source boundary violation: wallet_used"


def test_build_strategy_review_detects_all_blocking_boundary_flags(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(
        tmp_path,
        wallet_used=True,
        signing_used=True,
        exchange_write_used=True,
        permits_live_order=True,
    )

    result = build_strategy_review(
        review_id="blocked-flags",
        out_dir=tmp_path / "data/strategy_reviews",
        pack_path=pack_path,
        validation_path=validation_path,
        created_at=CREATED_AT,
    )

    assert result.manifest.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    flags = result.manifest.source_safety.observed_flags
    assert flags.permits_live_order is True
    assert flags.wallet_used is True
    assert flags.signing_used is True
    assert flags.exchange_write_used is True


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
    assert result.manifest.source_safety.observed_flags.venue_write_used is True
    lifecycle = next(
        artifact
        for artifact in result.manifest.source_artifacts
        if artifact.artifact_key == "lifecycle_review"
    )
    assert lifecycle.status.value == "blocked"
    assert lifecycle.summary["boundary_violations"] == ["venue_write_used"]
    assert lifecycle.error == "source boundary violation: venue_write_used"


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
    assert pack.error
    assert "error" in pack.summary
    assert pack.bytes == pack_path.stat().st_size
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
    review_path = tmp_path / "data/strategy_reviews/same-id/review.md"
    manifest_path = tmp_path / "data/strategy_reviews/same-id/review_manifest.json"
    review_path.write_text("keep review\n", encoding="utf-8")
    manifest_path.write_text("keep manifest\n", encoding="utf-8")

    try:
        build_strategy_review(**kwargs)
    except StrategyReviewOutputExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing output error")
    assert review_path.read_text(encoding="utf-8") == "keep review\n"
    assert manifest_path.read_text(encoding="utf-8") == "keep manifest\n"


def test_build_strategy_review_replace_existing_preserves_unmanaged_files(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pack_path, validation_path = _write_required_artifacts(tmp_path)
    kwargs = {
        "review_id": "replace-id",
        "out_dir": tmp_path / "data/strategy_reviews",
        "pack_path": pack_path,
        "validation_path": validation_path,
        "created_at": CREATED_AT,
    }
    build_strategy_review(**kwargs)
    extra_path = tmp_path / "data/strategy_reviews/replace-id/operator-note.txt"
    extra_path.write_text("keep\n", encoding="utf-8")
    review_path = tmp_path / "data/strategy_reviews/replace-id/review.md"
    manifest_path = tmp_path / "data/strategy_reviews/replace-id/review_manifest.json"
    review_path.write_text("old review\n", encoding="utf-8")
    manifest_path.write_text("old manifest\n", encoding="utf-8")

    build_strategy_review(**kwargs, replace_existing=True)

    assert extra_path.read_text(encoding="utf-8") == "keep\n"
    assert "old review" not in review_path.read_text(encoding="utf-8")
    assert "old manifest" not in manifest_path.read_text(encoding="utf-8")
