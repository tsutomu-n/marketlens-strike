from __future__ import annotations

from sis.reports import summary_normalizers
from sis.reports.remediation_recommendation_normalizers import (
    compare_signal_snapshots,
    recommend_remediation_actions,
    signal_observed_sources_by_reason,
    signal_source_confidence,
    source_confidence_for_observed_sources,
)


def test_compare_signal_snapshots_classifies_target_trends_and_sequence_targets() -> None:
    diffs = compare_signal_snapshots(
        {
            "unchanged": "ok",
            "improved": "bad",
            "regressed": "ok",
            "changed": "old",
        },
        {
            "unchanged": "ok",
            "improved": "ok",
            "regressed": "bad",
            "changed": "new",
            "new": "accepted",
        },
        {
            "unchanged": "ok",
            "improved": ["ok", "warn"],
            "regressed": "ok",
            "changed": "target",
            "new": ["accepted", "pending"],
        },
    )

    assert diffs["unchanged"]["trend"] == "unchanged"
    assert diffs["unchanged"]["target_matched"] is True
    assert diffs["improved"]["trend"] == "improved"
    assert diffs["improved"]["target_matched"] is True
    assert diffs["regressed"]["trend"] == "regressed"
    assert diffs["regressed"]["target_matched"] is False
    assert diffs["changed"]["trend"] == "changed"
    assert diffs["changed"]["target_matched"] is False
    assert diffs["new"]["trend"] == "new"
    assert diffs["new"]["target_matched"] is True


def test_source_confidence_prefers_best_observed_source_rank() -> None:
    assert source_confidence_for_observed_sources(["markdown_reports"]) == "low"
    assert source_confidence_for_observed_sources(["markdown_reports", "phase_gate_review"]) == (
        "medium"
    )
    assert source_confidence_for_observed_sources(["phase_gate_review", "stdout_stderr"]) == (
        "high"
    )
    assert source_confidence_for_observed_sources([]) is None


def test_signal_observed_sources_by_reason_maps_matching_source_actions() -> None:
    evaluator_summary = {
        "actions": [
            {
                "source": "phase_gate_review",
                "reason": "execution_drift_unresolved",
                "signal_evaluations": [
                    {
                        "signal": "execution_drift_overview_status == ok",
                        "observed_source": "markdown_reports",
                    },
                    {
                        "signal": "phase_gate_strict_validation_issue_count == 0",
                        "observed_source": ["phase_gate_review", "stdout_stderr"],
                    },
                ],
            },
            {
                "source": "paper_operations_runbook",
                "reason": "strict_validation_failed",
                "signal_evaluations": [
                    {"signal": "ignored", "observed_source": "stdout_stderr"},
                ],
            },
        ]
    }

    assert signal_observed_sources_by_reason(
        evaluator_summary,
        source="phase_gate_review",
    ) == {
        "execution_drift_unresolved": {
            "execution_drift_overview_status == ok": "markdown_reports",
            "phase_gate_strict_validation_issue_count == 0": [
                "phase_gate_review",
                "stdout_stderr",
            ],
        }
    }


def test_signal_source_confidence_flattens_nested_observed_sources() -> None:
    assert (
        signal_source_confidence(
            {
                "first": {"nested": ["markdown_reports", "phase_gate_review"]},
                "second": "stdout_stderr",
            },
            ["first", "second", "missing"],
        )
        == "high"
    )
    assert signal_source_confidence({}, ["first"]) is None


def test_recommend_remediation_actions_chooses_status_and_commands() -> None:
    assert recommend_remediation_actions(
        {},
        preflight_commands=["preflight"],
        execute_commands=["execute"],
        source_confidence="low",
        source_policy="verify_before_execute",
    ) == {
        "status": "no_signals",
        "commands": [],
        "why": "no remediation signals available",
        "source_confidence": "low",
        "source_policy": "verify_before_execute",
    }
    assert recommend_remediation_actions(
        {"a": {"target_matched": True, "trend": "unchanged"}},
        postcheck_commands=["postcheck"],
    ) == {
        "status": "matched",
        "commands": ["postcheck"],
        "why": "all current signals match target values",
    }
    assert recommend_remediation_actions(
        {"a": {"target_matched": False, "trend": "regressed"}},
        preflight_commands=["preflight"],
        execute_commands=["execute"],
    ) == {
        "status": "regressed",
        "commands": ["preflight"],
        "why": "one or more signals regressed away from target",
    }
    assert recommend_remediation_actions(
        {"a": {"target_matched": False, "trend": "changed"}},
        preflight_commands=["preflight"],
        execute_commands=["execute"],
        execute_signal_confidence="low",
    ) == {
        "status": "improving",
        "commands": ["preflight"],
        "why": "signals changed but low-confidence verification sources require revalidation before execute",
        "execute_signal_confidence": "low",
    }


def test_summary_normalizers_keeps_remediation_recommendation_aliases() -> None:
    assert summary_normalizers.compare_signal_snapshots is compare_signal_snapshots
    assert (
        summary_normalizers.source_confidence_for_observed_sources
        is source_confidence_for_observed_sources
    )
    assert (
        summary_normalizers.signal_observed_sources_by_reason is signal_observed_sources_by_reason
    )
    assert summary_normalizers.signal_source_confidence is signal_source_confidence
    assert summary_normalizers.recommend_remediation_actions is recommend_remediation_actions
