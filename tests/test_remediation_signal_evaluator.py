from __future__ import annotations

from sis.reports.remediation_signal_evaluator import (
    action_result,
    coerce_value,
    evaluate_signal_with_observations,
    evaluator_status,
    issue_preview_values,
)


def test_coerce_value_handles_booleans_none_ints_and_backticks() -> None:
    assert coerce_value("True") is True
    assert coerce_value("False") is False
    assert coerce_value("None") is None
    assert coerce_value("42") == 42
    assert coerce_value("`READ_ONLY_GO`") == "READ_ONLY_GO"


def test_issue_preview_values_normalizes_structured_and_string_items() -> None:
    previews = issue_preview_values(
        [
            {"path": "data/a.json", "message": "missing field"},
            {"path": "data/b.json"},
            {"message": "bad value"},
            "plain issue",
            123,
        ]
    )

    assert previews == [
        "data/a.json: missing field",
        "data/b.json",
        "bad value",
        "plain issue",
    ]


def test_evaluate_signal_with_observations_uses_manual_and_stdout_sources() -> None:
    manual = evaluate_signal_with_observations(
        "diagnostics report is regenerated",
        {},
        ["diagnostics report is regenerated"],
        None,
        None,
        None,
        {},
        {},
        {},
        {},
    )
    assert manual["status"] == "pass"
    assert manual["observed_source"] == "observed_signals"

    checked_files = evaluate_signal_with_observations(
        "strict validation output reports checked_files >= 1",
        {},
        [],
        0,
        "checked_files=3 issues=0",
        "",
        {},
        {},
        {},
        {},
    )
    assert checked_files["status"] == "pass"
    assert checked_files["observed"] == 3
    assert checked_files["observed_source"] == "stdout_stderr"


def test_evaluate_signal_with_observations_uses_fallback_sources() -> None:
    result = evaluate_signal_with_observations(
        "phase gate summary lists blockers",
        {},
        [],
        None,
        None,
        None,
        {"blockers": ["missing_trade_xyz_evidence"]},
        {},
        {"blockers": "markdown_reports"},
        {},
    )

    assert result["status"] == "pass"
    assert result["observed"] == ["missing_trade_xyz_evidence"]
    assert result["observed_source"] == "markdown_reports"


def test_action_result_and_evaluator_status_aggregate_signal_results() -> None:
    assert action_result([]) == "manual_review"
    assert action_result([{"status": "pass"}, {"status": "pass"}]) == "pass"
    assert action_result([{"status": "pass"}, {"status": "unsupported"}]) == "partial"
    assert action_result([{"status": "fail"}]) == "fail"

    assert evaluator_status([]) == "no_actions"
    assert evaluator_status(["pass", "pass"]) == "auto_passed"
    assert evaluator_status(["partial"]) == "partial"
    assert evaluator_status(["fail"]) == "needs_retry"
    assert evaluator_status(["manual_review"]) == "manual_review"
