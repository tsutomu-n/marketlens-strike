from __future__ import annotations

import json
from pathlib import Path

from sis.reports.phase_gate_review import build_phase_gate_review
from sis.reports.summary_normalizers import (
    normalize_phase_gate_summary,
    phase_gate_flat_fields,
    phase_gate_issue_note_lines,
    phase_gate_issue_preview_lines,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_registry(path: Path, venue: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "venue": venue,
                    "canonical_symbol": "SPY",
                    "venue_symbol": "SPY/USD",
                    "asset_class": "index",
                    "pair_index": 86,
                    "api_readable": True,
                    "api_orderable": True,
                    "active": True,
                    "notes": [],
                }
            ]
        ),
        encoding="utf-8",
    )


def test_build_phase_gate_review_writes_summary_and_markdown(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    _write_registry(data_dir / "registry/gtrade_instrument_registry.json", "gtrade")
    _write_registry(data_dir / "registry/ostium_instrument_registry.json", "ostium")

    raw_quote_path = data_dir / "raw/quotes/gtrade/2026-05-22.jsonl"
    raw_quote_path.parent.mkdir(parents=True, exist_ok=True)
    raw_quote_path.write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"QQQ","venue_symbol":"QQQ/USD","mark_price":100.0,"index_price":100.0,"spread_bps":2.0,"oracle_ts_ms":1779407999000,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"qqq"}',
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","mark_price":101.0,"index_price":101.0,"spread_bps":2.0,"oracle_ts_ms":1779407999000,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"spy"}',
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"XAU","venue_symbol":"XAU/USD","mark_price":102.0,"index_price":102.0,"spread_bps":3.0,"oracle_ts_ms":1779407999000,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"xau"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/backtest_metrics.json").write_text(
        '[{"timeframe":"4h","trade_count":10,"avg_trade_return":0.1}]',
        encoding="utf-8",
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":2,"latest_status_match":true,"mismatching_count":0}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"execution_drift_overview_status":"degraded","execution_drift_overview_diagnostics_alignment_match":false,"execution_drift_overview_state_comparison_mismatching_count":1,"execution_drift_overview_snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )

    evidence_path = data_dir / "evidence/evidence_card_20260522_000000.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "run_id": "20260522_000000",
                "created_at": "2026-05-22T00:00:00+00:00",
                "scope": {
                    "venues": ["gtrade"],
                    "symbols": ["QQQ", "SPY", "XAU"],
                    "timeframes": ["4h"],
                    "scalping_policy": "prohibited_by_default",
                },
                "data": {},
                "decision": "GO",
                "venue_decisions": [{"venue": "gtrade", "decision": "GO", "main_blocker": None}],
                "criteria": [],
                "blockers": [],
                "next_actions": ["proceed_to_phase2"],
                "timeline_latest_execution_summary": {
                    "execution_overall_status": "ok",
                    "execution_venue_count": 2,
                },
                "timeline_latest_execution_comparison_summary": {
                    "execution_comparison_all_registries_present": True,
                },
                "bundle_history_latest_execution_summary": {
                    "execution_overall_status": "warn",
                    "execution_venue_count": 1,
                },
                "bundle_history_latest_execution_comparison_summary": {
                    "execution_comparison_all_registries_present": False,
                },
                "cycle_history_latest_execution_summary": {
                    "execution_overall_status": "ok",
                    "execution_venue_count": 2,
                },
                "cycle_history_latest_execution_comparison_summary": {
                    "execution_comparison_all_registries_present": True,
                },
            }
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "logs/live_evidence/manifests/live_evidence_20260522_2308.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": "20260522_2308",
                "status": "completed",
                "decision": "GO",
                "artifacts": {"evidence_card": str(evidence_path)},
            }
        ),
        encoding="utf-8",
    )
    gtrade_backend_manifest_path = (
        data_dir / "raw/sidecar/gtrade-backend/manifests/2026-05-22/backend_r1.json"
    )
    gtrade_backend_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    gtrade_backend_manifest_path.write_text(
        json.dumps(
            {
                "status": "completed",
                "backend_ws_path": str(data_dir / "raw/sidecar/gtrade-backend/backend-ws/r1.jsonl"),
                "rest_snapshot_paths": [
                    str(data_dir / "raw/sidecar/gtrade-backend/rest/r1_trading_variables.json"),
                    str(data_dir / "raw/sidecar/gtrade-backend/rest/r1_open_trades.json"),
                ],
                "event_count": 10,
                "reconnect_count": 0,
                "deep_reorg_detected": False,
            }
        ),
        encoding="utf-8",
    )
    ostium_constraints_path = data_dir / "ops/ostium_constraints_r1.json"
    ostium_constraints_path.write_text(
        json.dumps(
            {
                "constraint_status": "pass",
                "failures": [],
                "python_sdk": {
                    "available": True,
                    "version": "3.2.1",
                    "status": "read_only_probe_passed",
                },
                "builder_prices_artifact": {
                    "path": str(data_dir / "raw/sidecar/ostium-constraints/r1_builder_prices.json"),
                    "body_digest": "builder-body",
                    "schema_digest": "builder-schema",
                },
                "legacy_latest_prices_artifact": {
                    "path": str(data_dir / "raw/sidecar/ostium-constraints/r1_latest_prices.json"),
                    "body_digest": "legacy-body",
                    "schema_digest": "legacy-schema",
                },
                "assets": [
                    {
                        "canonical_symbol": "XAU",
                        "venue_pair": "XAU-USD",
                        "legacy_asset_param": "XAUUSD",
                        "trading_hours_artifact": {
                            "path": str(data_dir / "raw/sidecar/ostium-constraints/r1_trading_hours_XAUUSD.json")
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    out_path = data_dir / "reports/phase_gate_review.md"
    summary_path = data_dir / "ops/phase_gate_review_summary.json"
    planner_summary_path = data_dir / "ops/remediation_planner_summary.json"
    evaluator_summary_path = data_dir / "ops/remediation_evaluator_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "remediation_signal_snapshots_before": {
                    "execution_drift_unresolved": {
                        "execution_drift_overview_status": "blocked",
                        "execution_drift_overview_diagnostics_alignment_match": False,
                    }
                },
                "remediation_recommendations": {
                    "execution_drift_unresolved": {
                        "status": "stalled",
                        "commands": ["uv run sis refresh-operations-artifacts"],
                        "why": "signals did not move toward target",
                        "source_confidence": "medium",
                        "source_policy": "structured_summary_priority",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    planner_summary_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source": "phase_gate_review",
                        "reason": "execution_drift_unresolved",
                        "source_confidence": "high",
                        "source_policy": "direct_observation_priority",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    evaluator_summary_path.write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "source": "phase_gate_review",
                        "reason": "execution_drift_unresolved",
                        "signal_evaluations": [
                            {
                                "signal": "execution_drift_overview_summary.json is regenerated",
                                "observed_source": "markdown_reports",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    text = build_phase_gate_review(
        data_dir,
        schema_root=PROJECT_ROOT / "schemas",
        execution_snapshot_summary_path=data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=data_dir / "ops/execution_state_comparison_history_summary.json",
        execution_snapshot_drift_history_summary_path=data_dir / "ops/execution_snapshot_drift_history_summary.json",
        execution_drift_overview_summary_path=data_dir / "ops/execution_drift_overview_summary.json",
        remediation_planner_summary_path=planner_summary_path,
        remediation_evaluator_summary_path=evaluator_summary_path,
        out_path=out_path,
        summary_path=summary_path,
    )

    assert out_path.exists()
    assert summary_path.exists()
    assert "Phase Gate Review" in text
    assert "## Quick Navigation" in text
    assert f"- phase_gate_review_report: {out_path}" in text
    assert "## Related Reports" in text
    assert f"- go_no_go_report: {data_dir / 'research/go_no_go_report.md'}" in text
    assert "phase2_entry_allowed: True" in text

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["quick_navigation"]["phase_gate_review_report"] == str(out_path)
    assert payload["related_reports"]["go_no_go_report"] == str(
        data_dir / "research/go_no_go_report.md"
    )
    assert payload["strict_validation_passed"] is True
    assert payload["strict_validation_issue_count"] == 0
    assert payload["checked_files"] >= 1
    assert payload["phase2_entry_allowed"] is True
    assert payload["phase_gate_decision"] == "GO"
    assert payload["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert payload["phase_gate_strict_validation_passed"] is True
    assert payload["phase_gate_strict_validation_issue_count"] == 0
    assert payload["phase_gate_checked_files"] >= 1
    assert payload["read_only_collector_gate_passed"] is True
    assert payload["latest_gtrade_backend_manifest_path"] == str(gtrade_backend_manifest_path)
    assert payload["latest_ostium_constraint_path"] == str(ostium_constraints_path)
    assert payload["latest_ostium_python_sdk_status"] == "read_only_probe_passed"
    assert payload["latest_ostium_builder_prices_artifact_path"].endswith("r1_builder_prices.json")
    assert payload["required_artifact_paths"]["latest_execution_snapshot_summary_path"] == str(
        data_dir / "ops/execution_snapshot_summary.json"
    )
    assert payload["missing_required_artifact_paths"] == []
    assert payload["artifact_recovery_commands"] == {}
    assert payload["remediation_order"][0]["priority"] == 4
    assert payload["remediation_order"][0]["reason"] == "execution_drift_unresolved"
    assert payload["remediation_success_criteria"]["execution_drift_unresolved"] == [
        "execution_drift_overview_status == ok",
        "execution_drift_overview_diagnostics_alignment_match == True",
    ]
    assert payload["remediation_preflight_commands"]["execution_drift_unresolved"] == [
        "uv run sis refresh-operations-artifacts"
    ]
    assert payload["remediation_postcheck_commands"]["execution_drift_unresolved"] == [
        "uv run sis phase-gate-review"
    ]
    assert payload["remediation_preflight_expected_outputs"]["execution_drift_unresolved"] == [
        "refresh-operations-artifacts regenerates execution summaries",
        "execution drift overview summary is rewritten",
    ]
    assert payload["remediation_execute_expected_outputs"]["execution_drift_unresolved"] == [
        "execution_drift_overview_summary.json is regenerated",
        "drift status is re-evaluated from fresh artifacts",
    ]
    assert payload["remediation_postcheck_pass_signals"]["execution_drift_unresolved"] == [
        "execution_drift_overview_status == ok",
        "execution_drift_overview_diagnostics_alignment_match == True",
    ]
    assert payload["remediation_signal_snapshots_before"]["execution_drift_unresolved"] == {
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": False,
    }
    assert payload["remediation_signal_snapshots_target"]["execution_drift_unresolved"] == {
        "execution_drift_overview_status": "ok",
        "execution_drift_overview_diagnostics_alignment_match": True,
    }
    assert payload["remediation_signal_snapshots_previous"]["execution_drift_unresolved"] == {
        "execution_drift_overview_status": "blocked",
        "execution_drift_overview_diagnostics_alignment_match": False,
    }
    assert payload["remediation_signal_snapshot_diffs"]["execution_drift_unresolved"][
        "execution_drift_overview_status"
    ] == {
        "previous": "blocked",
        "current": "degraded",
        "target": "ok",
        "trend": "changed",
        "target_matched": False,
    }
    assert payload["remediation_recommendations"]["execution_drift_unresolved"] == {
        "status": "improving",
        "commands": ["uv run sis refresh-operations-artifacts"],
        "why": "signals changed but low-confidence verification sources require revalidation before execute",
        "source_confidence": "high",
        "source_policy": "direct_observation_priority",
        "execute_signal_confidence": "low",
    }
    assert payload["remediation_planner_summary_path"] == str(planner_summary_path)
    assert payload["remediation_evaluator_summary_path"] == str(evaluator_summary_path)
    assert payload["phase_gate_review_report_path"] == str(out_path)
    assert payload["phase_gate_strict_validation_issues"] == []
    assert payload["latest_manifest_status"] == "completed"
    assert payload["decision"] == "GO"
    assert payload["diagnostics_all_available"] is True
    assert payload["execution_overall_status"] == "ok"
    assert payload["execution_venue_count"] == 2
    assert payload["execution_comparison_all_registries_present"] is True
    assert payload["execution_diagnostics_status"] == "degraded"
    assert payload["execution_balance_gap_detected"] is True
    assert payload["execution_gap_history_entry_count"] == 4
    assert payload["execution_gap_history_latest_status"] == "ok"
    assert payload["execution_gap_history_latest_diagnostics_status"] == "degraded"
    assert payload["execution_snapshot_drift_entry_count"] == 3
    assert payload["execution_snapshot_drift_latest_status_match"] is True
    assert payload["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert payload["execution_drift_overview_state_comparison_mismatching_count"] == 1
    assert payload["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] == 1
    assert payload["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert payload["timeline_latest_execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert payload["bundle_history_latest_execution_summary"]["execution_overall_status"] == "warn"
    assert payload["bundle_history_latest_execution_comparison_summary"]["execution_comparison_all_registries_present"] is False
    assert payload["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert payload["cycle_history_latest_execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert "timeline_latest_execution_overall_status: ok" in text
    assert "bundle_history_latest_execution_overall_status: warn" in text
    assert "cycle_history_latest_execution_overall_status: ok" in text
    assert "## Required Artifacts" in text
    assert "missing_required_artifact_paths: none" in text
    assert "## Recovery Commands" in text
    assert "recovery_commands: none" in text
    assert "## Remediation Order" in text
    assert "priority_4: execution_drift_unresolved" in text
    assert "## Remediation Success Criteria" in text
    assert "execution_drift_overview_status == ok" in text
    assert "## Remediation Command Flow" in text
    assert "`uv run sis refresh-operations-artifacts`" in text
    assert "`uv run sis phase-gate-review`" in text
    assert "## Remediation Verification Signals" in text
    assert "preflight_expected_output:" in text
    assert "execute_expected_output:" in text
    assert "postcheck_pass_signal:" in text
    assert "## Remediation Signal Snapshots" in text
    assert "before:" in text
    assert "target:" in text
    assert "## Remediation Signal Diffs" in text
    assert "trend=changed" in text
    assert "## Remediation Recommendations" in text
    assert "status: improving" in text
    assert "## Stop Conditions" in text


def test_phase_gate_normalizer_keeps_prefixed_validation_counts() -> None:
    normalized = normalize_phase_gate_summary(
        {
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "phase_gate_strict_validation_passed": False,
            "phase_gate_strict_validation_issue_count": 3,
            "phase_gate_checked_files": 9,
        }
    )

    assert normalized["strict_validation_issue_count"] == 3
    assert normalized["checked_files"] == 9

    phase_gate_flat = phase_gate_flat_fields(normalized)
    assert phase_gate_flat["phase_gate_strict_validation_issue_count"] == 3
    assert phase_gate_flat["phase_gate_checked_files"] == 9
    assert phase_gate_flat["phase_gate_strict_validation_issues"] is None


def test_phase_gate_issue_helpers_accept_string_and_dict_issues() -> None:
    summary = {
        "phase_gate_strict_validation_issues": [
            {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"},
            "data/ops/execution_snapshot_summary.json: malformed payload",
        ]
    }

    assert phase_gate_issue_preview_lines(summary) == [
        "data/research/backtest_metrics_summary.json: missing field",
        "data/ops/execution_snapshot_summary.json: malformed payload",
    ]
    assert phase_gate_issue_note_lines(summary) == [
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field",
        "phase_gate_issue_2=data/ops/execution_snapshot_summary.json: malformed payload",
    ]
