from typing import Any
from pathlib import Path

from sis.commands.ops_state_echo import (
    dict_or_empty,
    echo_state_snapshot_summaries,
    state_restore_ack_lines,
    state_snapshot_export_lines,
)


def test_dict_or_empty_returns_dict_payload() -> None:
    payload = {"status": "ok"}

    assert dict_or_empty(payload) is payload


def test_dict_or_empty_returns_empty_dict_for_non_dict_payload() -> None:
    assert dict_or_empty(None) == {}
    assert dict_or_empty(["not", "a", "dict"]) == {}


def test_state_snapshot_export_lines_preserve_bare_path_output() -> None:
    assert state_snapshot_export_lines(Path("data/state/state_snapshot.json")) == [
        "data/state/state_snapshot.json",
    ]


def test_state_restore_ack_lines_preserve_restored_label() -> None:
    assert state_restore_ack_lines(restored=True) == ["restored=true"]
    assert state_restore_ack_lines(restored=False) == ["restored=false"]


def test_echo_state_snapshot_summaries_forwards_audit_and_normalized_phase_gate() -> None:
    audit_calls: list[dict[str, Any]] = []
    phase_calls: list[dict[str, Any]] = []
    normalizer_calls: list[dict[str, Any]] = []
    audit_summary = {"overall_status": "ok"}
    raw_phase_gate = {"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"}
    normalized_phase_gate = {"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"}

    def normalize_phase_gate(summary: dict) -> dict:
        normalizer_calls.append(summary)
        return normalized_phase_gate

    echo_state_snapshot_summaries(
        {"audit_summary": audit_summary, "phase_gate_summary": raw_phase_gate},
        normalize_phase_gate_summary=normalize_phase_gate,
        echo_audit_summary=audit_calls.append,
        echo_phase_gate_summary=phase_calls.append,
    )

    assert audit_calls == [audit_summary]
    assert normalizer_calls == [raw_phase_gate]
    assert phase_calls == [normalized_phase_gate]


def test_echo_state_snapshot_summaries_ignores_missing_or_non_dict_summaries() -> None:
    audit_calls: list[dict[str, Any]] = []
    phase_calls: list[dict[str, Any]] = []
    normalizer_calls: list[dict[str, Any]] = []

    def normalize_phase_gate(summary: dict) -> dict:
        normalizer_calls.append(summary)
        return summary

    echo_state_snapshot_summaries(
        {"audit_summary": "missing", "phase_gate_summary": None},
        normalize_phase_gate_summary=normalize_phase_gate,
        echo_audit_summary=audit_calls.append,
        echo_phase_gate_summary=phase_calls.append,
    )
    echo_state_snapshot_summaries(
        "not a payload",
        normalize_phase_gate_summary=normalize_phase_gate,
        echo_audit_summary=audit_calls.append,
        echo_phase_gate_summary=phase_calls.append,
    )

    assert audit_calls == []
    assert normalizer_calls == []
    assert phase_calls == []
