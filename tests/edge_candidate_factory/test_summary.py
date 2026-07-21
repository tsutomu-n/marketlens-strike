from __future__ import annotations

import json
from pathlib import Path

from sis.edge_candidate_factory.summary import build_edge_candidate_artifact_summary

from .fixtures import (
    llm_adversarial_evidence_review_payload,
    risk_actual_cash_handoff_payload,
    smart_candidate_prior_report_payload,
    virtual_execution_gate_payload,
)


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def test_summary_marks_missing_artifacts_without_failure(tmp_path: Path) -> None:
    missing_report = tmp_path / "missing_report.json"

    summary = build_edge_candidate_artifact_summary(candidate_report_path=missing_report)

    assert summary["core_status"] == "MISSING_CORE_ARTIFACTS"
    assert summary["next_action"] == "run edge-candidate-factory-build"
    assert summary["artifacts"]["candidate_report"]["exists"] is False
    assert summary["production_exchange_write_used"] is False
    assert summary["live_order_allowed"] is False
    assert summary["known_gap_count"] >= 1


def test_summary_separates_virtual_pass_from_actual_cash_ready(tmp_path: Path) -> None:
    report_path = _write(
        tmp_path / "smart_candidate_prior_report.json", smart_candidate_prior_report_payload()
    )
    virtual_payload = virtual_execution_gate_payload()
    virtual_payload["gate_status"] = "VIRTUAL_PASSED_EXECUTION_LIFECYCLE"
    virtual_path = _write(tmp_path / "virtual_gate.json", virtual_payload)
    handoff_path = _write(tmp_path / "handoff.json", risk_actual_cash_handoff_payload())

    summary = build_edge_candidate_artifact_summary(
        candidate_report_path=report_path,
        virtual_execution_gate_paths=[virtual_path],
        risk_actual_cash_handoff_paths=[handoff_path],
    )

    assert summary["core_status"] == "VIRTUAL_PASSED_NEEDS_ACTUAL_CASH_ROWS"
    assert summary["candidate_count_total"] == 1
    assert summary["candidate_count_rejected"] == 0
    assert summary["shortlist_for_virtual_count"] == 0
    assert summary["virtual_passed_count"] == 1
    assert summary["actual_cash_ready_count"] == 0
    assert "actual cash rows are missing" in summary["top_blocker_reasons"]


def test_summary_does_not_promote_core_status_from_adversarial_review(tmp_path: Path) -> None:
    report_path = _write(
        tmp_path / "smart_candidate_prior_report.json", smart_candidate_prior_report_payload()
    )
    review_path = _write(
        tmp_path / "llm_adversarial_review.json",
        llm_adversarial_evidence_review_payload(),
    )

    summary = build_edge_candidate_artifact_summary(
        candidate_report_path=report_path,
        adversarial_review_paths=[review_path],
    )

    assert summary["core_status"] == "NEEDS_BACKTEST_KILL_GATE"
    assert summary["addon_status"]["adversarial_review_statuses"] == ["ADVERSARIAL_FINDING"]
