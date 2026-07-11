from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.backtest_candidate_pack import (
    BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES,
    build_crypto_perp_backtest_candidate_pack,
)
from sis.crypto_perp.backtest_candidate_pack_models import (
    CryptoPerpBacktestCandidatePackDecision,
)
from sis.crypto_perp.backtest_candidate_pack_reports import decide_backtest_candidate
from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.edge_scorer import build_edge_score
from sis.crypto_perp.features import build_feature_pack
from sis.crypto_perp.source_availability import build_source_availability
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows
from .test_profit_readiness_local_automation import _event, _outcome, _schema, _write_json


runner = CliRunner()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_ready_inputs(tmp_path: Path) -> Path:
    event = _event()
    outcome = _outcome(event.event_id)
    _write_json(tmp_path / "event.json", event)
    _write_json(tmp_path / "outcome.json", outcome)
    source = build_source_availability(
        event=event,
        created_at="2026-06-21T07:00:00Z",
        available_sources={"bars": True, "ticker": True, "funding": True, "outcome": True},
        row_counts={"bars": 20, "ticker": 1, "funding": 1, "outcome": 1},
        source_metadata={
            "ticker": {
                "coverage_class": "snapshot",
                "coverage_end_ms": int(event.information_cutoff_at.timestamp() * 1000),
                "exchange": "bitget",
                "market_type": "linear_perp",
                "symbols": ["BTCUSDT"],
            }
        },
    )
    _write_json(tmp_path / "source_availability.json", source)
    return tmp_path


def _write_explicit_passing_guard(data_dir: Path) -> None:
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )
    rows_path = data_dir / "tournament_rows_v2.json"
    _write_json(rows_path, rows)
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        source_refs=[
            {
                "path": rows_path.as_posix(),
                "sha256": _file_sha256(rows_path),
                "schema_version": rows.schema_version,
            }
        ],
    ).model_copy(update={"guard_status": "PASS", "stop_reasons": []})
    _write_json(data_dir / "bias_guard.json", guard)


def test_candidate_missing_selected_action_row_requires_revision() -> None:
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
    )
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
    ).model_copy(update={"pbo_status": "COMPUTED_PASS"})
    backtest_summary = {
        "executed_trade_count": 1,
        "unknown_count": 0,
        "blocked_missing_action_row_count": 1,
        "total_result_usd": "1",
        "max_drawdown_usd": "0",
        "profit_robustness": {
            "peak_concurrent_positions": 1,
            "position_overlap_accounted": True,
        },
    }

    decision, reasons = decide_backtest_candidate(
        event_count=1,
        outcome_count=1,
        min_events=1,
        ledger={"summary": {"critical_missing_count": 0}},
        no_lookahead={"summary": {"failed_count": 0, "unverified_count": 0}},
        backtest={"summary": backtest_summary},
        stress={"summary": {**backtest_summary, "total_result_usd": "1"}},
        rolling={"status": "complete"},
        guard=guard,
    )

    assert decision == "BACKTEST_REVISE"
    assert "ACTION_ROWS_MISSING" in reasons


def test_candidate_rejects_blocked_guard_before_uncomputed_pbo() -> None:
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
    )
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("0.5"),
    )
    assert guard.guard_status == "BLOCKED"
    assert guard.pbo_status == "INPUT_THRESHOLD_MET"
    backtest_summary = {
        "executed_trade_count": 1,
        "unknown_count": 0,
        "blocked_missing_action_row_count": 0,
        "total_result_usd": "1",
        "max_drawdown_usd": "0",
        "profit_robustness": {
            "peak_concurrent_positions": 1,
            "position_overlap_accounted": True,
        },
    }

    decision, reasons = decide_backtest_candidate(
        event_count=1,
        outcome_count=1,
        min_events=2,
        ledger={"summary": {"critical_missing_count": 0}},
        no_lookahead={"summary": {"failed_count": 0, "unverified_count": 0}},
        backtest={"summary": backtest_summary},
        stress={"summary": {**backtest_summary, "total_result_usd": "1"}},
        rolling={"status": "complete"},
        guard=guard,
    )

    assert decision == "BACKTEST_REJECT"
    assert "BIAS_GUARD_BLOCKED" in reasons
    assert set(guard.stop_reasons).issubset(reasons)


def test_backtest_candidate_pack_writes_artifacts_and_rejects_current_guard_blocker(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    _write_explicit_passing_guard(data_dir)
    out_dir = tmp_path / "pack"

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=out_dir,
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )

    assert set(result.paths) == set(BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES)
    for path in result.paths.values():
        assert path.exists()
    assert result.decision.decision == "BACKTEST_REJECT"
    assert result.decision.summary["pbo_status"] == "INPUT_THRESHOLD_MET"
    assert "BIAS_GUARD_BLOCKED" in result.decision.reason_codes
    assert result.decision.evidence_grade_summary is not None
    assert (
        result.decision.evidence_grade_summary.strongest_evidence_level
        == "recomputed_minimal_simulated_estimate"
    )
    assert result.decision.evidence_grade_summary.actual_cash_used is False
    assert result.decision.evidence_grade_summary.profit_proven is False
    assert result.decision.evidence_grade_summary.permits_live_order is False
    assert result.decision.evidence_grade_summary.overall_grade == (
        "local_simulation_with_recomputed_minimal_artifacts"
    )
    assert "RECOMPUTED_MINIMAL_ARTIFACTS_PRESENT" in (
        result.decision.evidence_grade_summary.known_limits
    )

    assert result.decision.non_goal_flags["profit_proven"] is False
    assert result.decision.boundary.permits_live_order is False

    signal_rows = [
        json.loads(line)
        for line in (out_dir / "signal_rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert signal_rows[0]["selected_action"] == "CONTINUATION_LONG"
    assert signal_rows[0]["entry_allowed"] is True

    decision_payload = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
    schema = _schema("crypto_perp_backtest_candidate_pack.v1.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(decision_payload)


def test_backtest_candidate_pack_rejects_blocked_guard_when_sources_are_missing(
    tmp_path: Path,
) -> None:
    event = _event()
    _write_json(tmp_path / "event.json", event)
    _write_json(tmp_path / "outcome.json", _outcome(event.event_id))

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=tmp_path,
        out_dir=tmp_path / "pack",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    assert result.decision.decision == "BACKTEST_REJECT"
    assert "BIAS_GUARD_BLOCKED" in result.decision.reason_codes
    assert result.decision.evidence_grade_summary is not None
    assert (
        result.decision.evidence_grade_summary.strongest_evidence_level
        == "incomplete_local_artifact"
    )

    assert "CRITICAL_SIGNAL_SOURCE_MISSING" in result.decision.reason_codes
    assert "SELECTED_ACTION_UNKNOWN_DUE_TO_MISSING_SOURCE" in result.decision.reason_codes


def test_backtest_candidate_pack_grades_existing_artifact_only_pack_as_local_simulated(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    event = _event()
    outcome = _outcome(event.event_id)
    source = build_source_availability(
        event=event,
        created_at="2026-06-21T07:00:00Z",
        available_sources={"bars": True, "ticker": True, "funding": True, "outcome": True},
        row_counts={"bars": 20, "ticker": 1, "funding": 1, "outcome": 1},
    )
    feature = build_feature_pack(
        event=event,
        source_availability=source,
        created_at="2026-06-21T07:01:00Z",
    )
    edge = build_edge_score(
        feature_pack=feature,
        source_availability=source,
        created_at="2026-06-21T07:02:00Z",
    )
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )
    rows_path = data_dir / "tournament_rows_v2.json"
    _write_json(rows_path, rows)
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
        source_refs=[
            {
                "path": rows_path.as_posix(),
                "sha256": _file_sha256(rows_path),
                "schema_version": rows.schema_version,
            }
        ],
    )
    _write_json(data_dir / "feature_pack.json", feature)
    _write_json(data_dir / "edge_score.json", edge)
    _write_json(data_dir / "bias_guard.json", guard)

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack-existing",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    assert result.decision.evidence_grade_summary is not None
    assert result.decision.evidence_grade_summary.strongest_evidence_level == (
        "recomputed_minimal_simulated_estimate"
    )
    assert result.decision.evidence_grade_summary.existing_artifact_only is False
    assert result.decision.evidence_grade_summary.recomputed_minimal_artifact_count >= 1


def test_backtest_candidate_pack_recomputes_external_guard_and_uses_current_blockers(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )
    rows_path = data_dir / "tournament_rows_v2.json"
    _write_json(rows_path, rows)
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        source_refs=[
            {
                "path": rows_path.as_posix(),
                "sha256": f"sha256:{_file_sha256(rows_path)}",
                "schema_version": rows.schema_version,
            }
        ],
    ).model_copy(
        update={
            "guard_status": "BLOCKED",
            "stop_reasons": ["BIAS_GUARD_FAILED_test_guard"],
        }
    )
    _write_json(data_dir / "bias_guard.json", guard)

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack-blocked",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    assert result.decision.decision == "BACKTEST_REJECT"
    assert "BIAS_GUARD_BLOCKED" in result.decision.reason_codes
    assert "BIAS_GUARD_FAILED_profit_concentration_within_limit" in (result.decision.reason_codes)
    assert "BIAS_GUARD_FAILED_test_guard" not in result.decision.reason_codes
    assert result.decision.summary["bias_guard_origin"]["note"] == (
        "recomputed with current guard policy from selected tournament rows"
    )


def test_backtest_candidate_pack_recomputes_guard_from_inconsistent_warning_contract(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )
    rows_path = data_dir / "tournament_rows_v2.json"
    _write_json(rows_path, rows)
    guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        source_refs=[
            {
                "path": rows_path.as_posix(),
                "sha256": _file_sha256(rows_path),
                "schema_version": rows.schema_version,
            }
        ],
    )
    legacy_checks = [check.model_copy() for check in guard.checks]
    legacy_guard = guard.model_copy(
        update={
            "checks": legacy_checks,
            "guard_status": "BLOCKED",
            "stop_reasons": ["BIAS_GUARD_FAILED_stress_cash_non_negative"],
        }
    )
    _write_json(data_dir / "bias_guard.json", legacy_guard)

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack-contract",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    origin = result.decision.summary["bias_guard_origin"]
    assert origin["origin"] == "recomputed_minimal"
    assert (
        "BIAS_GUARD_FAILED_stress_cash_non_negative"
        not in result.decision.summary["bias_guard_stop_reasons"]
    )
    assert result.decision.summary["bias_guard_warning_codes"] == [
        "BIAS_GUARD_WARNING_stress_cash_non_negative"
    ]


def test_backtest_candidate_pack_recomputes_guard_when_rows_hash_does_not_match(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    outcome = _outcome(_event().event_id)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )
    rows_path = data_dir / "tournament_rows_v2.json"
    _write_json(rows_path, rows)
    stale_guard = build_bias_guard(
        rows=rows.rows,
        created_at="2026-06-21T07:04:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        source_refs=[
            {
                "path": rows_path.as_posix(),
                "sha256": "0" * 64,
                "schema_version": rows.schema_version,
            }
        ],
    )
    _write_json(data_dir / "bias_guard.json", stale_guard)

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack-lineage",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    origin = result.decision.summary["bias_guard_origin"]
    assert origin["origin"] == "recomputed_minimal"
    assert origin["note"] == "recomputed with current guard policy from selected tournament rows"


def test_backtest_candidate_pack_always_recomputes_derived_tournament_rows(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    outcome = _outcome(_event().event_id)
    existing_rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
    )
    _write_json(data_dir / "tournament_rows_v2.json", existing_rows)

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    origin = result.decision.summary["tournament_rows_origin"]
    assert origin == {
        "origin": "recomputed_minimal",
        "path": None,
        "note": "always recomputed from matured outcomes; derived rows are not trusted inputs",
    }


def test_backtest_candidate_pack_recomputes_rows_when_cost_assumptions_change(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    outcome = _outcome(_event().event_id)
    existing_rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-21T07:03:00Z",
        notional_usd=Decimal("100"),
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("2"),
    )
    _write_json(data_dir / "tournament_rows_v2.json", existing_rows)

    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack-high-slippage",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
        fee_rate=Decimal("0.0004"),
        funding_rate=Decimal("0.0001"),
        slippage_bps=Decimal("50"),
    )

    assert result.decision.summary["tournament_rows_origin"]["origin"] == "recomputed_minimal"
    persisted_rows = json.loads(
        (tmp_path / "pack-high-slippage/tournament_rows_v2.json").read_text(encoding="utf-8")
    )
    assert persisted_rows["summary"]["cost_assumptions"]["notional_usd"] == "100"
    assert persisted_rows["summary"]["cost_assumptions"]["slippage_bps"] == "50"
    continuation = next(
        row for row in persisted_rows["rows"] if row["action"] == "CONTINUATION_LONG"
    )
    assert Decimal(continuation["slippage_estimate_usd"]) == Decimal("0.5")


def test_backtest_candidate_pack_persists_exact_rows_and_guard(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    manifest_path = data_dir / "selection_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "crypto_perp_real_market_no_cash_sample.v1",
            "event_set": [_event().event_id],
        },
    )
    result = build_crypto_perp_backtest_candidate_pack(
        data_dir=data_dir,
        out_dir=tmp_path / "pack-audit",
        created_at="2026-06-21T08:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
        min_events_for_stability=1,
        fold_count=2,
    )

    assert "tournament_rows_v2.json" in result.paths
    assert "bias_guard.json" in result.paths
    rows_payload = json.loads(result.paths["tournament_rows_v2.json"].read_text(encoding="utf-8"))
    guard_payload = json.loads(result.paths["bias_guard.json"].read_text(encoding="utf-8"))
    assert guard_payload["event_set"] == sorted(rows_payload["event_set"])
    assert (
        guard_payload["source_refs"][0]["path"]
        == result.paths["tournament_rows_v2.json"].as_posix()
    )
    assert guard_payload["source_refs"][0]["sha256"].startswith("sha256:")
    assert (
        result.decision.artifact_paths["bias_guard.json"]
        == result.paths["bias_guard.json"].as_posix()
    )
    assert any(
        ref["path"] == manifest_path.as_posix()
        and ref["sha256"] == f"sha256:{_file_sha256(manifest_path)}"
        and ref["schema_version"] == "crypto_perp_real_market_no_cash_sample.v1"
        for ref in result.decision.source_refs
    )
    no_lookahead = json.loads(result.paths["no_lookahead_report.json"].read_text(encoding="utf-8"))
    recursive_checks = [
        check
        for check in no_lookahead["checks"]
        if check["check_id"] == "recursive_feature_warmup_absent"
    ]
    assert len(recursive_checks) == 1
    assert recursive_checks[0]["status"] == "pass"
    recursive_guard_checks = [
        check for check in guard_payload["checks"] if check["check_id"] == "recursive_warmup_absent"
    ]
    assert len(recursive_guard_checks) == 1
    assert recursive_guard_checks[0]["passed"] is True
    component_refs = result.decision.summary["pack_component_refs"]
    for name in (
        "signal_rows.jsonl",
        "data_availability_ledger.json",
        "tournament_rows_v2.json",
        "bias_guard.json",
        "backtest_result.json",
        "stress_result.json",
        "rolling_stability_result.json",
    ):
        artifact_path = result.paths[name]
        assert component_refs[name]["path"] == artifact_path.as_posix()
        assert component_refs[name]["sha256"] == f"sha256:{_file_sha256(artifact_path)}"


def test_backtest_candidate_pack_accepts_legacy_v1_decision_without_evidence_grade() -> None:
    payload = {
        "schema_version": "crypto_perp_backtest_candidate_pack.v1",
        "artifact_id": "legacy-artifact",
        "created_at": "2026-06-21T08:00:00Z",
        "producer": {"tool": "sis", "command": "crypto-perp-backtest-candidate-pack"},
        "source_refs": [],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
        "pack_id": "legacy-pack",
        "decision": "BACKTEST_COLLECT_MORE_DATA",
        "reason_codes": [],
        "event_count": 0,
        "outcome_count": 0,
        "artifact_paths": {},
        "summary": {},
        "non_goal_flags": {
            "actual_cash_used": False,
            "profit_proven": False,
            "actual_cash_readiness_claimed": False,
            "tiny_live_readiness_claimed": False,
            "live_trading_readiness_claimed": False,
            "wallet_or_signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "backtest_promote_to_live_available": False,
            "ml_or_llm_trade_decision_used": False,
        },
    }

    artifact = CryptoPerpBacktestCandidatePackDecision.model_validate(payload)

    assert artifact.evidence_grade_summary is None


def test_backtest_candidate_pack_rejects_zero_cost_assumptions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fee_rate must be positive"):
        build_crypto_perp_backtest_candidate_pack(
            data_dir=tmp_path,
            out_dir=tmp_path / "pack",
            created_at="2026-06-21T08:00:00Z",
            notional_usd=Decimal("100"),
            fee_rate=Decimal("0"),
        )
    with pytest.raises(ValueError, match="slippage_bps must be positive"):
        build_crypto_perp_backtest_candidate_pack(
            data_dir=tmp_path,
            out_dir=tmp_path / "pack",
            created_at="2026-06-21T08:00:00Z",
            notional_usd=Decimal("100"),
            slippage_bps=Decimal("0"),
        )


def test_backtest_candidate_pack_cli_rejects_holding_horizon_mismatch(
    tmp_path: Path,
) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    out_dir = tmp_path / "cli-pack"

    result = runner.invoke(
        app,
        [
            "crypto-perp-backtest-candidate-pack",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--min-events",
            "1",
            "--min-events-for-stability",
            "1",
            "--fold-count",
            "2",
            "--max-holding-minutes",
            "5",
        ],
    )

    assert result.exit_code == 2
    assert "max_holding_minutes=5 does not match actual outcome horizon" in result.stdout
    assert not (out_dir / "decision.json").exists()


def test_backtest_candidate_pack_cli_generates_pack(tmp_path: Path) -> None:
    data_dir = _write_ready_inputs(tmp_path / "data")
    _write_explicit_passing_guard(data_dir)
    out_dir = tmp_path / "cli-pack"

    result = runner.invoke(
        app,
        [
            "crypto-perp-backtest-candidate-pack",
            "--data-dir",
            str(data_dir),
            "--out",
            str(out_dir),
            "--min-events",
            "1",
            "--min-events-for-stability",
            "1",
            "--fold-count",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "profit_proven=false" in result.stdout
    assert "decision=BACKTEST_REJECT" in result.stdout
    assert (out_dir / "decision.json").exists()
    decision_payload = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
    assert decision_payload["evidence_grade_summary"]["strongest_evidence_level"] == (
        "recomputed_minimal_simulated_estimate"
    )
    assumptions_payload = json.loads(
        (out_dir / "execution_assumptions.json").read_text(encoding="utf-8")
    )
    assert assumptions_payload["fee_rate"] == "0.0004"
