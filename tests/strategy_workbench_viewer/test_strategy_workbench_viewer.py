from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_case_index.service import build_strategy_case_index
from sis.strategy_workbench_viewer.service import build_strategy_workbench_viewer


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _stage_decision(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_stage_decision.v1",
            "decision_id": "stage-001",
            "strategy_id": "ndx-breakout-001",
            "decision_status": "READY_FOR_PAPER_SMOKE_PLAN",
            "recommended_action": "BUILD_PAPER_SMOKE_PLAN",
            "live_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    )


def _case_lite(
    path: Path,
    *,
    strategy_id: str,
    case_id: str,
    updated_at: str,
    latest_status: str,
    open_actions: list[str] | None = None,
    blocked_reasons: list[str] | None = None,
    source_artifacts: list[dict] | None = None,
) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_case_lite.v1",
            "strategy_id": strategy_id,
            "case_id": case_id,
            "updated_at": updated_at,
            "producer": {"tool": "sis", "command": "strategy-case-lite-update"},
            "source_artifacts": source_artifacts or [],
            "timeline": [],
            "summary": {
                "artifact_count": len(source_artifacts or []) or 1,
                "timeline_count": len(source_artifacts or []) or 1,
                "latest_status": latest_status,
                "open_actions": open_actions or [],
                "blocked_reasons": blocked_reasons or [],
                "latest_source_hashes": {},
            },
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
        },
    )


def _unsafe_review(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Review <script>alert(1)</script>\n\n"
        "This markdown contains <img src=x onerror=alert(1)> and must be escaped.\n",
        encoding="utf-8",
    )
    return path


def _crypto_perp_tournament_gate(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_tournament_gate.v1",
            "gate_id": "gate-001",
            "report_id": "tournament-001",
            "gate_status": "NEEDS_ACTUAL_CASH",
            "recommended_action": "REBUILD_WITH_ACTUAL_CASH",
            "summary": {
                "gate_status": "NEEDS_ACTUAL_CASH",
                "proxy_gap_count": 1,
                "failed_condition_count": ["malformed count must not enter compact summary"],
            },
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )


def _crypto_perp_ready_tournament_gate(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_tournament_gate.v1",
            "gate_id": "gate-ready",
            "report_id": "tournament-ready",
            "gate_status": "READY_FOR_HUMAN_TINY_LIVE_REVIEW",
            "recommended_action": "PREPARE_TINY_LIVE_APPROVAL_PACKET",
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )


def _crypto_perp_proxy_tournament_report(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_tournament_report.v1",
            "report_id": "tournament-proxy",
            "tournament_status": "COMPLETE",
            "leader_action": "CONTINUATION_LONG",
            "primary_metric": "actual_cash_result_usd",
            "primary_metric_display_name": "before_cost_proxy_usd",
            "cash_metric_basis": "before_cost_proxy",
            "actual_cash": False,
            "event_count": 2,
            "leader_cash_metric_value_usd": "4",
            "leader_actual_cash_result_usd": None,
            "known_gaps": ["OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH"],
            "summary": {
                "report_id": "tournament-proxy",
                "tournament_status": "COMPLETE",
                "leader_action": "CONTINUATION_LONG",
                "primary_metric": "actual_cash_result_usd",
                "primary_metric_display_name": "before_cost_proxy_usd",
                "cash_metric_basis": "before_cost_proxy",
                "actual_cash": False,
                "event_count": 2,
                "leader_cash_metric_value_usd": "4",
                "leader_actual_cash_result_usd": None,
            },
        },
    )


def _crypto_perp_truth_cycle_status(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_truth_cycle_status.v1",
            "cycle_status": "MISSING_PROBE_AUDIT",
            "recommended_next_command": "uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>",
            "next_steps": [
                {
                    "step_id": "verify_artifact_path",
                    "purpose": "指定したartifact pathまたはrun directoryが正しいかを確認する。",
                    "command": "verify the specified artifact path before rerunning status",
                    "requires_explicit_approval": False,
                    "network_allowed": False,
                    "exchange_write_allowed": False,
                    "live_order_allowed": False,
                },
            ],
            "stage_checklist": [
                {
                    "stage_id": "probe_audit",
                    "status": "path_not_found",
                    "present": False,
                    "blocks_progress": True,
                    "artifact_path": "data/crypto_perp/inputs/missing_probe_audit.json",
                    "expected_cli_option": "--probe-audit",
                    "expected_artifact_hint": "crypto_perp_probe_audit.v1 JSON from crypto-perp-probe-audit",
                }
            ],
            "stop_reasons": [
                "PROBE_AUDIT_ARTIFACT_PATH_NOT_FOUND",
                "PROBE_AUDIT_REQUIRED_BEFORE_EVENT_REFRESH",
            ],
            "summary": {
                "cycle_status": "MISSING_PROBE_AUDIT",
                "human_summary": "指定された probe audit artifact が見つからないため、path または生成済みrun directoryを先に確認する。",
                "present_stage_count": 0,
                "missing_artifact_path_count": 1,
                "known_gap_count": 0,
                "stop_reason_count": 2,
            },
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )


def _crypto_perp_ready_truth_cycle_status(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_truth_cycle_status.v1",
            "cycle_status": "READY_FOR_HUMAN_TINY_LIVE_REVIEW",
            "recommended_next_command": "PREPARE_TINY_LIVE_APPROVAL_PACKET",
            "next_steps": [
                {
                    "step_id": "human_tiny_live_approval",
                    "purpose": "tiny live measurementへ進める前に別の明示承認を取る。",
                    "command": "STOP_FOR_SEPARATE_HUMAN_APPROVAL",
                    "requires_explicit_approval": True,
                    "network_allowed": False,
                    "exchange_write_allowed": False,
                    "live_order_allowed": False,
                }
            ],
            "stage_checklist": [],
            "stop_reasons": [],
            "summary": {
                "cycle_status": "READY_FOR_HUMAN_TINY_LIVE_REVIEW",
                "human_summary": "人間のtiny live承認準備に進める可能性があるが、live実行許可ではない。",
                "stage_checklist_blocker_count": 0,
            },
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )


def _input_feedback_review(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_input_contract_update_review.v1",
            "review_id": "proposal-runtime-review",
            "proposal_id": "proposal-runtime",
            "strategy_id": "ndx-breakout-001",
            "reviewed_at": "2026-06-22T09:10:00Z",
            "producer": {"tool": "sis", "command": "strategy-input-feedback-proposal-review"},
            "reviewer": "operator-a",
            "decision": "HOLD",
            "rationale": "Hold before any manual contract update.",
            "approved_change_ids": [],
            "required_actions": [
                "Choose a human-approved manual contract update target before applying changes."
            ],
            "source_proposal": {
                "proposal_path": "data/strategy_input_feedback/proposal-runtime.json",
                "proposal_sha256": "sha256:" + "a" * 64,
                "proposal_id": "proposal-runtime",
                "proposal_status": "READY_FOR_HUMAN_REVIEW",
                "proposed_change_ids": ["runtime-001"],
                "proposed_change_count": 1,
                "auto_applied": False,
                "direct_contract_edit_allowed": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
            },
            "manual_contract_update_input_allowed": False,
            "requires_human_contract_update": True,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
            "feedback_boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "permits_wallet": False,
                "permits_signing": False,
                "permits_exchange_write": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
                "auto_applied": False,
                "direct_contract_edit_allowed": False,
            },
        },
    )


def _input_feedback_proposal(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_input_contract_update_proposal.v1",
            "proposal_id": "proposal-runtime",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-22T09:05:00Z",
            "producer": {"tool": "sis", "command": "strategy-input-feedback-proposal-build"},
            "status": "READY_FOR_HUMAN_REVIEW",
            "source_artifacts": [
                {
                    "artifact_kind": "runtime_observation",
                    "path": "data/strategy_runtime_observation/obs.json",
                    "sha256": "sha256:" + "a" * 64,
                    "schema_version": "strategy_runtime_observation_manifest.v1",
                }
            ],
            "proposed_changes": [
                {
                    "change_id": "runtime-001",
                    "target_section": "execution_reality",
                    "recommendation": "Review runtime observation evidence.",
                    "evidence_summary": (
                        "runtime ingest_status=INGESTED; no_fill_count=0; "
                        "blocked_count=0; max_observed_quote_age_ms=1048982067; "
                        "max_observed_spread_bps=0.332474441027346; "
                        "pnl_available=False; pnl_unavailable_reason=ledger rows do not "
                        "include realized_pnl_usd, paper_pnl_usd, or pnl_usd"
                    ),
                    "source_reason": "runtime_observation:INGESTED",
                    "requires_human_review": True,
                }
            ],
            "blocked_reasons": [],
            "requires_human_review": True,
            "auto_applied": False,
            "direct_contract_edit_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
            "feedback_boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "permits_wallet": False,
                "permits_signing": False,
                "permits_exchange_write": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
                "auto_applied": False,
                "direct_contract_edit_allowed": False,
            },
        },
    )


def _runtime_observation_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_runtime_observation_manifest.v1",
            "strategy_id": "ndx_open_gap_residual_v1",
            "created_at": "2026-06-22T10:00:00Z",
            "producer": {"tool": "sis", "command": "strategy-runtime-observation-ingest"},
            "ingest_status": "INGESTED",
            "summary": {
                "block_reasons": {},
                "blocked_count": 0,
                "filled_notional_usd_total": 20000.0,
                "first_observed_at": "2026-06-17T11:07:10.330218+00:00",
                "last_observed_at": "2026-06-17T11:13:45.220224+00:00",
                "ledger_entry_count": 20,
                "max_observed_quote_age_ms": 1048982067,
                "max_observed_spread_bps": 0.332474441027346,
                "no_fill_count": 0,
                "order_lifecycle_counts": {"paper_filled": 20},
                "paper_fill_count": 20,
                "paper_order_count": 20,
                "pnl_available": False,
                "pnl_unavailable_reason": (
                    "ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd"
                ),
                "status_counts": {"paper_filled": 20},
                "unique_intent_count": 1,
                "unique_symbol_count": 1,
            },
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
        },
    )


def _strategy_authoring_backtest_result(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_authoring_backtest_result.v1",
            "strategy_id": "trend_pullback_user_v1",
            "paper_only": True,
            "live_order_submitted": False,
            "summary": {
                "backtest_passed": True,
                "aggregate_metrics": {
                    "trade_count": 7,
                    "total_return": 0.004662409768745324,
                    "max_drawdown": 0.0,
                },
                "capital": {
                    "net_pnl_usd": 46.62409768745324,
                    "ending_equity_usd": 10046.624097687452,
                    "max_drawdown_loss_usd": 0.0,
                },
                "executed_count": 7,
                "blocked_count": 0,
            },
        },
    )


def _strategy_backtest_pack_validation(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_backtest_pack_validation.v1",
            "decision": "PASS",
            "paper_only": True,
            "live_order_submitted": False,
            "summary": {
                "check_count": 206,
                "passed_count": 206,
                "failed_count": 0,
                "locked_dependency_added": False,
                "external_framework_policy_decision": (
                    "complete_without_locked_external_dependency"
                ),
            },
        },
    )


def _strategy_backtest_pack(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_backtest_pack.v1",
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "artifacts": {f"artifact_{index}": {"exists": True} for index in range(45)},
            "summary": {
                "capital": {
                    "net_pnl_usd": 46.62409768745324,
                    "ending_equity_usd": 10046.624097687452,
                    "max_drawdown_loss_usd": 0.0,
                },
                "external_engine_run": False,
                "external_result_count": 9,
                "suite_method_count": 5,
                "suite_passed_count": 5,
                "suite_run_count": 5,
            },
            "external_framework_policy": {
                "decision": "complete_without_locked_external_dependency",
                "external_adapters_required_for_completion": False,
                "locked_dependency_added": False,
                "standard_engine": "strategy_authoring_native",
            },
        },
    )


def _strategy_backtest_suite_result(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_backtest_suite_result.v1",
            "suite_id": "trend_pullback_backtest_suite_v1",
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "aggregate": {
                "run_count": 5,
                "passed_count": 5,
                "failed_count": 0,
                "trade_count": 35,
                "total_return": 0.023312048843726618,
                "cost_drag_bps": 35.0,
            },
            "method_matrix": {
                "method_count": 5,
                "counts_by_method": {
                    "single_window": 1,
                    "walk_forward:trading_day": 1,
                },
            },
            "best_run": {
                "run_id": "000-single_window_120m",
                "method_id": "single_window",
                "case_id": "single_window_120m",
                "summary": {
                    "aggregate_metrics": {
                        "trade_count": 7,
                        "total_return": 0.004662409768745324,
                    }
                },
            },
        },
    )


def _strategy_backtest_comparison(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_backtest_comparison.v1",
            "comparison_id": "sha256:7d6c82dc19a0296565effedc365817451fcb7fad73cd6018ae75a92993037803",
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "method_results": [{}, {}],
            "external_results": [{} for _ in range(9)],
            "framework_adapters": [{} for _ in range(9)],
            "native_result": {
                "strategy_id": "trend_pullback_user_v1",
                "trade_count": 7,
                "total_return": 0.004662409768745324,
                "backtest_passed": True,
            },
            "comparison_diagnostics": {
                "suite_best_runs": [
                    {
                        "method_id": "single_window",
                        "case_id": "single_window_120m",
                        "total_return": 0.004662409768745324,
                        "trade_count": 7,
                    }
                ],
                "suite_failed_runs": [],
                "threshold_failures": [],
                "weakest_eras": [
                    {
                        "era": "2026-01-05",
                        "total_return": 0.0019993404303773055,
                        "trade_count": 3,
                    }
                ],
            },
            "portfolio_comparison": {"framework_id": "bt", "run_status": "skipped"},
            "metric_extension": {
                "framework_id": "empyrical_reloaded",
                "metric_status": "skipped",
            },
            "report_extension": {"framework_id": "quantstats", "report_status": "skipped"},
        },
    )


def _malformed_crypto_perp_truth_cycle_status(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_truth_cycle_status.v1",
            "cycle_status": "MISSING_PROBE_AUDIT",
            "next_steps": [
                {
                    "step_id": "bad_network_permission",
                    "purpose": "malformed input must not grant network permission.",
                    "command": "bad command",
                    "requires_explicit_approval": False,
                    "network_allowed": True,
                    "exchange_write_allowed": False,
                    "live_order_allowed": False,
                },
            ],
            "summary": {"cycle_status": "MISSING_PROBE_AUDIT"},
            "permits_live_order": False,
            "exchange_write_used": False,
        },
    )


def _strategy_daily_brief(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_daily_brief.v1",
            "data_dir": "data/crypto_perp/truth_cycle_dogfood_check",
            "generated_at": "2026-06-21T11:02:25Z",
            "producer": {"tool": "sis", "command": "strategy-daily-brief"},
            "live_allowed": False,
            "paper_execution_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
            "summary": {
                "scanned_json_count": 3,
                "total_item_count": 1,
                "broken_artifact_count": 0,
                "pending_human_review_count": 0,
                "crypto_perp_gate_follow_up_count": 0,
                "crypto_perp_truth_cycle_follow_up_count": 1,
                "normal_paper_gap_count": 0,
                "drift_review_needed_count": 0,
                "learning_request_pending_count": 0,
                "boundary_violation_count": 0,
            },
            "items": [
                {
                    "category": "crypto_perp_truth_cycle_follow_up",
                    "severity": "warning",
                    "status": "MISSING_PROBE_AUDIT",
                    "schema_version": "crypto_perp_truth_cycle_status.v1",
                    "action": "uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>",
                    "reason": "crypto perp truth-cycle follow-up: uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>",
                    "path": "data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json",
                    "sha256": "sha256:22505768a896e3f89d98c2e84da721192f1e500fd033b4333631f46a01bff20e",
                }
            ],
            "source_artifacts": [
                {
                    "path": "data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json",
                    "schema_version": "crypto_perp_truth_cycle_status.v1",
                    "sha256": "sha256:22505768a896e3f89d98c2e84da721192f1e500fd033b4333631f46a01bff20e",
                }
            ],
        },
    )


def test_strategy_workbench_viewer_builds_schema_valid_static_html(tmp_path: Path) -> None:
    result = build_strategy_workbench_viewer(
        artifacts=[
            _stage_decision(tmp_path / "data/strategy_stage/stage.json"),
            _crypto_perp_tournament_gate(tmp_path / "data/crypto_perp/tournament_gate/gate.json"),
            _crypto_perp_truth_cycle_status(
                tmp_path / "data/crypto_perp/truth_cycle_status/status.json"
            ),
            _unsafe_review(tmp_path / "data/strategy_reviews/review.md"),
        ],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    invalid_payload = json.loads(json.dumps(payload))
    invalid_payload["source_artifacts"][2]["summary"]["first_stage_blocker"] = ["probe_audit"]
    assert any(
        list(error.path)[-2:] == ["summary", "first_stage_blocker"]
        for error in Draft202012Validator(schema).iter_errors(invalid_payload)
    )

    assert payload["schema_version"] == "strategy_workbench_viewer.v1"
    assert payload["artifact_count"] == 4
    assert payload["paper_execution_allowed"] is False
    assert payload["live_allowed"] is False
    assert payload["source_artifacts"][0]["status"] == "READY_FOR_PAPER_SMOKE_PLAN"
    assert payload["source_artifacts"][1]["status"] == "NEEDS_ACTUAL_CASH"
    assert payload["source_artifacts"][1]["summary"]["proxy_gap_count"] == 1
    assert "failed_condition_count" not in payload["source_artifacts"][1]["summary"]
    assert payload["source_artifacts"][2]["status"] == "MISSING_PROBE_AUDIT"
    assert payload["source_artifacts"][2]["summary"]["stop_reason_count"] == 2
    assert payload["source_artifacts"][2]["summary"]["missing_artifact_path_count"] == 1
    assert payload["source_artifacts"][2]["summary"]["first_next_step"] == "verify_artifact_path"
    assert payload["source_artifacts"][2]["summary"]["first_stage_blocker"] == "probe_audit"
    assert (
        payload["source_artifacts"][2]["summary"]["first_stage_blocker_expected_cli_option"]
        == "--probe-audit"
    )
    assert (
        payload["source_artifacts"][2]["summary"]["first_stage_blocker_expected_artifact_hint"]
        == "crypto_perp_probe_audit.v1 JSON from crypto-perp-probe-audit"
    )
    assert (
        payload["source_artifacts"][2]["summary"]["first_next_step_command"]
        == "verify the specified artifact path before rerunning status"
    )
    assert payload["source_artifacts"][2]["summary"]["first_next_step_live_order_allowed"] is False
    assert (
        payload["source_artifacts"][2]["summary"]["first_stop_reason"]
        == "PROBE_AUDIT_ARTIFACT_PATH_NOT_FOUND"
    )
    assert (
        "path または生成済みrun directory"
        in payload["source_artifacts"][2]["summary"]["human_summary"]
    )

    html = result.html_path.read_text(encoding="utf-8")
    HTMLParser().feed(html)
    assert "Strategy Workbench Viewer" in html
    assert "paper / live 実行許可ではありません" in html
    assert "PROBE_AUDIT_ARTIFACT_PATH_NOT_FOUND" in html
    assert "verify_artifact_path" in html
    assert "first_stage_blocker" in html
    assert "--probe-audit" in html
    assert "first_next_step_live_order_allowed" in html
    assert "path または生成済みrun directory" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_strategy_workbench_viewer_summarizes_non_actual_tournament_report(
    tmp_path: Path,
) -> None:
    result = build_strategy_workbench_viewer(
        artifacts=[
            _crypto_perp_proxy_tournament_report(
                tmp_path / "data/crypto_perp/tournament/tournament_report.json"
            )
        ],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    source = payload["source_artifacts"][0]
    assert source["status"] == "COMPLETE"
    assert source["summary"]["cash_metric_basis"] == "before_cost_proxy"
    assert source["summary"]["primary_metric_display_name"] == "before_cost_proxy_usd"
    assert source["summary"]["actual_cash"] is False
    assert source["summary"]["leader_cash_metric_value_usd"] == "4"
    assert "leader_actual_cash_result_usd" not in source["summary"]

    html = result.html_path.read_text(encoding="utf-8")
    assert "cash_metric_basis" in html
    assert "before_cost_proxy" in html
    assert "actual_cash" in html


def test_strategy_workbench_viewer_summarizes_strategy_daily_brief_follow_up(
    tmp_path: Path,
) -> None:
    brief = _strategy_daily_brief(
        tmp_path / "data/crypto_perp/reports/strategy_daily_brief/strategy_daily_brief.json"
    )

    result = build_strategy_workbench_viewer(
        artifacts=[brief],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)

    source = payload["source_artifacts"][0]
    assert source["schema_version"] == "strategy_daily_brief.v1"
    assert source["summary"]["scanned_json_count"] == 3
    assert source["summary"]["total_item_count"] == 1
    assert source["summary"]["broken_artifact_count"] == 0
    assert source["summary"]["crypto_perp_truth_cycle_follow_up_count"] == 1
    assert source["summary"]["normal_paper_gap_count"] == 0
    assert source["summary"]["drift_review_needed_count"] == 0
    assert source["summary"]["learning_request_pending_count"] == 0
    assert source["summary"]["paper_execution_allowed"] is False
    assert source["summary"]["live_allowed"] is False
    assert source["summary"]["first_brief_item_category"] == "crypto_perp_truth_cycle_follow_up"
    assert source["summary"]["first_brief_item_severity"] == "warning"
    assert source["summary"]["first_brief_item_status"] == "MISSING_PROBE_AUDIT"
    assert (
        source["summary"]["first_brief_item_schema_version"] == "crypto_perp_truth_cycle_status.v1"
    )
    assert source["summary"]["first_brief_item_action"] == (
        "uv run sis crypto-perp-probe-audit --probe <provider_probe.json> --out <probe-audit-dir>"
    )
    assert source["summary"]["first_brief_item_reason"] == (
        "crypto perp truth-cycle follow-up: uv run sis crypto-perp-probe-audit "
        "--probe <provider_probe.json> --out <probe-audit-dir>"
    )
    assert source["summary"]["first_brief_item_path"] == (
        "data/crypto_perp/truth_cycle_dogfood_check/truth_cycle_status/truth_cycle_status.json"
    )

    html = result.html_path.read_text(encoding="utf-8")
    assert "crypto_perp_truth_cycle_follow_up_count" in html
    assert "first_brief_item_action" in html
    assert "MISSING_PROBE_AUDIT" in html
    assert "&lt;provider_probe.json&gt;" in html


def test_strategy_workbench_viewer_drops_true_permission_like_next_step_flags(
    tmp_path: Path,
) -> None:
    result = build_strategy_workbench_viewer(
        artifacts=[
            _malformed_crypto_perp_truth_cycle_status(
                tmp_path / "data/crypto_perp/truth_cycle_status/status.json"
            ),
        ],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    summary = payload["source_artifacts"][0]["summary"]
    assert summary["first_next_step"] == "bad_network_permission"
    assert "first_next_step_network_allowed" not in summary
    assert summary["first_next_step_exchange_write_allowed"] is False
    assert summary["first_next_step_live_order_allowed"] is False


def test_strategy_workbench_viewer_marks_human_tiny_live_review_as_approval_boundary(
    tmp_path: Path,
) -> None:
    result = build_strategy_workbench_viewer(
        artifacts=[
            _crypto_perp_ready_tournament_gate(
                tmp_path / "data/crypto_perp/tournament_gate/gate.json"
            ),
            _crypto_perp_ready_truth_cycle_status(
                tmp_path / "data/crypto_perp/truth_cycle_status/status.json"
            ),
        ],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    boundary = (
        "separate human approval is required before any tiny live measurement; "
        "this is not live execution permission"
    )
    gate_summary = payload["source_artifacts"][0]["summary"]
    truth_summary = payload["source_artifacts"][1]["summary"]
    assert gate_summary["approval_boundary"] == boundary
    assert truth_summary["approval_boundary"] == boundary
    assert truth_summary["first_next_step_requires_explicit_approval"] is True
    assert truth_summary["first_next_step_live_order_allowed"] is False

    html = result.html_path.read_text(encoding="utf-8")
    assert boundary in html
    assert '<span class="badge warn">READY_FOR_HUMAN_TINY_LIVE_REVIEW</span>' in html
    assert '<span class="badge good">READY_FOR_HUMAN_TINY_LIVE_REVIEW</span>' not in html


def test_strategy_workbench_viewer_scans_data_dir(tmp_path: Path) -> None:
    _stage_decision(tmp_path / "data/a/stage.json")
    _crypto_perp_tournament_gate(tmp_path / "data/a/gate.json")
    _crypto_perp_truth_cycle_status(tmp_path / "data/a/truth_cycle_status.json")
    _unsafe_review(tmp_path / "data/b/review.md")

    result = build_strategy_workbench_viewer(
        artifacts=None,
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    assert result.manifest.artifact_count == 4
    assert result.html_path.exists()


def test_strategy_workbench_viewer_summarizes_strategy_case_index(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    case = _case_lite(
        tmp_path / "data/strategy_cases/ndx-breakout-001/case-a.json",
        strategy_id="ndx-breakout-001",
        case_id="case-a",
        updated_at="2026-06-22T09:00:00Z",
        latest_status="READY_FOR_HUMAN_REVIEW",
        open_actions=["REVISE_STRATEGY"],
        blocked_reasons=["runtime_no_fill_rate_within_limit"],
    )
    index = build_strategy_case_index(
        case_paths=[case],
        data_dir=None,
        out_dir=tmp_path / "data/strategy_case_index",
        index_id="viewer-index",
    )

    result = build_strategy_workbench_viewer(
        artifacts=[index.index_path],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    assert payload["source_artifacts"][0]["status"] == "READY_FOR_HUMAN_REVIEW"
    summary = payload["source_artifacts"][0]["summary"]
    assert summary["index_id"] == "viewer-index"
    assert summary["case_count"] == 1
    assert summary["strategy_count"] == 1
    assert summary["latest_status"] == "READY_FOR_HUMAN_REVIEW"
    assert summary["latest_case_path"] == "data/strategy_cases/ndx-breakout-001/case-a.json"
    assert summary["first_open_action"] == "REVISE_STRATEGY"
    assert summary["first_blocked_reason"] == "runtime_no_fill_rate_within_limit"
    assert summary["case_index_source_hash"].startswith("sha256:")

    html = result.html_path.read_text(encoding="utf-8")
    assert "case_count" in html
    assert "strategy_count" in html
    assert '<span class="badge warn">READY_FOR_HUMAN_REVIEW</span>' in html
    assert "READY_FOR_HUMAN_REVIEW" in html
    assert "REVISE_STRATEGY" in html
    assert "runtime_no_fill_rate_within_limit" in html


def test_strategy_workbench_viewer_uses_case_lite_latest_status_as_status_badge(
    tmp_path: Path,
) -> None:
    case = _case_lite(
        tmp_path / "data/strategy_cases/ndx-breakout-001/case-a.json",
        strategy_id="ndx-breakout-001",
        case_id="case-a",
        updated_at="2026-06-22T09:00:00Z",
        latest_status="READY_FOR_HUMAN_REVIEW",
        open_actions=["REVISE_STRATEGY"],
        blocked_reasons=["runtime_no_fill_rate_within_limit"],
        source_artifacts=[
            {
                "artifact_type": "strategy_backtest_pack_validation",
                "path": "data/research/backtest_pack/strategy_backtest_pack_validation.json",
                "schema_version": "strategy_backtest_pack_validation.v1",
                "sha256": "sha256:0ffbc5d4e2af667c5a8a792274d1e7ca033fbdec24212d857687ef03a26147b6",
            },
            {
                "artifact_type": "strategy_review_manifest",
                "path": "data/strategy_reviews/current/review_manifest.json",
                "schema_version": "strategy_review_manifest.v1",
                "sha256": "sha256:0bee2b89c6bbc7eb05ef2d0be2b0972a65cfc4d9d23b11a95569d12774f0bb21",
            },
        ],
    )

    result = build_strategy_workbench_viewer(
        artifacts=[case],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    assert payload["source_artifacts"][0]["status"] == "READY_FOR_HUMAN_REVIEW"
    assert payload["source_artifacts"][0]["summary"]["latest_status"] == "READY_FOR_HUMAN_REVIEW"
    assert payload["source_artifacts"][0]["summary"]["artifact_count"] == 2
    assert payload["source_artifacts"][0]["summary"]["timeline_count"] == 2
    assert (
        payload["source_artifacts"][0]["summary"]["first_source_artifact_type"]
        == "strategy_backtest_pack_validation"
    )
    assert (
        payload["source_artifacts"][0]["summary"]["first_source_artifact_hash"]
        == "sha256:0ffbc5d4e2af667c5a8a792274d1e7ca033fbdec24212d857687ef03a26147b6"
    )
    assert (
        payload["source_artifacts"][0]["summary"]["first_source_artifact_path"]
        == "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    )
    assert payload["source_artifacts"][0]["summary"]["first_open_action"] == "REVISE_STRATEGY"
    assert (
        payload["source_artifacts"][0]["summary"]["first_blocked_reason"]
        == "runtime_no_fill_rate_within_limit"
    )

    html = result.html_path.read_text(encoding="utf-8")
    assert '<span class="badge warn">READY_FOR_HUMAN_REVIEW</span>' in html
    assert "artifact_count" in html
    assert "first_source_artifact_type" in html
    assert "strategy_backtest_pack_validation" in html
    assert "first_open_action" in html
    assert "runtime_no_fill_rate_within_limit" in html
    assert '<span class="badge neutral">n/a</span>' not in html


def test_strategy_workbench_viewer_uses_input_feedback_review_decision_as_status_badge(
    tmp_path: Path,
) -> None:
    review = _input_feedback_review(
        tmp_path / "data/strategy_input_feedback/proposal-runtime-review.json"
    )

    result = build_strategy_workbench_viewer(
        artifacts=[review],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    source = payload["source_artifacts"][0]
    assert source["status"] == "HOLD"
    assert source["summary"]["decision"] == "HOLD"
    assert source["summary"]["proposal_id"] == "proposal-runtime"
    assert source["summary"]["review_id"] == "proposal-runtime-review"
    assert source["summary"]["source_proposal_status"] == "READY_FOR_HUMAN_REVIEW"
    assert source["summary"]["approved_change_count"] == 0
    assert source["summary"]["required_action_count"] == 1
    assert source["summary"]["manual_contract_update_input_allowed"] is False
    assert source["summary"]["requires_human_contract_update"] is True
    assert source["summary"]["direct_contract_edit_allowed"] is False
    assert source["summary"]["auto_applied"] is False
    assert source["summary"]["paper_execution_allowed"] is False
    assert source["summary"]["live_allowed"] is False

    html = result.html_path.read_text(encoding="utf-8")
    assert '<span class="badge warn">HOLD</span>' in html
    assert "manual_contract_update_input_allowed" in html
    assert '<span class="badge neutral">n/a</span>' not in html


def test_strategy_workbench_viewer_summarizes_input_feedback_proposal_evidence(
    tmp_path: Path,
) -> None:
    proposal = _input_feedback_proposal(
        tmp_path / "data/strategy_input_feedback/proposal-runtime.json"
    )

    result = build_strategy_workbench_viewer(
        artifacts=[proposal],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    source = payload["source_artifacts"][0]
    assert source["status"] == "READY_FOR_HUMAN_REVIEW"
    assert source["summary"]["proposal_id"] == "proposal-runtime"
    assert source["summary"]["proposed_change_count"] == 1
    assert source["summary"]["first_proposed_change_target_section"] == "execution_reality"
    assert source["summary"]["first_proposed_change_source_reason"] == (
        "runtime_observation:INGESTED"
    )
    assert (
        "max_observed_quote_age_ms=1048982067"
        in (source["summary"]["first_proposed_change_evidence_summary"])
    )
    assert "pnl_available=False" in source["summary"]["first_proposed_change_evidence_summary"]
    assert (
        "ledger rows do not include realized_pnl_usd"
        in (source["summary"]["first_proposed_change_evidence_summary"])
    )

    html = result.html_path.read_text(encoding="utf-8")
    assert '<span class="badge warn">READY_FOR_HUMAN_REVIEW</span>' in html
    assert "first_proposed_change_evidence_summary" in html
    assert "max_observed_quote_age_ms=1048982067" in html


def test_strategy_workbench_viewer_summarizes_runtime_observation_execution_reality(
    tmp_path: Path,
) -> None:
    observation = _runtime_observation_manifest(
        tmp_path / "data/strategy_runtime_observation/strategy_runtime_observation_manifest.json"
    )

    result = build_strategy_workbench_viewer(
        artifacts=[observation],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    source = payload["source_artifacts"][0]
    assert source["status"] == "INGESTED"
    assert source["summary"]["strategy_id"] == "ndx_open_gap_residual_v1"
    assert source["summary"]["ledger_entry_count"] == 20
    assert source["summary"]["paper_order_count"] == 20
    assert source["summary"]["paper_fill_count"] == 20
    assert source["summary"]["no_fill_count"] == 0
    assert source["summary"]["blocked_count"] == 0
    assert source["summary"]["unique_intent_count"] == 1
    assert source["summary"]["unique_symbol_count"] == 1
    assert source["summary"]["filled_notional_usd_total"] == 20000.0
    assert source["summary"]["max_observed_quote_age_ms"] == 1048982067
    assert source["summary"]["max_observed_spread_bps"] == 0.332474441027346
    assert source["summary"]["pnl_available"] is False
    assert (
        source["summary"]["pnl_unavailable_reason"]
        == "ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd"
    )
    assert source["summary"]["first_observed_at"] == "2026-06-17T11:07:10.330218+00:00"
    assert source["summary"]["last_observed_at"] == "2026-06-17T11:13:45.220224+00:00"

    html = result.html_path.read_text(encoding="utf-8")
    assert '<span class="badge neutral">INGESTED</span>' in html
    assert "max_observed_quote_age_ms" in html
    assert "1048982067" in html
    assert "pnl_available" in html
    assert "ledger rows do not include realized_pnl_usd" in html


def test_strategy_workbench_viewer_summarizes_backtest_result_and_pack_validation(
    tmp_path: Path,
) -> None:
    backtest = _strategy_authoring_backtest_result(
        tmp_path / "data/research/strategy_backtest_metrics.json"
    )
    validation = _strategy_backtest_pack_validation(
        tmp_path / "data/research/backtest_pack/strategy_backtest_pack_validation.json"
    )

    result = build_strategy_workbench_viewer(
        artifacts=[backtest, validation],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)

    backtest_source = payload["source_artifacts"][0]
    assert backtest_source["summary"]["strategy_id"] == "trend_pullback_user_v1"
    assert backtest_source["summary"]["backtest_passed"] is True
    assert backtest_source["summary"]["trade_count"] == 7
    assert backtest_source["summary"]["total_return"] == 0.004662409768745324
    assert backtest_source["summary"]["net_pnl_usd"] == 46.62409768745324
    assert backtest_source["summary"]["max_drawdown"] == 0.0
    assert backtest_source["summary"]["paper_only"] is True
    assert backtest_source["summary"]["live_order_submitted"] is False

    validation_source = payload["source_artifacts"][1]
    assert validation_source["status"] == "PASS"
    assert validation_source["summary"]["decision"] == "PASS"
    assert validation_source["summary"]["check_count"] == 206
    assert validation_source["summary"]["passed_count"] == 206
    assert validation_source["summary"]["failed_count"] == 0
    assert validation_source["summary"]["locked_dependency_added"] is False
    assert (
        validation_source["summary"]["external_framework_policy_decision"]
        == "complete_without_locked_external_dependency"
    )

    html = result.html_path.read_text(encoding="utf-8")
    assert "backtest_passed" in html
    assert "trade_count" in html
    assert "net_pnl_usd" in html
    assert "locked_dependency_added" in html
    assert "complete_without_locked_external_dependency" in html


def test_strategy_workbench_viewer_summarizes_backtest_pack_suite_and_comparison(
    tmp_path: Path,
) -> None:
    pack = _strategy_backtest_pack(tmp_path / "data/research/backtest_pack/pack.json")
    suite = _strategy_backtest_suite_result(tmp_path / "data/research/backtest_suite/suite.json")
    comparison = _strategy_backtest_comparison(
        tmp_path / "data/research/backtest_compare/comparison.json"
    )

    result = build_strategy_workbench_viewer(
        artifacts=[pack, suite, comparison],
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)

    pack_summary = payload["source_artifacts"][0]["summary"]
    assert pack_summary["pack_artifact_count"] == 45
    assert pack_summary["suite_method_count"] == 5
    assert pack_summary["suite_run_count"] == 5
    assert pack_summary["suite_passed_count"] == 5
    assert pack_summary["external_result_count"] == 9
    assert pack_summary["external_engine_run"] is False
    assert pack_summary["net_pnl_usd"] == 46.62409768745324
    assert pack_summary["external_framework_policy_decision"] == (
        "complete_without_locked_external_dependency"
    )
    assert pack_summary["standard_engine"] == "strategy_authoring_native"
    assert pack_summary["locked_dependency_added"] is False
    assert pack_summary["external_adapters_required_for_completion"] is False

    suite_summary = payload["source_artifacts"][1]["summary"]
    assert suite_summary["suite_id"] == "trend_pullback_backtest_suite_v1"
    assert suite_summary["method_count"] == 5
    assert suite_summary["run_count"] == 5
    assert suite_summary["passed_count"] == 5
    assert suite_summary["failed_count"] == 0
    assert suite_summary["trade_count"] == 35
    assert suite_summary["total_return"] == 0.023312048843726618
    assert suite_summary["cost_drag_bps"] == 35.0
    assert suite_summary["best_run_id"] == "000-single_window_120m"
    assert suite_summary["best_run_method_id"] == "single_window"
    assert suite_summary["best_run_total_return"] == 0.004662409768745324
    assert suite_summary["best_run_trade_count"] == 7

    comparison_summary = payload["source_artifacts"][2]["summary"]
    assert comparison_summary["comparison_id"].startswith("sha256:")
    assert comparison_summary["method_result_count"] == 2
    assert comparison_summary["external_result_count"] == 9
    assert comparison_summary["framework_adapter_count"] == 9
    assert comparison_summary["native_total_return"] == 0.004662409768745324
    assert comparison_summary["native_trade_count"] == 7
    assert comparison_summary["suite_failed_run_count"] == 0
    assert comparison_summary["threshold_failure_count"] == 0
    assert comparison_summary["suite_best_run_method_id"] == "single_window"
    assert comparison_summary["weakest_era"] == "2026-01-05"
    assert comparison_summary["weakest_era_total_return"] == 0.0019993404303773055
    assert comparison_summary["portfolio_run_status"] == "skipped"
    assert comparison_summary["metric_status"] == "skipped"
    assert comparison_summary["report_status"] == "skipped"

    html = result.html_path.read_text(encoding="utf-8")
    assert "pack_artifact_count" in html
    assert "suite_best_run_method_id" in html
    assert "weakest_era_total_return" in html
    assert "portfolio_run_status" in html


def test_strategy_workbench_viewer_scans_case_index_and_marks_boundary_violation(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    malformed_index = _write_json(
        tmp_path / "data/strategy_case_index/malformed_index.json",
        {
            "schema_version": "strategy_case_index.v1",
            "index_id": "malformed-index",
            "created_at": "2026-06-22T09:00:00Z",
            "producer": {"tool": "sis", "command": "strategy-case-index-build"},
            "case_count": 0,
            "strategy_count": 0,
            "cases": [],
            "strategies": [],
            "source_artifacts": [],
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
            "index_boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "paper_execution_allowed": False,
                "live_allowed": False,
                "db_persistence_allowed": True,
            },
        },
    )

    result = build_strategy_workbench_viewer(
        artifacts=None,
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "data/reports/strategy_workbench_viewer",
        replace_existing=True,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["artifact_count"] == 1
    assert (
        payload["source_artifacts"][0]["path"] == malformed_index.relative_to(tmp_path).as_posix()
    )
    assert payload["source_artifacts"][0]["boundary_violations"] == [
        "index_boundary.db_persistence_allowed"
    ]
    assert payload["boundary_violation_count"] == 1
