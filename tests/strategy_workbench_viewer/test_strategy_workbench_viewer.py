from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.strategy_workbench_viewer.service import build_strategy_workbench_viewer


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
                "failed_condition_count": 1,
            },
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
        Path("schemas/strategy_workbench_viewer.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)

    assert payload["schema_version"] == "strategy_workbench_viewer.v1"
    assert payload["artifact_count"] == 4
    assert payload["paper_execution_allowed"] is False
    assert payload["live_allowed"] is False
    assert payload["source_artifacts"][0]["status"] == "READY_FOR_PAPER_SMOKE_PLAN"
    assert payload["source_artifacts"][1]["status"] == "NEEDS_ACTUAL_CASH"
    assert payload["source_artifacts"][1]["summary"]["proxy_gap_count"] == 1
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
