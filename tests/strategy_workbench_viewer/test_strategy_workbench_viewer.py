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
) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "strategy_case_lite.v1",
            "strategy_id": strategy_id,
            "case_id": case_id,
            "updated_at": updated_at,
            "producer": {"tool": "sis", "command": "strategy-case-lite-update"},
            "source_artifacts": [],
            "timeline": [],
            "summary": {
                "artifact_count": 1,
                "timeline_count": 1,
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

    html = result.html_path.read_text(encoding="utf-8")
    assert '<span class="badge warn">READY_FOR_HUMAN_REVIEW</span>' in html
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
