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

    out_path = data_dir / "reports/phase_gate_review.md"
    summary_path = data_dir / "ops/phase_gate_review_summary.json"
    text = build_phase_gate_review(
        data_dir,
        schema_root=Path("/home/tn/projects/marketlens-strike/schemas"),
        execution_snapshot_summary_path=data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=data_dir / "ops/execution_gap_history_summary.json",
        execution_snapshot_drift_history_summary_path=data_dir / "ops/execution_snapshot_drift_history_summary.json",
        execution_drift_overview_summary_path=data_dir / "ops/execution_drift_overview_summary.json",
        out_path=out_path,
        summary_path=summary_path,
    )

    assert out_path.exists()
    assert summary_path.exists()
    assert "Phase Gate Review" in text
    assert "phase2_entry_allowed: True" in text

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["strict_validation_passed"] is True
    assert payload["strict_validation_issue_count"] == 0
    assert payload["checked_files"] >= 1
    assert payload["phase2_entry_allowed"] is True
    assert payload["phase_gate_decision"] == "GO"
    assert payload["phase_gate_reason"] == "decision_cleared_and_phase1_gate_complete"
    assert payload["phase_gate_strict_validation_passed"] is True
    assert payload["phase_gate_strict_validation_issue_count"] == 0
    assert payload["phase_gate_checked_files"] >= 1
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
