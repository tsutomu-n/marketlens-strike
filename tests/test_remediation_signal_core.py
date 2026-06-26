from __future__ import annotations

from sis.reports.remediation_signal_core import (
    action_result,
    evaluate_signal,
    evaluator_status,
    issue_preview_values,
)


def test_issue_preview_values_normalizes_structured_and_string_items() -> None:
    assert issue_preview_values(
        [
            {"path": "data/a.json", "message": "missing field"},
            {"path": "data/b.json"},
            {"message": "bad value"},
            "plain issue",
            123,
        ]
    ) == [
        "data/a.json: missing field",
        "data/b.json",
        "bad value",
        "plain issue",
    ]


def test_evaluate_signal_handles_equality_set_empty_and_non_null() -> None:
    summary = {
        "phase_gate_decision": "READ_ONLY_GO",
        "phase2_entry_allowed": True,
        "blockers": [],
        "required_artifact_paths": {
            "latest_trade_xyz_registry_path": "data/registry/trade_xyz.json",
            "latest_trade_xyz_quote_path": "data/raw/quotes/trade_xyz/quotes.jsonl",
        },
    }

    assert evaluate_signal("phase_gate_decision == READ_ONLY_GO", summary) == {
        "signal": "phase_gate_decision == READ_ONLY_GO",
        "status": "pass",
        "field": "phase_gate_decision",
        "expected": "READ_ONLY_GO",
        "observed": "READ_ONLY_GO",
    }
    assert evaluate_signal("phase2_entry_allowed in {True, False}", summary) == {
        "signal": "phase2_entry_allowed in {True, False}",
        "status": "pass",
        "field": "phase2_entry_allowed",
        "expected": [True, False],
        "observed": True,
    }
    assert evaluate_signal("blockers is empty", summary) == {
        "signal": "blockers is empty",
        "status": "pass",
        "field": "blockers",
        "expected": "empty",
        "observed": [],
    }
    assert evaluate_signal("required artifact paths are non-null", summary) == {
        "signal": "required artifact paths are non-null",
        "status": "pass",
        "field": "required_artifact_paths",
        "expected": "non-null",
        "observed": summary["required_artifact_paths"],
    }


def test_result_aggregation_helpers_keep_existing_status_contract() -> None:
    assert action_result([]) == "manual_review"
    assert action_result([{"status": "pass"}, {"status": "pass"}]) == "pass"
    assert action_result([{"status": "pass"}, {"status": "unsupported"}]) == "partial"
    assert action_result([{"status": "fail"}]) == "fail"

    assert evaluator_status([]) == "no_actions"
    assert evaluator_status(["pass", "pass"]) == "auto_passed"
    assert evaluator_status(["partial"]) == "partial"
    assert evaluator_status(["fail"]) == "needs_retry"
    assert evaluator_status(["manual_review"]) == "manual_review"
