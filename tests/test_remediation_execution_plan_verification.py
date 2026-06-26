from __future__ import annotations

from sis.reports.remediation_execution_plan_verification import (
    flatten_observed_sources,
    ordered_verification,
    verification_confidence,
)


def test_flatten_observed_sources_recurses_through_nested_payloads() -> None:
    observed_sources = {
        "preflight": ["stdout_stderr", {"fallback": "markdown_reports"}],
        "postcheck": {"primary": ["phase_gate_review", 7, None]},
    }

    assert flatten_observed_sources(observed_sources) == [
        "stdout_stderr",
        "markdown_reports",
        "phase_gate_review",
    ]


def test_verification_confidence_uses_worst_source_confidence() -> None:
    signal_sources = {
        "direct": "stdout_stderr",
        "mixed": ["phase_gate_review", "markdown_reports"],
        "missing": [],
    }

    assert verification_confidence(signal_sources, ["direct"]) == "high"
    assert verification_confidence(signal_sources, ["mixed"]) == "low"
    assert verification_confidence(signal_sources, ["missing"]) == "unknown"
    assert verification_confidence(signal_sources, []) == "unknown"


def test_ordered_verification_sorts_by_confidence_then_signal_name() -> None:
    signal_sources = {
        "high_signal": "stdout_stderr",
        "low_signal": "markdown_reports",
        "medium_signal": "phase_gate_review",
        "unknown_signal": [],
    }

    assert ordered_verification(
        signal_sources,
        ["unknown_signal", "high_signal", "low_signal", "medium_signal"],
    ) == ["unknown_signal", "low_signal", "medium_signal", "high_signal"]
